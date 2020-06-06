import logging
from datetime import datetime

import discord
from discord.ext import commands

from saucebot.bot import bot
from saucebot.lang import lang


class Misc(commands.Cog):
    """
    Miscellaneous commands
    """
    def __init__(self):
        self._log = logging.getLogger(__name__)

    @commands.command()
    async def ping(self, ctx: commands.context.Context):
        """
        Tests the bot and Discord message response times
        """
        self._log.debug("Pong!")

        # Time between when the message was sent and when we processed it
        now = datetime.utcnow().timestamp()
        response_time = round((now - ctx.message.created_at.timestamp()) * 1000, 1)

        embed = discord.Embed()
        embed.description = lang('Misc', 'ping_response', {'server': response_time, 'message': 'Pending...'})

        # Time between when we sent the message and when it was registered by Discord
        now = datetime.utcnow().timestamp()
        message = await ctx.send(embed=embed)
        message_delay = round((datetime.utcnow().timestamp() - now) * 1000, 1)

        embed.description = lang('Misc', 'ping_response', {'server': response_time, 'message': message_delay})
        await message.edit(embed=embed)

    @commands.command(alias=['support', 'patreon'])
    async def info(self, ctx: commands.context.Context):
        """
        Learn more about the SauceBot project and how to contribute!
        """
        embed = discord.Embed()
        embed.set_thumbnail(url=bot.user.avatar_url)
        embed.title = lang('Misc', 'info_title')
        embed.url = 'https://github.com/FujiMakoto/saucebot'
        embed.description = lang('Misc', 'info_desc')

        await ctx.send(embed=embed)
