import discord

from saucebot.bot import bot
from saucebot.cogs.admin import Admin
from saucebot.cogs.misc import Misc
from saucebot.cogs.sauce import Sauce
from saucebot.log import log


bot.add_cog(Sauce())
bot.add_cog(Misc())
bot.add_cog(Admin())


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
