import re

import discord
import typing

from saucebot.bot import bot
from saucebot.log import log

# https://daringfireball.net/2010/07/improved_regex_for_matching_urls
from saucebot.models.database import Servers

URL_REGEX = re.compile(r"(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")


def validate_url(url: str) -> bool:
    """
    Validates URL's for security
    Args:
        url (str): The URL to validate

    Returns:
        bool
    """
    if not URL_REGEX.match(url):
        log.debug("URL failed to match: " + url)
        return False

    return True


def basic_embed(**kwargs) -> discord.Embed:
    """
    Generates a boilerplate embed with the bots avatar as the thumbnail
    Returns:
        discord.Embed
    """
    embed = discord.Embed(**kwargs)
    embed.set_thumbnail(url=bot.user.avatar_url)

    return embed
