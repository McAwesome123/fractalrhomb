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
import src.fractalthorns_notifications as ft_notifs
from src.fractalrhomb_globals import FRACTALRHOMB_VERSION_FULL, bot
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
		allowed = json.loads(getenv("BOT_ADMIN_USERS", "[]"))
		if user_id not in allowed:
			discord_logger.info(
				"User %s tried to use -say, but is not part of %s", user_id, allowed
			)
			return

		await say_message_command(message)

	if message.content.startswith("-status"):
		allowed = json.loads(getenv("BOT_ADMIN_USERS", "[]"))
		if user_id not in allowed:
			discord_logger.info(
				"User %s tried to use -status, but is not part of %s", user_id, allowed
			)
			return

		await change_status_command(message)


async def say_message_command(message: discord.Message) -> None:
	"""Send a message in a specified channel."""
	args = message.content.split(" ", 2)

	discord_logger.debug(
		"Received -say command: %s. Parsed as: %s.", message.content, args
	)

	if len(args) < 3:  # noqa: PLR2004
		discord_logger.debug("Command did not receive enough arguments.")
		return

	channel = args[1]
	content = args[2]

	discord_logger.debug("Parsed channel as %s and content as %s.", channel, content)

	try:
		discord_channel = bot.get_channel(int(channel))
		if discord_channel is None:
			discord_logger.debug("%s is not a valid channel.", channel)
			return
	except ValueError:
		discord_logger.debug("%s is not a channel id.", channel)
		return

	await discord_channel.send(content)


async def change_status_command(message: discord.Message) -> None:
	"""Change the bot's status."""
	args = message.content.split(" ", 1)

	discord_logger.debug(
		"Received -status command: %s. Parsed as: %s.", message.content, args
	)

	if len(args) < 2:  # noqa: PLR2004
		discord_logger.debug("Did not receive enough arguments.")
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
	if ctx.response.is_done():
		await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
	else:
		await ctx.respond(response)
	raise error


@bot.slash_command(description="Pong!")
async def ping(ctx: discord.ApplicationContext) -> None:
	"""Pong."""
	frg.discord_logger.info(
		"Ping command used. Latency: %s ms", round(bot.latency * 1000)
	)

	await ctx.respond(f"pong! latency: {f"{round(bot.latency * 1000)!s}ms"}.")


@bot.slash_command(name="license")
async def show_license(ctx: discord.ApplicationContext) -> None:
	"""Display the bot's license message."""
	frg.discord_logger.info("License command used")

	license_text = (
		">>> fractalrhomb\n"
		"Copyright (C) 2024 [McAwesome](<https://github.com/McAwesome123>)\n"
		"\n"
		"The [source code](<https://github.com/McAwesome123/fractal-rhomb>) is licensed under the [GNU AGPL version 3](<https://www.gnu.org/licenses/agpl-3.0.en.html>) or later.\n"
		"\n"
		"[fractalthorns](<https://fractalthorns.com>) is created by [Pierce Smith](<https://github.com/pierce-smith1>)."
	)
	await ctx.respond(license_text)


@bot.slash_command(name="purge")
@discord.option(
	"cache",
	str,
	choices=[
		*[
			i.value
			for i in FractalthornsAPI.CacheTypes
			if i
			not in {
				FractalthornsAPI.CacheTypes.CACHE_METADATA,
				FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
				FractalthornsAPI.CacheTypes.IMAGE_DESCRIPTIONS,
			}
		],
		"all",
	],
	description="Which cache to purge?",
)
@discord.option(
	"force",
	bool,
	description="Ignore cooldowns (parameter restricted to certain users)",
)
async def purge(
	ctx: discord.ApplicationContext, cache: str, *, force: bool = False
) -> None:
	"""Purge the bot's cache."""
	frg.discord_logger.info("Purge command used (cache=%s, force=%s)", cache, force)

	user = str(ctx.author.id)

	if force:
		force_purge_allowed = json.loads(getenv("BOT_ADMIN_USERS"))

		if user not in force_purge_allowed:
			discord_logger.warning("Unauthorized force purge attempt by %s.", user)

			await ctx.respond("you cannot do that.")
			return

	if cache == "all":
		await purge_all(ctx, force=force)
		return

	cache = FractalthornsAPI.CacheTypes(cache)

	if force:
		fractalthorns_api.purge_cache(cache, force_purge=True)

		discord_logger.info('"%s" force purged by %s.', cache.value, ctx.author.id)

		await ctx.respond(f"successfully force purged {cache.value}")
		return

	user = frg.bot_data.purge_cooldowns.get(user)
	if user is not None:
		time = user.get(cache.value)
		if (
			time is not None
			and dt.datetime.now(dt.UTC)
			< dt.datetime.fromtimestamp(time, dt.UTC) + frg.USER_PURGE_COOLDOWN
		):
			time += frg.USER_PURGE_COOLDOWN.total_seconds()
			await ctx.respond(f"you cannot do that. try again <t:{ceil(time)}:R>")
			return
	try:
		fractalthorns_api.purge_cache(cache)

	except CachePurgeError as exc:
		if exc.allowed_time is not None:
			response = f"could not purge the cache - {exc.reason.lower()}\ntry again <t:{ceil(exc.args[1].timestamp())}:R>"
		elif exc.reason is not None:
			response = f"could not purge the cache - {exc.reason.lower()}"
		else:
			response = "could not purge the cache"
		await ctx.respond(response)

	else:
		await ctx.respond(f"successfully purged {cache.value}")

		if str(ctx.author.id) not in frg.bot_data.purge_cooldowns:
			frg.bot_data.purge_cooldowns.update({str(ctx.author.id): {}})
		frg.bot_data.purge_cooldowns[str(ctx.author.id)].update(
			{cache.value: dt.datetime.now(dt.UTC).timestamp()}
		)
		try:
			await frg.bot_data.save(frg.BOT_DATA_PATH)
		except Exception:
			discord_logger.exception("Could not save bot data.")


