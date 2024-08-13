# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module containing bot logic."""

import argparse
import datetime as dt
import json
import logging
import logging.handlers
from math import ceil
from os import getenv

import discord
import discord.utils
from dotenv import load_dotenv

import src.fractalrhomb_globals as frf
from src.fractalrhomb_globals import bot
from src.fractalthorns_api import FractalthornsAPI, fractalthorns_api
from src.fractalthorns_exceptions import CachePurgeError

load_dotenv()

discord_logger = logging.getLogger("discord")

log_handler = logging.handlers.TimedRotatingFileHandler(
	filename="discord.log", when="midnight", backupCount=7, encoding="utf-8", utc=True
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
log_formatter = logging.Formatter(
	"[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
log_handler.setFormatter(log_formatter)
discord_logger.addHandler(log_handler)


@bot.event
async def on_ready() -> None:
	"""Do stuff when the bot finishes logging in."""
	print(f"Logged in as {bot.user}")


@bot.event
async def on_application_command_error(
	ctx: discord.ApplicationContext, error: Exception
) -> None:
	"""Do stuff when there's a command error."""
	response = "an unhandled exception occurred"
	await ctx.respond(response)
	raise error


@bot.slash_command(description="Pong!")
async def ping(ctx: discord.ApplicationContext) -> None:
	"""Pong."""
	response = f"pong! latency: {round(bot.latency*1000)}ms."
	await ctx.respond(response)


@bot.slash_command(name="license")
async def show_license(ctx: discord.ApplicationContext) -> None:
	"""Display the bot's license message."""
	license_text = (
		"```\n"
		"fractalrhomb\n"
		"Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)\n"
		"View the source code on GitHub: https://github.com/McAwesome123/fractal-rhomb\n"
		"\n"
		"This bot is licensed under the GNU Affero General Public License version 3 or later.\n"
		"For more information, visit: https://www.gnu.org/licenses/agpl-3.0.en.html\n"
		"\n"
		"fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).\n"
		"View it here: https://fractalthorns.com\n"
		"```"
	)
	await ctx.respond(license_text)


purge_group = bot.create_group("purge", "Purge the bot's cache.")


@purge_group.command(name="cache")
@discord.option(
	"cache",
	str,
	choices=[
		i.value
		for i in FractalthornsAPI.CacheTypes
		if i
		not in [
			FractalthornsAPI.CacheTypes.CACHE_METADATA,
			FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
		]
	],
)
async def purge(
	ctx: discord.ApplicationContext,
	cache: str,
) -> None:
	"""Purge the bot's cache."""
	cache = FractalthornsAPI.CacheTypes(cache)
	user = frf.bot_data.purge_cooldowns.get(str(ctx.author.id))
	if user is not None:
		time = user.get(cache.value)
		if (
			time is not None
			and dt.datetime.now(dt.UTC)
			< dt.datetime.fromtimestamp(time, dt.UTC) + frf.USER_PURGE_COOLDOWN
		):
			time += frf.USER_PURGE_COOLDOWN.total_seconds()
			response = f"you cannot do that. try again <t:{ceil(time)}:R>"
			await ctx.respond(response)
			return
	try:
		fractalthorns_api.purge_cache(cache)

	except CachePurgeError as exc:
		response = f"could not purge the cache: {exc.args[0].lower()}\ntry again <t:{ceil(exc.args[1].timestamp())}:R>"
		await ctx.respond(response)

	else:
		response = f"successfully purged {cache.value}"
		await ctx.respond(response)

		if str(ctx.author.id) not in frf.bot_data.purge_cooldowns:
			frf.bot_data.purge_cooldowns.update({str(ctx.author.id): {}})
		frf.bot_data.purge_cooldowns[str(ctx.author.id)].update(
			{cache.value: dt.datetime.now(dt.UTC).timestamp()}
		)
		try:
			frf.bot_data.save(frf.BOT_DATA_PATH)
		except Exception:
			discord_logger.exception("Could not save bot data.")


@purge_group.command(name="all")
async def purge_all(ctx: discord.ApplicationContext) -> None:
	"""Purge the bot's entire cache."""
	user = frf.bot_data.purge_cooldowns.get(str(ctx.author.id))
	purged = []
	cooldown = {}
	for cache in FractalthornsAPI.CacheTypes:
		if cache in [
			FractalthornsAPI.CacheTypes.CACHE_METADATA,
			FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
		]:
			continue

		if user is not None:
			time = user.get(cache.value)
			if (
				time is not None
				and dt.datetime.now(dt.UTC)
				< dt.datetime.fromtimestamp(time, dt.UTC) + frf.USER_PURGE_COOLDOWN
			):
				cooldown.update({cache: time + frf.USER_PURGE_COOLDOWN.total_seconds()})
				continue

		try:
			fractalthorns_api.purge_cache(cache)
		except CachePurgeError as exc:
			if len(exc.args) > 1:
				cooldown.update({cache: exc.args[1].timestamp()})
		else:
			purged.append(cache.value)

			if str(ctx.author.id) not in frf.bot_data.purge_cooldowns:
				frf.bot_data.purge_cooldowns.update({str(ctx.author.id): {}})
			frf.bot_data.purge_cooldowns[str(ctx.author.id)].update(
				{cache.value: dt.datetime.now(dt.UTC).timestamp()}
			)

	if len(purged) > 0:
		response = f"successfully purged {", ".join(purged)}"
		await ctx.respond(response)

		try:
			frf.bot_data.save(frf.BOT_DATA_PATH)
		except Exception:
			discord_logger.exception("Could not save bot data.")
	else:
		earliest = min(cooldown, key=cooldown.get)

		response = f"could not purge any caches.\nearliest available: '{earliest.value}' <t:{ceil(cooldown[earliest])}:R>"
		await ctx.respond(response)


@purge_group.command(name="force")
@discord.option(
	"cache",
	str,
	choices=[
		i.value
		for i in FractalthornsAPI.CacheTypes
		if i
		not in [
			FractalthornsAPI.CacheTypes.CACHE_METADATA,
			FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
		]
	],
)
async def force_purge(
	ctx: discord.ApplicationContext,
	cache: str,
) -> None:
	"""Force purge the bot's cache, regardless of cooldowns (restricted)."""
	cache = FractalthornsAPI.CacheTypes(cache)
	force_purge_allowed = json.loads(getenv("FORCE_PURGE_ALLOWED"))

	if str(ctx.author.id) in force_purge_allowed:
		fractalthorns_api.purge_cache(cache, force_purge=True)

		msg = f"'{cache.value}' purged by {ctx.author.id}."
		discord_logger.info(msg)

		response = f"successfully force purged {cache.value}"
		await ctx.respond(response)
	else:
		msg = f"Unauthorized force purge attempt by {ctx.author.id}."
		discord_logger.warning(msg)

		response = "you cannot do that."
		await ctx.respond(response)


bot_channel_group = bot.create_group(
	"botchannel",
	"Manage bot channels.",
	contexts={discord.InteractionContextType.guild},
	default_member_permissions=discord.Permissions(manage_guild=True),
)


@bot_channel_group.command(name="add")
@discord.default_permissions(manage_guild=True)
@discord.option(
	"channel",
	discord.SlashCommandOptionType.channel,
	desrciption="The channel to add (default: (current channel))",
)
@discord.option("hidden", bool, description="Only visible for you (default: No)")
async def add_bot_channel(
	ctx: discord.ApplicationContext,
	channel: discord.abc.GuildChannel | discord.abc.Messageable | None = None,
	*,
	hidden: bool = False,
) -> None:
	"""Add the channel as a bot channel (requires Manage Server permission)."""
	if channel is not None:
		if isinstance(channel, discord.abc.Messageable):
			channel_id = str(channel.id)
		else:
			response = "not a valid channel."
			await ctx.respond(response, ephemeral=hidden)
			return
	else:
		channel_id = str(ctx.channel_id)

	guild_id = str(ctx.guild_id)

	if guild_id not in frf.bot_data.bot_channels:
		frf.bot_data.bot_channels.update({guild_id: []})

	if channel_id not in frf.bot_data.bot_channels[guild_id]:
		frf.bot_data.bot_channels[guild_id].append(channel_id)
		frf.bot_data.save(frf.BOT_DATA_PATH)
		response = f"successfully added channel ({channel_id})"
	else:
		response = f"channel is already a bot channel ({channel_id})"

	await ctx.respond(response, ephemeral=hidden)


@bot_channel_group.command(name="remove")
@discord.default_permissions(manage_guild=True)
@discord.option(
	"channel",
	discord.SlashCommandOptionType.channel,
	desrciption="The channel to remove (default: (current channel))",
)
@discord.option("hidden", bool, description="Only visible for you (default: No)")
async def remove_bot_channel(
	ctx: discord.ApplicationContext,
	channel: discord.abc.GuildChannel | discord.abc.Messageable | None = None,
	*,
	hidden: bool = False,
) -> None:
	"""Remove the channel as a bot channel (requires Manage Server permission)."""
	if channel is not None:
		if isinstance(channel, discord.abc.Messageable):
			channel_id = str(channel.id)
		else:
			response = "not a valid channel."
			await ctx.respond(response, ephemeral=hidden)
			return
	else:
		channel_id = str(ctx.channel_id)

	guild_id = str(ctx.guild_id)

	if guild_id not in frf.bot_data.bot_channels:
		frf.bot_data.bot_channels.update({guild_id: []})

	if channel_id in frf.bot_data.bot_channels[guild_id]:
		frf.bot_data.bot_channels[guild_id].remove(channel_id)
		frf.bot_data.save(frf.BOT_DATA_PATH)
		response = f"successfully removed channel ({channel_id})"
	else:
		response = f"channel is not a bot channel ({channel_id})"

	await ctx.respond(response, ephemeral=hidden)


@bot_channel_group.command(name="removeall")
@discord.default_permissions(manage_guild=True)
@discord.option("hidden", bool, description="Only visible for you (default: No)")
async def remove_all_bot_channels(
	ctx: discord.ApplicationContext, *, hidden: bool = False
) -> None:
	"""Remove all channels as a bot channel (requires Manage Server permission)."""
	guild_id = str(ctx.guild_id)

	if guild_id not in frf.bot_data.bot_channels:
		frf.bot_data.bot_channels.update({guild_id: []})

	if len(frf.bot_data.bot_channels[guild_id]) > 0:
		frf.bot_data.bot_channels[guild_id].clear()
		frf.bot_data.save(frf.BOT_DATA_PATH)
		response = "successfully removed all channels"
	else:
		response = "server has no bot channels"

	await ctx.respond(response, ephemeral=hidden)


@bot.slash_command(name="test")
async def test_command(ctx: discord.ApplicationContext) -> None:
	"""Test command."""
	await ctx.respond("<:look2:1270758550695837706>")


def parse_arguments() -> None:
	"""Parse command line arguments."""
	parser = argparse.ArgumentParser(
		prog="Fractal-RHOMB", description="Discord bot for fractalthorns.com"
	)
	parser.add_argument(
		"-V",
		"--version",
		action="version",
		version="%(prog)s 0.2.0",
	)
	parser.add_argument(
		"-v",
		"--verbose",
		action="store_true",
		help="verbose logging for the bot (info)",
	)
	parser.add_argument(
		"-vv",
		"--more-verbose",
		action="store_true",
		help="even more verbose logging for the bot (debug). overrides --verbose",
	)
	parser.add_argument(
		"-rv",
		"--root-verbose",
		action="store_true",
		help="verbose logging for everything (info)",
	)
	parser.add_argument(
		"-rvv",
		"--root-more-verbose",
		action="store_true",
		help="even more verbose logging for everything (debug). overrides --root-verbose",
	)
	parser.add_argument(
		"--log-level",
		choices=["none", "critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for the bot. overrides --verbose and --more-verbose. if not set, uses root log level",
		default=None,
	)
	parser.add_argument(
		"--root-log-level",
		choices=["none", "critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for everything. overrides --root-verbose and --root-more-verbose. default: warning",
		default=None,
	)
	args = parser.parse_args()

	root_logger = logging.getLogger()

	if args.verbose:
		discord_logger.setLevel(logging.INFO)
	if args.root_verbose:
		root_logger.setLevel(logging.INFO)

	if args.more_verbose:
		discord_logger.setLevel(logging.DEBUG)
	if args.root_more_verbose:
		root_logger.setLevel(logging.DEBUG)

	if args.log_level is not None:
		args.log_level = args.log_level.upper()

		if args.log_level == "NONE":
			discord_logger.setLevel(logging.CRITICAL + 10)
		else:
			discord_logger.setLevel(args.log_level)

	if args.root_log_level is not None:
		args.root_log_level = args.root_log_level.upper()

		if args.root_log_level == "NONE":
			root_logger.setLevel(logging.CRITICAL + 10)
		else:
			root_logger.setLevel(args.root_log_level)


def main() -> None:
	"""Do main."""
	parse_arguments()

	try:
		frf.bot_data.load(frf.BOT_DATA_PATH)
	except Exception:
		discord_logger.exception("Could not load bot data.")

	bot.load_extension("cogs.fractalthorns")

	token = getenv("DISCORD_BOT_TOKEN")
	bot.run(token)


if __name__ == "__main__":
	main()
