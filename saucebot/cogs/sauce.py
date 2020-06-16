import logging
import re
import reprlib

import typing

import discord
from discord.embeds import EmptyEmbed
from discord.ext import commands
from pysaucenao import SauceNao, ShortLimitReachedException, DailyLimitReachedException, SauceNaoException,\
    InvalidOrWrongApiKeyException, InvalidImageException, VideoSource, MangaSource

from saucebot.config import config
from saucebot.helpers import validate_url, basic_embed
from saucebot.lang import lang
from saucebot.models.database import Servers


class Sauce(commands.Cog):
    """
    SauceNao commands
    """
    def __init__(self):
        self._log = logging.getLogger(__name__)
        self._re_api_key = re.compile(r"^[a-zA-Z0-9]{40}$")

    @commands.command(aliases=['source'])
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
            # Make sure we have an API key configured for this server
            api_key = Servers.lookup_guild(ctx.guild)
            if not api_key:
                await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'api_missing')))
                return

            saucenao = SauceNao(api_key=api_key, min_similarity=float(config.get('SauceNao', 'min_similarity', fallback=50.0)))
            sauce = await saucenao.from_url(url)
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

        result = sauce.results[0]

        repr = reprlib.Repr()
        repr.maxstring = 16
        self._log.debug(f"[{ctx.guild.name}] {sauce.short_remaining} short API queries remaining for {repr.repr(api_key)}")
        self._log.info(f"[{ctx.guild.name}] {sauce.long_remaining} daily API queries remaining for {repr.repr(api_key)}")

        # Build our embed
        embed = basic_embed()
        embed.set_footer(text=lang('Sauce', 'found', member=ctx.author), icon_url='https://i.imgur.com/Mw109wP.png')
        embed.title = result.title or result.author_name or "Untitled"
        embed.url = result.url
        embed.description = lang('Sauce', 'match_title', {'index': result.index, 'similarity': result.similarity})

        if result.author_name and result.title:
            embed.set_author(name=result.author_name, url=result.author_url or EmptyEmbed)
        embed.set_thumbnail(url=result.thumbnail)

        if isinstance(result, VideoSource):
            embed.add_field(name=lang('Sauce', 'episode'), value=result.episode)
            embed.add_field(name=lang('Sauce', 'timestamp'), value=result.timestamp)

        if isinstance(result, MangaSource):
            embed.add_field(name=lang('Sauce', 'chapter'), value=result.chapter)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def apikey(self, ctx: commands.context.Context, api_key: str) -> None:
        """
        Define the SauceNao API key for this server.

        Be sure to run this command from a channel that is only accessible to administrators!
        """
        if not self._re_api_key.match(api_key):
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'bad_api_key')))
            return

        Servers.register(ctx.guild, api_key)
        await ctx.message.delete()
        await ctx.send(embed=basic_embed(title=lang('Global', 'generic_success'), description=lang('Sauce', 'registered_api_key')))
