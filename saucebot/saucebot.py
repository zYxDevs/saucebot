from saucebot.bot import bot
from saucebot.cogs.misc import Misc
from saucebot.log import log


bot.add_cog(Misc())


@bot.event
async def on_ready():
    log.info(f'Logged in as {bot.user.name} ({bot.user.id})')

    print(f'{bot.user.display_name} is ready for work!')
    print('------')