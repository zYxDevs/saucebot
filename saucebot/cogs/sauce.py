import asyncio
import logging
import re
import reprlib
import typing
from io import BytesIO

import discord
import pysaucenao
from discord.embeds import EmptyEmbed
from discord.ext import commands
from pysaucenao import DailyLimitReachedException, GenericSource, InvalidImageException, InvalidOrWrongApiKeyException, \
    MangaSource, SauceNao, SauceNaoException, ShortLimitReachedException, VideoSource
from pysaucenao.containers import ACCOUNT_ENHANCED, AnimeSource, BooruSource

from saucebot.bot import bot
from saucebot.config import config, server_api_limit
from saucebot.helpers import basic_embed, keycap_emoji, keycap_to_int, reaction_check, validate_url
from saucebot.lang import lang
from saucebot.models.database import SauceCache, SauceQueries, Servers
from saucebot.tracemoe import ATraceMoe


class Sauce(commands.Cog):
    """
    SauceNao commands
    """

    IMAGE_URL_RE = re.compile(r"^https?://\S+(\.jpg|\.png|\.jpeg|\.webp)$")

    def __init__(self):
        self._log = logging.getLogger(__name__)
        self._api_key = config.get('SauceNao', 'api_key', fallback=None)
        self._re_api_key = re.compile(r"^[a-zA-Z0-9]{40}$")
        self.tracemoe = None

        bot.loop.create_task(self.purge_cache())
        self.ready_tracemoe()

    def ready_tracemoe(self):
        token = config.get('TraceMoe', 'token', fallback=None)
        if token:
            self.tracemoe = ATraceMoe(bot.loop, token)

    @commands.command(aliases=['source'])
    @commands.cooldown(server_api_limit or 10000, 86400, commands.BucketType.guild)
    async def sauce(self, ctx: commands.context.Context, url: typing.Optional[str] = None) -> None:
        """
        Get the sauce for the attached image, the specified image URL, or the last image uploaded to the channel
        """
        # No URL specified? Check for attachments.
        url = url or await self._get_last_image_post(ctx)

        # If we still don't have a URL, that means no attachments have been recently uploaded, and we have nothing to work with
        if not url:
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'no_images')))
            return

        self._log.info(f"[{ctx.guild.name}] Looking up image source/sauce: {url}")

        # Make sure the URL is valid
        if not validate_url(url):
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'bad_url')))
            return

        # Make sure this user hasn't exceeded their API limits
        if self._check_member_limited(ctx):
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'),
                                             description=lang('Sauce', 'member_api_limit_exceeded')))
            return

        # Attempt to find the source of this image
        try:
            preview = None
            sauce = await self._get_sauce(ctx, url)
            if isinstance(sauce, AnimeSource):
                preview_file, nsfw = await self._video_preview(sauce, url, True)
                if preview_file:
                    if nsfw and not ctx.channel.is_nsfw():
                        self._log.info(f"Channel #{ctx.channel.name} is not NSFW; not uploading an NSFW video here")
                    else:
                        preview = discord.File(
                                BytesIO(preview_file),
                                filename=f"{sauce.title}_preview.mp4".lower().replace(' ', '_')
                        )
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
            embed = basic_embed(title=lang('Sauce', 'not_found', member=ctx.author),
                                description=lang('Sauce', 'not_found_advice'))

            google_url  = f"https://www.google.com/searchbyimage?image_url={url}&safe=off"
            ascii_url   = f"https://ascii2d.net/search/url/{url}"
            yandex_url  = f"https://yandex.com/images/search?url={url}&rpt=imageview"

            urls = [
                (lang('Sauce', 'google'), google_url),
                (lang('Sauce', 'ascii2d'), ascii_url),
                (lang('Sauce', 'yandex'), yandex_url)
            ]
            urls = ' • '.join([f"[{t}]({u})" for t, u in urls])

            embed.add_field(name=lang('Sauce', 'search_engines'), value=urls)
            await ctx.send(embed=embed)
            return

        await ctx.send(embed=await self._build_sauce_embed(ctx, sauce), file=preview)
        await ctx.message.delete()

    async def _get_last_image_post(self, ctx: commands.context.Context) -> typing.Optional[str]:
        """
        Get the most recently posted image in this channel
        Args:
            ctx (commands.context.Context):

        Returns:
            typing.Optional[str]
        """
        async for message in ctx.channel.history(limit=50):  # type: discord.Message
            # Make sure there's an image attachment
            image_attachments = []  # type: typing.Optional[typing.List[discord.Attachment]]
            for _attachment in message.attachments:  # type: discord.Attachment
                # Native images
                if self._get_attachment_image(_attachment):
                    image_attachments.append(_attachment)

            # Do we have any images?
            if image_attachments:
                attachment = await self._index_prompt(ctx, ctx.channel, image_attachments)
                image_url = self._get_attachment_image(attachment)
                self._log.info(f"[{ctx.guild.name}] Attachment found: {image_url}")
                return image_url

            if self.IMAGE_URL_RE.match(message.content):
                self._log.debug(f"[{ctx.guild.name}] Message contains an embedded image link: {message.content}")
                return message.content

    def _get_attachment_image(self, attachment: discord.Attachment) -> typing.Optional[str]:
        """
        Gets the image associated with an attachment, including support for video attachments
        Args:
            attachment (discord.Attachment): The attachment to process.

        Returns:
            typing.Optional[str]
        """
        if not attachment.url:
            return None

        if attachment.url and str(attachment.url).endswith(('.jpg', '.png', '.gif', '.jpeg', '.webp')):
            return attachment.url

        if attachment.url and str(attachment.url).endswith(('.mp4', '.webm', '.mov')):
            return attachment.proxy_url + '?format=jpeg'

    async def _index_prompt(self, ctx: commands.context.Context, channel: discord.TextChannel, items: list):
        prompt = await channel.send(lang('Sauce', 'multiple_images'))  # type: discord.Message
        index_range = range(1, min(len(items), 10) + 1)

        # Add the numerical emojis. The syntax is weird for this.
        for index in index_range:
            await prompt.add_reaction(keycap_emoji(index))

        try:
            check = reaction_check(prompt, [ctx.message.author.id], [keycap_emoji(i) for i in index_range])
            reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.message.delete()
            await prompt.delete()
            return

        await prompt.delete()
        return items[keycap_to_int(reaction) - 1]

    async def _get_sauce(self, ctx: commands.context.Context, url: str) -> typing.Optional[GenericSource]:
        """
        Perform a SauceNao lookup on the supplied URL
        Args:
            ctx (commands.context.Context):
            url (str):

        Returns:
            typing.Optional[GenericSource]
        """
        # Get the API key for this server
        api_key = Servers.lookup_guild(ctx.guild)
        if not api_key:
            api_key = self._api_key

        # Log the query
        SauceQueries.log(ctx, url)

        cache = SauceCache.fetch(url)  # type: SauceCache
        if cache:
            container   = getattr(pysaucenao.containers, cache.result_class)
            sauce       = container(cache.header, cache.result)  # type: GenericSource
            self._log.info(f'Cache entry found: {sauce.title}')
        else:
            # Initialize SauceNao and execute a search query
            saucenao = SauceNao(api_key=api_key,
                                min_similarity=float(config.get('SauceNao', 'min_similarity', fallback=50.0)),
                                priority=[21, 22, 5, 37, 25])
            search = await saucenao.from_url(url)
            sauce = search.results[0] if search.results else None

            # Log output
            rep = reprlib.Repr()
            rep.maxstring = 16
            self._log.debug(f"[{ctx.guild.name}] {search.short_remaining} short API queries remaining for {rep.repr(api_key)}")
            self._log.info(f"[{ctx.guild.name}] {search.long_remaining} daily API queries remaining for {rep.repr(api_key)}")

            # Cache the search result
            if sauce:
                SauceCache.add_or_update(url, sauce)

        return sauce

    async def _build_sauce_embed(self, ctx: commands.context.Context, sauce: GenericSource) -> discord.Embed:
        """
        Builds a Discord embed for the provided SauceNao lookup
        Args:
            ctx (commands.context.Context)
            sauce (GenericSource):

        Returns:
            discord.Embed
        """
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

        if isinstance(sauce, AnimeSource):
            await sauce.load_ids()
            urls = [(lang('Sauce', 'anidb'), sauce.anidb_url)]

            if sauce.mal_url:
                urls.append((lang('Sauce', 'mal'), sauce.mal_url))

            if sauce.anilist_url:
                urls.append((lang('Sauce', 'anilist'), sauce.anilist_url))

            urls = ' • '.join([f"[{t}]({u})" for t, u in urls])
            embed.add_field(name=lang('Sauce', 'more_info'), value=urls, inline=False)

        if isinstance(sauce, MangaSource):
            embed.add_field(name=lang('Sauce', 'chapter'), value=sauce.chapter)

        if isinstance(sauce, BooruSource):
            if sauce.characters:
                characters = [c.title() for c in sauce.characters]
                embed.add_field(name=lang('Sauce', 'characters'), value=', '.join(characters), inline=False)
            if sauce.material:
                material = [m.title() for m in sauce.material]
                embed.add_field(name=lang('Sauce', 'material'), value=', '.join(material), inline=False)

        return embed

    async def _video_preview(self, sauce: AnimeSource, path_or_fh: typing.Union[str, typing.BinaryIO],
                             is_url: bool) -> typing.Tuple[typing.Optional[bytes], bool]:
        """
        Attempt to grab a video preview of an AnimeSource entry from trace.moe
        Args:
            sauce (AnimeSource): An anime of hentai source
            path_or_fh (typing.Union[str, typing.BinaryIO]): Path or file handler
            is_url (bool): Path is a URL to an image rather than a file path.

        Returns:
            typing.Tuple[typing.Optional[bytes], bool]: The video preview if available, and whether the video is NSFW.
        """
        if not self.tracemoe:
            return None, False

        # noinspection PyBroadException
        try:
            tracemoe_sauce = await self.tracemoe.search(path_or_fh, is_url=is_url)
            if not tracemoe_sauce.get('docs'):
                self._log.info("Tracemoe returned no results")
                return None, False
        except Exception as e:
            self._log.error(f"Tracemoe returned an exception: {e}")
            return None, False

        # Make sure our search results match
        if await sauce.load_ids():
            if sauce.anilist_id != tracemoe_sauce['docs'][0]['anilist_id']:
                self._log.info(f"saucenao and trace.moe provided mismatched anilist entries: `{sauce.anilist_id}` vs. `{tracemoe_sauce['docs'][0]['anilist_id']}`")
                return None, False

            self._log.info(f'Downloading video preview for AniList entry {sauce.anilist_id} from trace.moe')
            tracemoe_preview = await self.tracemoe.video_preview_natural(tracemoe_sauce)
            return tracemoe_preview, tracemoe_sauce['docs'][0]['is_adult']

        return None, False

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

        raise error

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

    async def purge_cache(self):
        """
        Task to purge SauceNao cache entries older than 24-hours every 6-hours
        Returns:
            None
        """
        await bot.wait_until_ready()

        while not bot.is_closed():
            try:
                self._log.info('[SYSTEM] Purging SauceNao query cache')
                SauceCache.purge_cache()
                await asyncio.sleep(21600)
            except Exception:
                self._log.exception('An unknown error occurred while purging the local query cache')
