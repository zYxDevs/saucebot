import logging
from datetime import datetime

import discord
from discord.ext import commands

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
        # Time between when the message was sent and when we processed it
        now = datetime.utcnow().timestamp()
        response_time = round((now - ctx.message.created_at.timestamp()) * 1000, 1)

        embed = discord.Embed()
        embed.description = lang('Misc', 'ping_response', {'command': response_time, 'message': 'Pending...'})

        # Time between when we sent the message and when it was registered by Discord
        now = datetime.utcnow().timestamp()
        message = await ctx.send(embed=embed)
        response_time = round((now - ctx.message.created_at.timestamp()) * 1000, 1)
        message_delay = round((now - message.created_at.timestamp()) * 1000, 1)

        embed.description = lang('Misc', 'ping_response', {'command': response_time, 'message': message_delay})
        await message.edit(embed=embed)
