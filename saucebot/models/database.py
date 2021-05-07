import hashlib
import typing
from time import time

import discord
from discord.ext.commands import Context
from pony.orm import *
from pysaucenao import GenericSource

from saucebot.config import config
from saucebot.log import log

db = Database()

if config.has_section('MySQL'):
    db.bind(provider='mysql', host=config.get('MySQL', 'hostname'), user=config.get('MySQL', 'username'),
            passwd=config.get('MySQL', 'password'), db=config.get('MySQL', 'database'), charset='utf8mb4')
else:
    db.bind(provider='sqlite', filename='database.sqlite', create_db=True)


# noinspection PyMethodParameters
class Servers(db.Entity):
    server_id = Required(int, size=64, unique=True)
    api_key = Optional(str, 40)

    @db_session
    def lookup_guild(guild: discord.Guild) -> typing.Optional[str]:
        """
        Gets the SauceNao API key for the specified guild
        Args:
            guild (discord.Guild):

        Returns:
            typing.Optional[str]
        """
        server = Servers.get(server_id=guild.id)
        if server:
            return server.api_key

    @db_session
    def register(guild: discord.Guild, api_key: str):
        # Delete any existing entry for this server
        server = Servers.get(server_id=guild.id)
        if server:
            server.delete()

        Servers(server_id=guild.id, api_key=api_key)
        log.info(f'Registering API key for server {guild.name} ({guild.id})')


# noinspection PyMethodParameters
class SauceCache(db.Entity):
    url_hash        = Required(str, 32, index=True, unique=True)
    created_at      = Required(int, size=32, index=True)
    header          = Required(Json)
    result          = Required(Json)
    result_class    = Required(str, 250)

    @db_session
    def fetch(url: str):
        """
        Fetch a cached result, if available
        Args:
            url ():

        Returns:

        """
        h = hashlib.new('md5')
        h.update(url.encode())

        return SauceCache.get(url_hash=h.hexdigest())

    @db_session
    def add_or_update(url: str, result: GenericSource):
        """
        Cache a SauceNao result for 24-hours
        Args:
            url (str): Url to query
            result (GenericSource): Result to cache

        Returns:
            SauceQueries
        """
        now = int(time())

        h = hashlib.new('md5')
        h.update(url.encode())

        log.debug(f"Looking up cache entry {h.hexdigest()}")
        cache = SauceCache.get(url_hash=h.hexdigest())
        if cache:
            log.debug(f"Refreshing cache entry for {h.hexdigest()}")
            cache.delete()

        return SauceCache(url_hash=h.hexdigest(), created_at=now, header=result.header, result=result.data,
                          result_class=type(result).__name__)

    # noinspection PyTypeChecker
    @db_session
    def purge_cache(cutoff_minutes: int = 86400) -> None:
        """
        Purge cache entries older than the supplied cutoff
        Returns:
            None
        """
        cutoff = int(time()) - (cutoff_minutes * 60)
        delete(c for c in SauceCache if c.created_at < cutoff)


# noinspection PyMethodParameters
class SauceQueries(db.Entity):
    server_id       = Required(int, size=64)
    user_id         = Required(int, size=64, index=True)
    url_hash        = Required(str, 32, index=True)
    queried         = Optional(int, size=32, index=True)

    @db_session
    def log(ctx: Context, url: str):
        """
        Gets the SauceNao API key for the specified guild
        Args:
            ctx (Context):
            url (str): URL to the image that was queries. Will be md5 hashed and stored in the database.

        Returns:
            SauceQueries
        """
        now = int(time())

        h = hashlib.new('md5')
        h.update(url.encode())

        log.debug(f"Logging query from user {ctx.author} with URL hash {h.hexdigest()}")
        return SauceQueries(server_id=ctx.guild.id, user_id=ctx.author.id, url_hash=h.hexdigest(), queried=now)

    # noinspection PyTypeChecker
    @db_session
    def user_count(user: discord.User, minutes: int = 5) -> int:
        """
        Get a count of how many requests the specified discord user has made in the specified timespan
        Args:
            user (discord.User):
            minutes (int):

        Returns:
            int
        """
        log.debug(f"Counting how many queries {user} has made in the last {minutes} minute(s)")
        cutoff = int(time()) - (minutes * 60)
        return count(q for q in SauceQueries if q.queried > cutoff)

    # noinspection PyTypeChecker
    @db_session
    def count_total() -> int:
        """
        Get a count of the total number of sauce requests the bot has ever received
        Returns:
            int
        """
        total = count(q for q in SauceQueries)
        log.debug(f"Counted {total} total number of saucenao queries")

        return total


class GuildBanlist(db.Entity):
    server_id   = Required(int, size=64, index=True)
    banned_on   = Required(int, size=32)
    reason      = Optional(str, max_len=3000)

    @db_session
    def check(guild: typing.Union[discord.Guild, int]) -> bool:
        """
        Check whether the specified guild has been banned
        Args:
            guild (typing.Union[discord.Guild, int]): The guild / server that is being checked.

        Returns:
            bool
        """
        guild_id = guild.id if isinstance(guild, discord.Guild) else guild
        banned = GuildBanlist.get(server_id=guild_id)
        return True if banned else False

    @db_session
    def ban(guild: discord.Guild, reason: typing.Optional[str] = None):
        """
        Adds a guild to the server ban list
        Args:
            guild (discord.Guild): The guild / server that is being banned
            reason (typing.Optional[str]): An optional reason which will be sent to the guild owner.

        Returns:
            None
        """
        now = int(time())
        if reason:
            reason = reason[:1000]

        log.warning(f"Guild {guild.name} ({guild.id}) is being added to the server banlist")
        GuildBanlist(server_id=guild.id, banned_on=now, reason=reason)

    @db_session
    def unban(guild: typing.Union[discord.Guild, int]) -> bool:
        """
        Removed a guild to the server ban list
        Args:
            guild (typing.Union[discord.Guild, int]): The guild / server that is being unbanned.

        Returns:
            bool: Returns False if the guild isn't on the banlist
        """
        # Make sure the guild has actually been banned first
        guild_id = guild.id if isinstance(guild, discord.Guild) else guild
        entry = GuildBanlist.get(server_id=guild_id)
        if not entry:
            log.warning(f"Attempting to unban guild {guild_id}, but it's not on the banlist")
            return False

        log.warning(f"Guild {guild_id} is being removed from the server banlist")
        entry.delete()
        return True


db.generate_mapping(create_tables=True)
