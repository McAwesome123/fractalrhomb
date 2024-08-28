# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module containing bot logic."""

import argparse
import asyncio
import contextlib
import datetime as dt
import json
import logging
import logging.handlers
from math import ceil
from os import getenv

import aiohttp
import discord
import discord.utils
from dotenv import load_dotenv

import src.fractalrhomb_globals as frg
from src.fractalrhomb_globals import bot
from src.fractalthorns_api import FractalthornsAPI, fractalthorns_api
from src.fractalthorns_exceptions import CachePurgeError

load_dotenv()

discord_logger = logging.getLogger("discord")
root_logger = logging.getLogger()

log_handler = logging.handlers.TimedRotatingFileHandler(
	filename="discord.log", when="midnight", backupCount=7, encoding="utf-8", utc=True
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
log_formatter = logging.Formatter(
	"[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
log_handler.setFormatter(log_formatter)
root_logger.addHandler(log_handler)

PING_LATENCY_HIGH = 10.0


@bot.event
async def on_ready() -> None:  # noqa: RUF029
	"""Do stuff when the bot finishes logging in."""
	print(f"Logged in as {bot.user}")


@bot.listen("on_message")
async def private_commands(message: discord.Message) -> None:
	"""Parse private commands."""
	if message.author == bot.user:
		return

	if message.channel.type != discord.ChannelType.private:
		return

	user_id = str(message.author.id)

	if message.content.startswith("-say"):
		allowed = json.loads(getenv("SAY_COMMAND_ALLOWED", "[]"))
		if user_id not in allowed:
			msg = f"User {user_id} tried to use -say, but is not part of {allowed}"
			discord_logger.info(msg)
			return

		await say_message_command(message)

	if message.content.startswith("-status"):
		allowed = json.loads(getenv("STATUS_COMMAND_ALLOWED", "[]"))
		if user_id not in allowed:
			msg = f"User {user_id} tried to use -status, but is not part of {allowed}"
			discord_logger.info(msg)
			return

		await change_status_command(message)


async def say_message_command(message: discord.Message) -> None:
	"""Send a message in a specified channel."""
	args = message.content.split(" ", 2)

	msg = f"Received -say command: {message.content}. Parsed as: {args}."
	discord_logger.debug(msg)

	if len(args) < 3:  # noqa: PLR2004
		msg = "Command did not receive enough arguments."
		discord_logger.debug(msg)
		return

	channel = args[1]
	content = args[2]

	msg = f"Parsed channel as {channel} and content as {content}."
	discord_logger.debug(msg)

	try:
		discord_channel = bot.get_channel(int(channel))
		if discord_channel is None:
			msg = f"{channel} is not a valid channel."
			discord_logger.debug(msg)
			return
	except ValueError:
		msg = f"{channel} is not a channel id."
		discord_logger.debug(msg)
		return

	await discord_channel.send(content)


async def change_status_command(message: discord.Message) -> None:
	"""Change the bot's status."""
	args = message.content.split(" ", 1)

	msg = f"Received -status command: {message.content}. Parsed as: {args}."
	discord_logger.debug(msg)

	if len(args) < 2:  # noqa: PLR2004
		msg = "Did not receive enough arguments."
		discord_logger.debug(msg)
		return

	content = args[1]
	if content.lower() == "clear":
		await bot.change_presence()
		return
	if content.strip("\\").lower() == "clear":
		content = content[1:]

	await bot.change_presence(activity=discord.CustomActivity(content))


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
	if bot.latency < PING_LATENCY_HIGH:
		latency = f"{round(bot.latency * 1000)!s}ms"
	else:
		latency = f"{round(bot.latency, 2)!s}s"

	response = f"pong! latency: {latency}."
	await ctx.respond(response)


@bot.slash_command(name="license")
async def show_license(ctx: discord.ApplicationContext) -> None:
	"""Display the bot's license message."""
	license_text = (
		">>> fractalrhomb\n"
		"Copyright (C) 2024 [McAwesome](<https://github.com/McAwesome123>)\n"
		"\n"
		"The [source code](<https://github.com/McAwesome123/fractal-rhomb>) is licensed under the [GNU AGPL version 3](<https://www.gnu.org/licenses/agpl-3.0.en.html>) or later.\n"
		"\n"
		"[fractalthorns](<https://fractalthorns.com>) is created by [Pierce Smith](<https://github.com/pierce-smith1>)."
	)
	await ctx.respond(license_text)


purge_group = bot.create_group("cache", "Manage the bot's cache.")


@purge_group.command(name="purge")
@discord.option(
	"cache",
	str,
	choices=[
		i.value
		for i in FractalthornsAPI.CacheTypes
		if i
		not in {
			FractalthornsAPI.CacheTypes.CACHE_METADATA,
			FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
		}
	],
)
async def purge(
	ctx: discord.ApplicationContext,
	cache: str,
) -> None:
	"""Purge the bot's cache."""
	cache = FractalthornsAPI.CacheTypes(cache)
	user = frg.bot_data.purge_cooldowns.get(str(ctx.author.id))
	if user is not None:
		time = user.get(cache.value)
		if (
			time is not None
			and dt.datetime.now(dt.UTC)
			< dt.datetime.fromtimestamp(time, dt.UTC) + frg.USER_PURGE_COOLDOWN
		):
			time += frg.USER_PURGE_COOLDOWN.total_seconds()
			response = f"you cannot do that. try again <t:{ceil(time)}:R>"
			await ctx.respond(response)
			return
	try:
		fractalthorns_api.purge_cache(cache)

	except CachePurgeError as exc:
		if exc.allowed_time is not None:
			response = f"could not purge the cache - {exc.reason}\ntry again <t:{ceil(exc.args[1].timestamp())}:R>"
		elif exc.reason is not None:
			response = f"could not purge the cache - {exc.reason}"
		else:
			response = "could not purge the cache"
		await ctx.respond(response)

	else:
		response = f"successfully purged {cache.value}"
		await ctx.respond(response)

		if str(ctx.author.id) not in frg.bot_data.purge_cooldowns:
			frg.bot_data.purge_cooldowns.update({str(ctx.author.id): {}})
		frg.bot_data.purge_cooldowns[str(ctx.author.id)].update(
			{cache.value: dt.datetime.now(dt.UTC).timestamp()}
		)
		try:
			await frg.bot_data.save(frg.BOT_DATA_PATH)
		except Exception:
			discord_logger.exception("Could not save bot data.")


@purge_group.command(name="purgeall")
async def purge_all(ctx: discord.ApplicationContext) -> None:
	"""Purge the bot's entire cache."""
	user = frg.bot_data.purge_cooldowns.get(str(ctx.author.id))
	purged = []
	cooldown = {}
	for cache in FractalthornsAPI.CacheTypes:
		if cache in {
			FractalthornsAPI.CacheTypes.CACHE_METADATA,
			FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
		}:
			continue

		if user is not None:
			time = user.get(cache.value)
			if (
				time is not None
				and dt.datetime.now(dt.UTC)
				< dt.datetime.fromtimestamp(time, dt.UTC) + frg.USER_PURGE_COOLDOWN
			):
				cooldown.update({cache: time + frg.USER_PURGE_COOLDOWN.total_seconds()})
				continue

		try:
			fractalthorns_api.purge_cache(cache)
		except CachePurgeError as exc:
			if exc.allowed_time is not None:
				cooldown.update({cache: exc.allowed_time.timestamp()})
		else:
			purged.append(cache.value)

			if str(ctx.author.id) not in frg.bot_data.purge_cooldowns:
				frg.bot_data.purge_cooldowns.update({str(ctx.author.id): {}})
			frg.bot_data.purge_cooldowns[str(ctx.author.id)].update(
				{cache.value: dt.datetime.now(dt.UTC).timestamp()}
			)

	if len(purged) > 0:
		response = f"successfully purged {", ".join(purged)}"
		await ctx.respond(response)

		msg = f"'{"', '".join(purged)} purged by {ctx.author.id}."
		discord_logger.info(msg)

		try:
			await frg.bot_data.save(frg.BOT_DATA_PATH)
		except Exception:
			discord_logger.exception("Could not save bot data.")
	else:
		earliest = min(cooldown, key=cooldown.get)

		response = f"could not purge any caches.\nearliest available: '{earliest.value}' <t:{ceil(cooldown[earliest])}:R>"
		await ctx.respond(response)


@purge_group.command(name="forcepurge")
@discord.option(
	"cache",
	str,
	choices=[
		i.value
		for i in FractalthornsAPI.CacheTypes
		if i
		not in {
			FractalthornsAPI.CacheTypes.CACHE_METADATA,
			FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
		}
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

		msg = f"'{cache.value}' force purged by {ctx.author.id}."
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

	if guild_id not in frg.bot_data.bot_channels:
		frg.bot_data.bot_channels.update({guild_id: []})

	if channel_id not in frg.bot_data.bot_channels[guild_id]:
		frg.bot_data.bot_channels[guild_id].append(channel_id)
		await frg.bot_data.save(frg.BOT_DATA_PATH)
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

	if guild_id not in frg.bot_data.bot_channels:
		frg.bot_data.bot_channels.update({guild_id: []})

	if channel_id in frg.bot_data.bot_channels[guild_id]:
		frg.bot_data.bot_channels[guild_id].remove(channel_id)
		await frg.bot_data.save(frg.BOT_DATA_PATH)
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

	if guild_id not in frg.bot_data.bot_channels:
		frg.bot_data.bot_channels.update({guild_id: []})

	if len(frg.bot_data.bot_channels[guild_id]) > 0:
		frg.bot_data.bot_channels[guild_id].clear()
		await frg.bot_data.save(frg.BOT_DATA_PATH)
		response = "successfully removed all channels"
	else:
		response = "server has no bot channels"

	await ctx.respond(response, ephemeral=hidden)


@bot.slash_command(name="test")
async def test_command(ctx: discord.ApplicationContext) -> None:
	"""Test command."""
	await ctx.respond(getenv("LOOK2_EMOJI", ":look2:"))


def parse_arguments() -> None:
	"""Parse command line arguments."""
	parser = argparse.ArgumentParser(
		prog="Fractal-RHOMB", description="Discord bot for fractalthorns.com"
	)
	parser.add_argument(
		"-V",
		"--version",
		action="version",
		version="%(prog)s 0.5.0",
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


async def main() -> None:
	"""Do main."""
	parse_arguments()

	try:
		await frg.bot_data.load(frg.BOT_DATA_PATH)
	except Exception:
		discord_logger.exception("Could not load bot data.")

	conn = aiohttp.TCPConnector(limit_per_host=6)

	async with aiohttp.ClientSession(connector=conn) as session:
		frg.session = session

		bot.load_extension("cogs.fractalthorns")

		token = getenv("DISCORD_BOT_TOKEN")
		async with bot:
			await bot.start(token)


if __name__ == "__main__":
	with contextlib.suppress(KeyboardInterrupt):
		asyncio.run(main())
