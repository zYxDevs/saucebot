import discord
from discord.ext import commands

from saucebot.bot import bot
from saucebot.cogs.admin import Admin
from saucebot.cogs.misc import Misc
from saucebot.cogs.sauce import Sauce
from saucebot.log import log

bot.add_cog(Sauce())
bot.add_cog(Misc())
bot.add_cog(Admin())


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    # If command has local error handler, return
    if hasattr(ctx.command, 'on_error'):
        return

    # Get the original exception
    error = getattr(error, 'original', error)

    # Stop spamming our console everytime someone uses another bots command
    if isinstance(error, commands.CommandNotFound):
        return

    raise error


@bot.event
async def on_ready():
    log.info(f'Logged in as {bot.user.name} ({bot.user.id})')

    print(f'{bot.user.display_name} is in {len(bot.guilds)} guild(s) and ready for work!')
    print('------')


@bot.event
async def on_guild_join(guild: discord.Guild):
    log.info(f'Joining guild {guild.name} ({guild.id}) with {guild.member_count} members')


@bot.event
async def on_guild_remove(guild: discord.Guild):
    log.info(f'Leaving guild {guild.name} ({guild.id})')