async def purge_all(ctx: discord.ApplicationContext, *, force: bool) -> None:
	"""Purge the bot's entire cache."""
	user = str(ctx.author.id)

	if force:
		for cache in FractalthornsAPI.CacheTypes:
			if cache in {
				FractalthornsAPI.CacheTypes.CACHE_METADATA,
				FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
				FractalthornsAPI.CacheTypes.FULL_IMAGE_DESCRIPTIONS,
			}:
				continue

			fractalthorns_api.purge_cache(cache, force_purge=True)

		discord_logger.info("All caches force purged by %s.", user)

		await ctx.respond("successfully force purged all caches")
		return

	user = frg.bot_data.purge_cooldowns.get(user)

	purged = []
	cooldown = {}
	for cache in FractalthornsAPI.CacheTypes:
		if cache in {
			FractalthornsAPI.CacheTypes.CACHE_METADATA,
			FractalthornsAPI.CacheTypes.FULL_RECORD_CONTENTS,
			FractalthornsAPI.CacheTypes.FULL_IMAGE_DESCRIPTIONS,
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
		await ctx.respond(f"successfully purged {", ".join(purged)}")

		discord_logger.info("%s purged by %s.", ('", "'.join(purged)), ctx.author.id)

		try:
			await frg.bot_data.save(frg.BOT_DATA_PATH)
		except Exception:
			discord_logger.exception("Could not save bot data.")
	else:
		earliest = min(cooldown, key=cooldown.get)

		await ctx.respond(
			f"could not purge any caches.\nearliest available: '{earliest.value}' <t:{ceil(cooldown[earliest])}:R>"
		)


bot_channel_group = bot.create_group(
	"channel",
	"Manage special channels.",
	contexts={discord.InteractionContextType.guild},
	default_member_permissions=discord.Permissions(manage_guild=True),
)


@bot_channel_group.command(name="set")
@discord.option(
	"type",
	str,
	choices=["bot", "news"],
	description="What type of channel to set it as",
	parameter_name="type_",
)
@discord.option(
	"channel",
	discord.SlashCommandOptionType.channel,
	description="The channel to add (default: (current channel))",
)
@discord.option("hidden", bool, description="Only visible for you (default: No)")
async def add_bot_channel(
	ctx: discord.ApplicationContext,
	type_: str,
	channel: discord.abc.GuildChannel | discord.abc.Messageable | None = None,
	*,
	hidden: bool = False,
) -> None:
	"""Mark a channel as a special type (requires Manage Server permission)."""
	frg.discord_logger.info(
		"Add special channel command used (type_=%s, channel=%s, hidden=%s)",
		type_,
		channel,
		hidden,
	)

	if channel is not None:
		if isinstance(channel, discord.abc.Messageable):
			channel_id = str(channel.id)
		else:
			await ctx.respond("not a valid channel", ephemeral=hidden)
			return
	else:
		channel_id = str(ctx.channel_id)

	match type_:
		case "bot":
			guild_id = str(ctx.guild_id)

			if guild_id not in frg.bot_data.bot_channels:
				frg.bot_data.bot_channels.update({guild_id: []})

			if channel_id not in frg.bot_data.bot_channels[guild_id]:
				frg.bot_data.bot_channels[guild_id].append(channel_id)
				await frg.bot_data.save(frg.BOT_DATA_PATH)
				response = f"successfully added bot channel ({channel_id})"
			else:
				response = f"channel is already a bot channel ({channel_id})"

		case "news":
			if channel_id not in frg.bot_data.news_post_channels:
				frg.bot_data.news_post_channels.append(channel_id)
				await frg.bot_data.save(frg.BOT_DATA_PATH)
				response = f"successfully added news channel ({channel_id})"
			else:
				response = f"channel is already a news channel ({channel_id})"

		case _:
			response = f"not a valid type ({type_})"

	await ctx.respond(response, ephemeral=hidden)


@bot_channel_group.command(name="clear")
@discord.option(
	"type",
	str,
	choices=["bot", "news"],
	description="What type of channel to clear it as",
	parameter_name="type_",
)
@discord.option(
	"channel",
	discord.SlashCommandOptionType.channel,
	description="The channel to remove (default: (current channel))",
)
@discord.option("hidden", bool, description="Only visible for you (default: No)")
async def remove_bot_channel(
	ctx: discord.ApplicationContext,
	type_: str,
	channel: discord.abc.GuildChannel | discord.abc.Messageable | None = None,
	*,
	hidden: bool = False,
) -> None:
	"""Unmark a channel as a special type (requires Manage Server permission)."""
	frg.discord_logger.info(
		"Remove special channel command used (type_=%s, channel=%s, hidden=%s)",
		type_,
		channel,
		hidden,
	)

	if channel is not None:
		if isinstance(channel, discord.abc.Messageable):
			channel_id = str(channel.id)
		else:
			await ctx.respond("not a valid channel", ephemeral=hidden)
			return
	else:
		channel_id = str(ctx.channel_id)

	match type_:
		case "bot":
			guild_id = str(ctx.guild_id)

			if guild_id not in frg.bot_data.bot_channels:
				frg.bot_data.bot_channels.update({guild_id: []})

			if channel_id in frg.bot_data.bot_channels[guild_id]:
				frg.bot_data.bot_channels[guild_id].remove(channel_id)
				await frg.bot_data.save(frg.BOT_DATA_PATH)
				response = f"successfully removed bot channel ({channel_id})"
			else:
				response = f"channel is not a bot channel ({channel_id})"

		case "news":
			if channel_id in frg.bot_data.news_post_channels:
				frg.bot_data.news_post_channels.remove(channel_id)
				await frg.bot_data.save(frg.BOT_DATA_PATH)
				response = f"successfully removed news channel ({channel_id})"
			else:
				response = f"channel is not a news channel ({channel_id})"

		case _:
			response = f"not a valid type ({type_})"

	await ctx.respond(response, ephemeral=hidden)


@bot_channel_group.command(name="clearall")
@discord.option(
	"type",
	str,
	choices=["bot", "news"],
	description="What type of channels to clear",
	parameter_name="type_",
)
@discord.option("hidden", bool, description="Only visible for you (default: No)")
async def remove_all_bot_channels(
	ctx: discord.ApplicationContext, type_: str, *, hidden: bool = False
) -> None:
	"""Unmark all channels as a special type (requires Manage Server permission)."""
	frg.discord_logger.info(
		"Remove all bot channels command used (type_=%s, hidden=%s)", type_, hidden
	)

	match type_:
		case "bot":
			guild_id = str(ctx.guild_id)

			if guild_id not in frg.bot_data.bot_channels:
				frg.bot_data.bot_channels.update({guild_id: []})

			if len(frg.bot_data.bot_channels[guild_id]) > 0:
				frg.bot_data.bot_channels[guild_id].clear()
				await frg.bot_data.save(frg.BOT_DATA_PATH)
				response = "successfully removed all bot channels"
			else:
				response = "server has no bot channels"

		case "news":
			if len(frg.bot_data.news_post_channels) > 0:
				frg.bot_data.news_post_channels.clear()
				await frg.bot_data.save(frg.BOT_DATA_PATH)
				response = "successfully removed all news channels"
			else:
				response = "server has no news channels"

		case _:
			response = f"not a valid type ({type_})"

	await ctx.respond(response, ephemeral=hidden)


@bot.slash_command(name="test")
async def test_command(ctx: discord.ApplicationContext) -> None:
	"""Test command."""
	frg.discord_logger.info("Test command used")
	await ctx.respond(getenv("LOOK2_EMOJI", ":look2:"))


@bot.slash_command(name="restart-notification-listener")
async def restart_notification_listener(ctx: discord.ApplicationContext) -> None:
	"""Restart the notification listener (command restricted to certain users)."""
	privileged_users = json.loads(getenv("BOT_ADMIN_USERS", "[]"))

	user_id = str(ctx.author.id)
	if user_id not in privileged_users:
		discord_logger.warning(
			"Unauthorized notif listener restart attempt by %s.", user_id
		)
		await ctx.respond("you cannot do that.")
		return

	ft_notifs.resume_event.set()
	await ctx.respond("listener has been restarted.")


def parse_arguments() -> None:
	"""Parse command line arguments."""
	parser = argparse.ArgumentParser(
		prog="Fractal-RHOMB", description="Discord bot for fractalthorns.com"
	)
	parser.add_argument(
		"-V",
		"--version",
		action="version",
		version=f"%(prog)s {FRACTALRHOMB_VERSION_FULL}",
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
			main_bot_task = asyncio.create_task(bot.start(token))
			notifs_listen_task = asyncio.create_task(
				ft_notifs.start_and_watch_notification_listener()
			)

			await asyncio.wait([main_bot_task, notifs_listen_task])


if __name__ == "__main__":
	with contextlib.suppress(KeyboardInterrupt):
		asyncio.run(main())
