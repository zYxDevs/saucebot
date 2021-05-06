import logging
import re
import typing

import discord

from saucebot.bot import bot
from saucebot.log import log

# https://daringfireball.net/2010/07/improved_regex_for_matching_urls

URL_REGEX = re.compile(r"(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")

_log = logging.getLogger(__name__)


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
    thumbnail = kwargs.pop('avatar') if 'avatar' in kwargs else bot.user.avatar_url
    embed.set_thumbnail(url=thumbnail)

    return embed


def reaction_check(message: discord.Message, authorized_users: typing.List[int], valid_emojis: typing.List[str]):
    def _inner_check(_reaction: discord.Reaction, _user: discord.User):
        if message.id != _reaction.message.id:
            _log.debug(f"[Reaction check] Wrong message (Expecting {message.id}, got {_reaction.message.id})")
            return False

        if _user.id not in authorized_users:
            _log.debug(f"[Reaction check] Unauthorized user: {_user.id}")
            return False

        if str(_reaction.emoji) not in valid_emojis:
            _log.debug(f"[Reaction check] Invalid emoji: {_reaction.emoji}")
            return False

        _log.debug("[Reaction check] Check passed!")
        return True

    return _inner_check


def keycap_emoji(number: int) -> str:
    """
    Helper function for getting a 0-10 keycap emoji, since these are inherently weird
    """
    # Only keycaps between 0 and 10 are supported
    if not 0 <= number <= 10:
        raise IndexError

    # 10 is unique
    if number == 10:
        return "\N{keycap ten}"

    return str(number) + "\N{variation selector-16}\N{combining enclosing keycap}"


def keycap_to_int(emoji: discord.Emoji) -> int:
    """
    Converts a keycap emoji back to an integer
    Used to help when prompting users to select an index with keycap reactions
    """
    if str(emoji) == '\N{keycap ten}':
        return 10
    else:
        return int(str(emoji)[0])
