import logging

import typing

import discord
from discord.embeds import EmptyEmbed
from discord.ext import commands
from pysaucenao import SauceNao, ShortLimitReachedException, DailyLimitReachedException, SauceNaoException, VideoSource, \
    MangaSource

from saucebot.config import config
from saucebot.helpers import validate_url, basic_embed
from saucebot.lang import lang


class Sauce(commands.Cog):
    """
    SauceNao commands
    """
    def __init__(self):
        self._log = logging.getLogger(__name__)

        # SauceNAO
        self._default_api_key = config.get('SauceNao', 'api_key')
        self._saucenow = SauceNao(api_key=self._default_api_key)

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

                self._log.info(f"Attachment found: {attachment.url}")
                url = attachment.url
                break

        # If we still don't have a URL, that means no attachments have been recently uploaded and we have nothing to work with
        if not url:
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'no_images')))
            return

        self._log.info("Looking up image source/sauce: " + url)

        # Make sure the URL is valid
        if not validate_url(url):
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'bad_url')))
            return

        # Attempt to find the source of this image
        try:
            sauce = await self._saucenow.from_url(url)
        except (ShortLimitReachedException, DailyLimitReachedException):
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'api_limit_exceeded')))
            return
        except SauceNaoException:
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'api_offline')))
            return

        if not sauce:
            self._log.info("No image sources found")
            await ctx.send(embed=basic_embed(title=lang('Global', 'generic_error'), description=lang('Sauce', 'not_found', member=ctx.author)))
            return

        result = sauce.results[0]

        # Build our embed
        embed = basic_embed()
        embed.set_footer(text=lang('Sauce', 'found', member=ctx.author), icon_url='https://i.imgur.com/Mw109wP.png')
        embed.title = result.title
        embed.url = result.url
        embed.description = lang('Sauce', 'match_title', {'index': result.index, 'similarity': result.similarity})

        if result.author_name:
            embed.set_author(name=result.author_name, url=result.author_url or EmptyEmbed)
        embed.set_thumbnail(url=result.thumbnail)

        if isinstance(result, VideoSource):
            embed.add_field(name=lang('Sauce', 'episode'), value=result.episode)
            embed.add_field(name=lang('Sauce', 'timestamp'), value=result.timestamp)

        if isinstance(result, MangaSource):
            embed.add_field(name=lang('Sauce', 'chapter'), value=result.chapter)

        await ctx.send(embed=embed)
