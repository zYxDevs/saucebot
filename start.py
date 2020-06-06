from saucebot.config import config
from saucebot.saucebot import bot

bot.run(config.get('Discord', 'token'))
