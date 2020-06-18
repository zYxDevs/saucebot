import logging
import re
import reprlib

import typing

import discord
import pysaucenao
from discord.embeds import EmptyEmbed
from discord.ext import commands
from pysaucenao import SauceNao, ShortLimitReachedException, DailyLimitReachedException, SauceNaoException, \
    InvalidOrWrongApiKeyException, InvalidImageException, VideoSource, MangaSource, GenericSource
from pysaucenao.containers import ACCOUNT_ENHANCED

from saucebot.config import config, server_api_limit, member_api_limit
from saucebot.helpers import validate_url, basic_embed
from saucebot.lang import lang
from saucebot.models.database import Servers, SauceQueries, SauceCache


class Sauce(commands.Cog):
    """
    SauceNao commands
    """
    def __init__(self):
        self._log = logging.getLogger(__name__)
        self._api_key = config.get('SauceNao', 'api_key', fallback=None)
        self._re_api_key = re.compile(r"^[a-zA-Z0-9]{40}$")

    @commands.command(aliases=['source'])
    @commands.cooldown(server_api_limit or 10000, 86400, commands.BucketType.guild)
    async def sauce(self, ctx: commands.context.Context, url: typing.Optional[str] = None) -> None:
        """
        Get the sauce for the attached image, the specified image URL, or the last image uploaded to the channel
        """
        # No URL specified? Check for attachments
        if not url:
            async for message in ctx.channel.history(limit=50):  # type: discord.Message
                if not message.attachments:
                    continue

                # Make sure there's an image attachment
                attachment = None  # type: typing.Optional[discord.Attachment]
                for _attachment in message.attachments:  # type: discord.Attachment
                    if _attachment.width:
                        attachment = _attachment
                        break

                # No image attachments?
                if not attachment:
                    continue

                self._log.info(f"[{ctx.guild.name}] Attachment found: {attachment.url}")
                url = attachment.url
                break

        # If we still don't have a URL, that means no attachments have been recently uploaded and we have nothing to work with
        if not url:
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'no_images')))
            return

        self._log.info(f"[{ctx.guild.name}] Looking up image source/sauce: {url}")

        # Make sure the URL is valid
        if not validate_url(url):
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'bad_url')))
            return

        # Attempt to find the source of this image
        try:
            # Make sure this user hasn't exceeded their API limits
            if self._check_member_limited(ctx):
                await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'member_api_limit_exceeded')))
                return

            # Get the API key for this server
            api_key = Servers.lookup_guild(ctx.guild)
            if not api_key:
                api_key = self._api_key

            # Log the query
            SauceQueries.log(ctx, url)

            # Check if we have a cached entry
            search = None
            cache = SauceCache.fetch(url)  # type: SauceCache
            if cache:
                container = getattr(pysaucenao.containers, cache.result_class)
                sauce = container(cache.header, cache.result)  # type: GenericSource
                self._log.info(f'Cache entry found: {sauce.title}')
            else:
                # Initialize SauceNao and execute a search query
                saucenao = SauceNao(api_key=api_key, min_similarity=float(config.get('SauceNao', 'min_similarity', fallback=50.0)))
                search = await saucenao.from_url(url)
                sauce = search.results[0]

                # Cache the search result
                SauceCache.add_or_update(url, sauce)
        except (ShortLimitReachedException, DailyLimitReachedException):
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'api_limit_exceeded')))
            return
        except InvalidOrWrongApiKeyException:
            self._log.warning(f"[{ctx.guild.name}] API key was rejected by SauceNao")
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'rejected_api_key')))
            return
        except InvalidImageException:
            self._log.info(f"[{ctx.guild.name}] An invalid image / image link was provided")
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'no_images')))
            return
        except SauceNaoException:
            self._log.exception(f"[{ctx.guild.name}] An unknown error occurred while looking up this image")
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'api_offline')))
            return

        if not sauce:
            self._log.info(f"[{ctx.guild.name}] No image sources found")
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'not_found', member=ctx.author)))
            return

        if search:
            repr = reprlib.Repr()
            repr.maxstring = 16
            self._log.debug(f"[{ctx.guild.name}] {search.short_remaining} short API queries remaining for {repr.repr(api_key)}")
            self._log.info(f"[{ctx.guild.name}] {search.long_remaining} daily API queries remaining for {repr.repr(api_key)}")

        # Build our embed
        embed = basic_embed()
        embed.set_footer(text=lang('Sauce', 'found', member=ctx.author), icon_url='https://i.imgur.com/Mw109wP.png')
        embed.title = sauce.title or sauce.author_name or "Untitled"
        embed.url = sauce.url
        embed.description = lang('Sauce', 'match_title', {'index': sauce.index, 'similarity': sauce.similarity})

        if sauce.author_name and sauce.title:
            embed.set_author(name=sauce.author_name, url=sauce.author_url or EmptyEmbed)
        embed.set_thumbnail(url=sauce.thumbnail)

        if isinstance(sauce, VideoSource):
            embed.add_field(name=lang('Sauce', 'episode'), value=sauce.episode)
            embed.add_field(name=lang('Sauce', 'timestamp'), value=sauce.timestamp)

        if isinstance(sauce, MangaSource):
            embed.add_field(name=lang('Sauce', 'chapter'), value=sauce.chapter)

        await ctx.send(embed=embed)

    @sauce.error
    async def sauce_error(self, ctx: commands.context.Context, error) -> None:
        """
        Override guild cooldowns for servers with their own API keys provided
        Args:
            ctx (commands.context.Context):
            error (Exception):

        Returns:
            None
        """
        if isinstance(error, commands.CommandOnCooldown):
            if Servers.lookup_guild(ctx.guild):
                self._log.info(f"[{ctx.guild.name}] Guild has an enhanced API key; ignoring triggered guild API limit")
                await ctx.reinvoke()
                return

            self._log.info(f"[{ctx.guild.name}] Guild has exceeded their available API queries for the day")
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'api_limit_exceeded')))

    def _check_member_limited(self, ctx: commands.context.Context) -> bool:
        """
        Check if the author of this message has exceeded their API limits
        Args:
            ctx (commands.context.Context):

        Returns:
            bool
        """
        member_limit = config.getint('SauceNao', 'member_api_limit', fallback=0)
        if not member_limit:
            self._log.debug('No member limit defined')
            return False

        count = SauceQueries.user_count(ctx.author)
        return count >= member_limit

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(5, 1800, commands.BucketType.guild)
    async def apikey(self, ctx: commands.context.Context, api_key: str) -> None:
        """
        Define your own enhanced SauceNao API key for this server.

        This can only be used to add enhanced / upgraded API keys, not freely registered ones. Adding your own enhanced
        API key will remove the shared daily API query limit from your server.

        You can get an enhanced API key from the following page:
        https://saucenao.com/user.php?page=account-upgrades
        """
        await ctx.message.delete()

        # Make sure the API key is formatted properly
        if not self._re_api_key.match(api_key):
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'bad_api_key')))
            return

        # Test and make sure it's a valid enhanced-level API key
        saucenao = SauceNao(api_key=api_key)
        test = await saucenao.test()

        # Make sure the test went through successfully
        if not test.success:
            self._log.error(f"[{ctx.guild.name}] An unknown error occurred while assigning an API key to this server",
                            exc_info=test.error)
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'api_offline')))
            return

        # Make sure this is an enhanced API key
        if test.account_type != ACCOUNT_ENHANCED:
            self._log.info(f"[{ctx.guild.name}] Rejecting an attempt to register a free API key")
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'api_free')))
            return

        Servers.register(ctx.guild, api_key)
        await ctx.send(embed=basic_embed(title=lang('Global', 'generic_success'), description=lang('Sauce', 'registered_api_key')))
