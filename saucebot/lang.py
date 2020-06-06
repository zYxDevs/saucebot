import logging
import os
import random
import typing
from configparser import ConfigParser

import discord

from saucebot.config import config

# Set up localization for use elsewhere in the application
_language = config.get('Bot', 'Language', fallback='english')
_language_config = ConfigParser()
_language_config.read(os.path.join('lang', f'{_language}.ini'), 'utf-8')


def lang(category: str, key: str, replacements: typing.Optional[dict] = None, default=None,
         member: typing.Optional[discord.Member] = None):
    """
    Provides easy to use application localization in the form of ini configuration files

    Language strings can be added or altered in the data/lang folder
    """
    string = _language_config.get(category, key, fallback=default)  # type: str
    if string:
        if replacements:
            for rkey, rvalue in replacements.items():
                string = string.replace(f"{{{rkey}}}", rvalue)

        if member:
            string = _member_replacements(string, member)

    else:
        logging.getLogger(__name__).warning(f"Missing {_language} language string: {key} ({category})")
        return '<Missing language string>'

    return string


def rand_lang(category: str, replacements: typing.Optional[dict] = None, default=None,
              member: typing.Optional[discord.Member] = None):
    """
    An alternative to the regular lang() method that pulls a random language string from the specified category
    """
    strings = _language_config.items(category)
    if strings:
        key, string = random.choice(strings)
    else:
        if default:
            key, string = None, default
        else:
            logging.getLogger(__name__).warning(f"Missing {_language} language category: {category}")
            return '<Missing language string>'

    if replacements:
        for rkey, rvalue in replacements.items():
            string = string.replace(f"{{{rkey}}}", rvalue)

    if member:
        string = _member_replacements(string, member)

    return string


def _member_replacements(string: str, member: discord.Member) -> str:
    """
    Perform some standard replacements for language strings
    """
    string = string.replace('{display_name}', member.display_name)
    string = string.replace('{mention}', member.mention)

    return string
