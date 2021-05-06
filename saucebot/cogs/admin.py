import asyncio
import logging
import typing

import discord
from discord.ext import commands

from saucebot.lang import lang
from saucebot.models.database import GuildBanlist


class Admin(commands.Cog):
    """
    Bot owner / administrative commands
    """
    def __init__(self):
        self._log = logging.getLogger(__name__)

    CONFIRM_EMOJI   = '<:confirm:781477845888794655>'
    ABORT_EMOJI     = '<:deny:781478098100027412>'

    @commands.command(name="ban-guild", aliases=["gban"])
    @commands.is_owner()
    async def ban_guild(self, ctx: commands.Context, guild_id: int, *, reason: typing.Optional[str] = None):
        """
        Bans a specified guild from using SauceBot
        Upon issuing this command, the bot will immediately leave the guild if they are already invited.
        Any future invite requests will be refused.
        """
        # Make sure the guild exists
        guild = ctx.bot.get_guild(guild_id)  # type: discord.Guild
        if not guild:
            await ctx.send(lang('Admin', 'guild_404'))

        # Make sure it's not already banned
        if GuildBanlist.check(guild):
            await ctx.send(lang('Admin', 'gban_already_banned'), delete_after=15.0)
            return

        # Confirm we really want to do this
        confirm_message = await ctx.send(lang('Admin', 'gban_confirm', {'guild_name': guild.name}))
        await confirm_message.add_reaction(self.CONFIRM_EMOJI)
        await confirm_message.add_reaction(self.ABORT_EMOJI)

        def _check(_reaction, _user):
            return _user == ctx.message.author and str(_reaction.emoji) in [self.CONFIRM_EMOJI, self.ABORT_EMOJI]

        try:
            reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60.0, check=_check)
        except asyncio.TimeoutError:
            return
        else:
            if str(reaction) != self.CONFIRM_EMOJI:
                return
        finally:
            await confirm_message.delete()

        GuildBanlist.ban(guild, reason)

        # Send the guild owner a ban message
        try:
            await guild.owner.send(lang('Admin', 'gban_notice', {'guild_name': guild.name}))
            if reason:
                await guild.owner.send(lang('Admin', 'gban_reason', {'reason': reason}))
        except (discord.Forbidden, AttributeError):
            self._log.warning(f"Failed to send ban notice for guild {guild.name} to user {guild.owner}")

        # Leave the guild
        await ctx.send(f'Leaving guild {guild.name} ({guild.id})', delete_after=15.0)
        await guild.leave()

    @commands.command(name="unban-guild", aliases=["ungban"])
    @commands.is_owner()
    async def unabn_guild(self, ctx: commands.Context, guild_id: int):
        """
        Removed a specified guild from the bots banlist
        """
        # Make sure the guild has actually been banned
        if not GuildBanlist.check(guild_id):
            await ctx.send(lang('Admin', 'gban_not_banned'), delete_after=15.0)
            return

        self._log.warning(f"Removing guild {guild_id} from the guild banlist")
        GuildBanlist.unban(guild_id)

        await ctx.send(lang('Admin', 'gban_unban_success'))

    @commands.Cog.listener('on_guild_join')
    async def refuse_banned_invites(self, guild: discord.Guild):
        """
        There's no way to actually refuse invites from a specific guild; so the best we can do is immediately leave
        a server after join if they are on the banlist.
        Args:
            guild (discord.Guild): The guild we are verifying.

        Returns:
            None
        """
        self._log.info(f"Verifying whether or not guild {guild.name} ({guild.id}) has been banned")
        if GuildBanlist.check(guild):
            self._log.warning(f"Banned guild {guild.name} ({guild.id}) attempted to re-invite the bot")
            await guild.leave()
