import logging
from datetime import datetime
from time import time

import discord
from discord.ext import commands

from saucebot.bot import bot
from saucebot.helpers import basic_embed
from saucebot.lang import lang


class Misc(commands.Cog):
    """
    Miscellaneous commands
    """
    def __init__(self):
        self._log = logging.getLogger(__name__)
        self._recache_stats_at = 0  # Recache guild/member counts every 15 minutes
        self._guild_count = 0
        self._user_count = 0

    @commands.command()
    async def ping(self, ctx: commands.Context):
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

    @commands.command(aliases=['support', 'patreon'])
    async def info(self, ctx: commands.Context):
        """
        Learn more about the SauceBot project and how to contribute!
        """
        embed = discord.Embed()
        embed.set_thumbnail(url=bot.user.avatar_url)
        embed.title = lang('Misc', 'info_title')
        embed.url = 'https://www.patreon.com/saucebot'
        embed.description = lang('Misc', 'info_desc')

        await ctx.send(embed=embed)

    @commands.command()
    async def stats(self, ctx: commands.Context):
        """
        Displays how many guilds SauceBot is in among statistics
        """
        embed = basic_embed(title=lang('Misc', 'stats_title'))
        embed.add_field(
            name=lang('Misc', 'stats_guilds'),
            value=lang('Misc', 'stats_guilds_desc', {'count': f'{self.guild_count:,}'}),
            inline=True
        )
        embed.add_field(
            name=lang('Misc', 'stats_users'),
            value=lang('Misc', 'stats_users_desc', {'count': f'{self.user_count:,}'}),
            inline=True
        )
        await ctx.reply(embed=embed)

    @property
    def guild_count(self):
        """
        Get the number of guilds the bot is in
        """
        if time() > self._recache_stats_at:
            self.recount_stats()

        return self._guild_count

    @property
    def user_count(self):
        """
        Get the sum of unique users in all guilds the bot is in
        """
        if time() > self._recache_stats_at:
            self.recount_stats()

        return self._user_count

    def recount_stats(self):
        """
        Recounts the guild statistics
        """
        self._guild_count = len(bot.guilds)
        self._user_count = len([member for member in bot.get_all_members()])
        self._recache_stats_at = time() + 900
