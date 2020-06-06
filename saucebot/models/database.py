import discord
import typing
from pony.orm import *

from saucebot.log import log

db = Database()
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


db.generate_mapping(create_tables=True)
