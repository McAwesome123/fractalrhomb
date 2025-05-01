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
from pathlib import Path

import aiohttp
import aiohttp.client_exceptions as client_exc
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
fractalrhomb_logger = logging.getLogger("fractalrhomb")
root_logger = logging.getLogger()


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
	allowed = json.loads(getenv("BOT_ADMIN_USERS", "[]"))

	if message.content.startswith("-say"):
		if user_id not in allowed:
			fractalrhomb_logger.info(
				"User %s tried to use -say, but is not part of %s", user_id, allowed
			)
			return

		await say_message_command(message)

	if message.content.startswith("-status"):
		if user_id not in allowed:
			fractalrhomb_logger.info(
				"User %s tried to use -status, but is not part of %s", user_id, allowed
			)
			return

		await change_status_command(message)

	if message.content.startswith("-botdata"):
		if user_id not in allowed:
			fractalrhomb_logger.info(
				"User %s tried to use -botdata, but is not part of %s", user_id, allowed
			)
			return

		await bot_data_command(message)


async def say_message_command(message: discord.Message) -> None:
	"""Send a message in a specified channel."""
	args = message.content.split(" ", 2)

	fractalrhomb_logger.debug(
		"Received -say command: %s. Parsed as: %s.", message.content, args
	)

	if len(args) < 3:  # noqa: PLR2004
		fractalrhomb_logger.debug("Command did not receive enough arguments.")
		return

	channel = args[1]
	content = args[2]

	fractalrhomb_logger.debug(
		"Parsed channel as %s and content as %s.", channel, content
	)

	try:
		discord_channel = bot.get_channel(int(channel))
		if discord_channel is None:
			fractalrhomb_logger.debug("%s is not a valid channel.", channel)
			return
	except ValueError:
		fractalrhomb_logger.debug("%s is not a channel id.", channel)
		return

	await discord_channel.send(content)


async def change_status_command(message: discord.Message) -> None:
	"""Change the bot's status."""
	args = message.content.split(" ", 1)

	fractalrhomb_logger.debug(
		"Received -status command: %s. Parsed as: %s.", message.content, args
	)

	if len(args) < 2:  # noqa: PLR2004
		fractalrhomb_logger.debug("Did not receive enough arguments.")
		return

	content = args[1]
	if content.lower() == "clear":
		await bot.change_presence()
		frg.bot_data.status = ""
		await frg.bot_data.save(frg.BOT_DATA_PATH)
		return
	if content.strip("\\").lower() == "clear":
		content = content[1:]

	await bot.change_presence(activity=discord.CustomActivity(content))

	frg.bot_data.status = content
	await frg.bot_data.save(frg.BOT_DATA_PATH)


async def bot_data_command(message: discord.Message) -> None:
	"""Save or reload bot data."""
	args = message.content.split(" ", 2)

	fractalrhomb_logger.debug(
		"Received -botdata command: %s. Parsed as: %s.", message.content, args
	)

	if len(args) < 2:  # noqa: PLR2004
		fractalrhomb_logger.debug("Command did not receive enough arguments.")
		return

	action = args[1]

	fractalrhomb_logger.debug("Parsed action as %s.", action)

	match action:
		case "save":
			await frg.bot_data.save(frg.BOT_DATA_PATH)
		case "load":
			await frg.bot_data.load(frg.BOT_DATA_PATH)
		case "reload":
			await frg.bot_data.load(frg.BOT_DATA_PATH)
		case _:
			fractalrhomb_logger.debug("Action is not valid.")


@bot.event
async def on_application_command_error(
	ctx: discord.ApplicationContext, error: Exception
) -> None:
	"""Do stuff when there's a command error."""
	response = "an unhandled exception occurred"
	await frg.send_message(ctx, response)
	raise error


@bot.slash_command(description="Pong!")
async def ping(ctx: discord.ApplicationContext) -> None:
	"""Pong."""
	fractalrhomb_logger.info(
		"Ping command used. Latency: %s ms", round(bot.latency * 1000)
	)

	response = f"pong! latency: {f"{round(bot.latency * 1000)!s}ms"}."
	await frg.send_message(ctx, response)


@bot.slash_command(name="license")
async def show_license(ctx: discord.ApplicationContext) -> None:
	"""Display the bot's license message."""
	fractalrhomb_logger.info("License command used")

	license_text = (
		">>> fractalrhomb\n"
		"Copyright (C) 2024 [McAwesome](<https://github.com/McAwesome123>)\n"
		"\n"
		"The [source code](<https://github.com/McAwesome123/fractal-rhomb>) is licensed under the [GNU AGPL version 3](<https://www.gnu.org/licenses/agpl-3.0.en.html>) or later.\n"
		"\n"
		"[fractalthorns](<https://fractalthorns.com>) is created by [Pierce Smith](<https://github.com/pierce-smith1>)."
	)
	await frg.send_message(ctx, license_text)


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
	fractalrhomb_logger.info("Purge command used (cache=%s, force=%s)", cache, force)

	user = str(ctx.author.id)

	if force:
		force_purge_allowed = json.loads(getenv("BOT_ADMIN_USERS"))

		if user not in force_purge_allowed:
			fractalrhomb_logger.warning("Unauthorized force purge attempt by %s.", user)

			response = "you cannot do that."
			await frg.send_message(ctx, response)
			return

	if cache == "all":
		await purge_all(ctx, force=force)
		return

	cache = FractalthornsAPI.CacheTypes(cache)

	if force:
		fractalthorns_api.purge_cache(cache, force_purge=True)

		fractalrhomb_logger.info('"%s" force purged by %s.', cache.value, ctx.author.id)

		response = f"successfully force purged {cache.value}"
		await frg.send_message(ctx, response)
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
			response = f"you cannot do that. try again <t:{ceil(time)}:R>"
			await frg.send_message(ctx, response)
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
		await frg.send_message(ctx, response)

	else:
		response = f"successfully purged {cache.value}"
		await frg.send_message(ctx, response)

		if str(ctx.author.id) not in frg.bot_data.purge_cooldowns:
			frg.bot_data.purge_cooldowns.update({str(ctx.author.id): {}})
		frg.bot_data.purge_cooldowns[str(ctx.author.id)].update(
			{cache.value: dt.datetime.now(dt.UTC).timestamp()}
		)
		try:
			await frg.bot_data.save(frg.BOT_DATA_PATH)
		except Exception:
			fractalrhomb_logger.exception("Could not save bot data.")


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

		fractalrhomb_logger.info("All caches force purged by %s.", user)

		response = "successfully force purged all caches"
		await frg.send_message(ctx, response)
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
		response = f"successfully purged {", ".join(purged)}"
		await frg.send_message(ctx, response)

		fractalrhomb_logger.info(
			"%s purged by %s.", ('", "'.join(purged)), ctx.author.id
		)

		try:
			await frg.bot_data.save(frg.BOT_DATA_PATH)
		except Exception:
			fractalrhomb_logger.exception("Could not save bot data.")
	else:
		earliest = min(cooldown, key=cooldown.get)

		response = f"could not purge any caches.\nearliest available: '{earliest.value}' <t:{ceil(cooldown[earliest])}:R>"
		await frg.send_message(ctx, response)


bot_channel_group = bot.create_group(
	"channel",
	"Manage special channels.",
	contexts={discord.InteractionContextType.guild},
	integration_types=[discord.IntegrationType.guild_install],
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
	fractalrhomb_logger.info(
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
	fractalrhomb_logger.info(
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
	fractalrhomb_logger.info(
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
	fractalrhomb_logger.info("Test command used")
	await ctx.respond(getenv("LOOK2_EMOJI", ":look2:"))


@bot.slash_command(
	name="restart-notification-listener",
	contexts={discord.InteractionContextType.bot_dm},
)
async def restart_notification_listener(ctx: discord.ApplicationContext) -> None:
	"""Restart the notification listener (command restricted to certain users)."""
	privileged_users = json.loads(getenv("BOT_ADMIN_USERS", "[]"))

	user_id = str(ctx.author.id)
	if user_id not in privileged_users:
		fractalrhomb_logger.warning(
			"Unauthorized notif listener restart attempt by %s.", user_id
		)
		response = "you cannot do that."
		await frg.send_message(ctx, response)
		return

	ft_notifs.resume_event.set()
	ft_notifs.resume_done_event.clear()

	try:
		await ctx.defer()
		await asyncio.wait_for(ft_notifs.resume_done_event.wait(), timeout=5.0)
	except TimeoutError:
		response = "listener didn't restart - it either didn't need restarting or is slow/dead."
		await frg.send_message(ctx, response, is_deferred=True)
	else:
		response = "listener has been restarted."
		await frg.send_message(ctx, response, is_deferred=True)

	ft_notifs.resume_event.clear()


@bot.slash_command(
	name="manual-news-post", contexts={discord.InteractionContextType.bot_dm}
)
@discord.option(
	"test", bool, description="Sends the post to just you instead of news channels."
)
async def manual_news_post(ctx: discord.ApplicationContext, *, test: bool) -> None:
	"""Fetch the latest news entry and send it to all news channels (command restricted to certain users)."""
	privileged_users = json.loads(getenv("BOT_ADMIN_USERS", "[]"))

	user_id = str(ctx.author.id)
	if user_id not in privileged_users:
		fractalrhomb_logger.warning(
			"Unauthorized notif listener restart attempt by %s.", user_id
		)
		response = "you cannot do that."
		await frg.send_message(ctx, response)
		return

	if not test:
		confirmation = frg.BotWarningView()
		await ctx.respond(
			"❗ this will post the latest news entry in all news tagged channels. are you sure?",
			view=confirmation,
			ephemeral=True,
		)
		await confirmation.wait()

		if not confirmation.value:
			return

	try:
		fractalthorns_api.purge_cache(
			fractalthorns_api.CacheTypes.NEWS_ITEMS, force_purge=True
		)
		news = await fractalthorns_api.get_all_news(frg.session)
		news = news[0]

		if test:
			fractalrhomb_logger.debug(
				"Trying to make a test news post in channel %s.", ctx.channel_id
			)
			await ctx.respond(news.format(), ephemeral=True)
		else:
			fractalrhomb_logger.info(
				"Sending news item to be posted by the notification handler."
			)
			await ft_notifs.post_news_update(news)

		tasks = set()
		async with asyncio.TaskGroup() as tg:
			task = tg.create_task(
				fractalthorns_api.save_cache(fractalthorns_api.CacheTypes.NEWS_ITEMS)
			)
			tasks.add(task)
			task.add_done_callback(tasks.discard)

			task = tg.create_task(
				fractalthorns_api.save_cache(
					fractalthorns_api.CacheTypes.CACHE_METADATA
				)
			)
			tasks.add(task)
			task.add_done_callback(tasks.discard)

	except* (TimeoutError, client_exc.ClientError) as exc:
		await frg.standard_exception_handler(
			ctx, fractalrhomb_logger, exc, "Fractalrhomb.manual_news_post"
		)


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
		help="verbose logging for everything (info)",
	)
	parser.add_argument(
		"-vv",
		"--more-verbose",
		action="store_true",
		help="even more verbose logging for everything (debug). overrides --root-verbose",
	)
	parser.add_argument(
		"-dv",
		"--discord-verbose",
		action="store_true",
		help="verbose logging for discord operations (info)",
	)
	parser.add_argument(
		"-dvv",
		"--discord-more-verbose",
		action="store_true",
		help="even more verbose logging for discord operations (debug). overrides --discord-verbose",
	)
	parser.add_argument(
		"-bv",
		"--bot-verbose",
		action="store_true",
		help="verbose logging for the bot (info)",
	)
	parser.add_argument(
		"-bvv",
		"--bot-more-verbose",
		action="store_true",
		help="even more verbose logging for the bot (debug). overrides --bot-verbose",
	)
	parser.add_argument(
		"--log-level",
		choices=["none", "critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for everything (root). overrides --verbose and --more-verbose. default: warning",
		default=None,
	)
	parser.add_argument(
		"--discord-log-level",
		choices=["none", "critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for discord operations. overrides --discord-verbose and --discord-more-verbose. if not set, uses root log level.",
		default=None,
	)
	parser.add_argument(
		"--bot-log-level",
		choices=["none", "critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for the bot. overrides --bot-verbose and --bot-more-verbose. if not set, uses root log level.",
		default=None,
	)
	parser.add_argument(
		"--log-console",
		dest="log_to_console",
		action="store_true",
		help="output logs to console (stderr)",
	)
	parser.add_argument(
		"--console-log-level",
		choices=["critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for logging messages to console. does nothing if used without --log-console. if not set, logs everything.",
		default="notset",
	)
	parser.add_argument(
		"--no-log-file",
		dest="log_to_file",
		action="store_false",
		help="don't output logs to a file",
	)
	parser.add_argument(
		"--file-log-level",
		choices=["critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for logging messages to file. does nothing if used with --no-log-file. if not set, logs everything.",
		default="notset",
	)
	args = parser.parse_args()

	if args.verbose:
		root_logger.setLevel(logging.INFO)
	if args.discord_verbose:
		discord_logger.setLevel(logging.INFO)
	if args.bot_verbose:
		fractalrhomb_logger.setLevel(logging.INFO)

	if args.more_verbose:
		root_logger.setLevel(logging.DEBUG)
	if args.discord_more_verbose:
		discord_logger.setLevel(logging.DEBUG)
	if args.bot_more_verbose:
		fractalrhomb_logger.setLevel(logging.DEBUG)

	if args.log_level is not None:
		args.log_level = args.log_level.upper()

		if args.log_level == "NONE":
			root_logger.setLevel(logging.CRITICAL + 10)
		else:
			root_logger.setLevel(args.log_level)

	if args.discord_log_level is not None:
		args.discord_log_level = args.discord_log_level.upper()

		if args.discord_log_level == "NONE":
			discord_logger.setLevel(logging.CRITICAL + 10)
		else:
			discord_logger.setLevel(args.discord_log_level)

	if args.bot_log_level is not None:
		args.bot_log_level = args.bot_log_level.upper()

		if args.bot_log_level == "NONE":
			fractalrhomb_logger.setLevel(logging.CRITICAL + 10)
		else:
			fractalrhomb_logger.setLevel(args.bot_log_level)

	dt_fmt = "%Y-%m-%d %H:%M:%S"
	log_formatter = logging.Formatter(
		"[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
	)

	if args.log_to_file:
		log_file_name = getenv("LOG_FILE_NAME", "discord.log")
		log_file_when = getenv("LOG_FILE_WHEN", "midnight")
		log_file_interval = getenv("LOG_FILE_INTERVAL", "1")
		log_file_backup_count = getenv("LOG_FILE_BACKUP_COUNT", "7")
		log_file_at_time = getenv("LOG_FILE_AT_TIME", "00:00:00Z")

		log_file_interval = int(log_file_interval)
		log_file_backup_count = int(log_file_backup_count)
		log_file_utc = "Z" in log_file_at_time
		log_file_at_time = dt.time.fromisoformat(log_file_at_time)

		log_file_handler = logging.handlers.TimedRotatingFileHandler(
			filename=log_file_name,
			when=log_file_when,
			interval=log_file_interval,
			backupCount=log_file_backup_count,
			encoding="utf-8",
			utc=log_file_utc,
			atTime=log_file_at_time,
		)
		log_file_handler.setFormatter(log_formatter)

		log_file_handler.setLevel(args.file_log_level.upper())

		root_logger.addHandler(log_file_handler)

	if args.log_to_console:
		log_stream_handler = logging.StreamHandler()
		log_stream_handler.setFormatter(log_formatter)
		log_stream_handler.setLevel(args.console_log_level.upper())
		root_logger.addHandler(log_stream_handler)


async def main() -> None:
	"""Do main."""
	parse_arguments()

	try:
		await frg.bot_data.load(frg.BOT_DATA_PATH)
	except Exception:
		fractalrhomb_logger.exception("Could not load bot data.")

	activity_text = frg.bot_data.status
	if activity_text is not None:
		bot.activity = discord.CustomActivity(
			activity_text,
			emoji=frg.activity_emoji,
		)

	conn = aiohttp.TCPConnector(limit_per_host=6)

	async with aiohttp.ClientSession(connector=conn) as frg.session:
		bot.load_extension("cogs.fractalthorns")
		if (
			Path("aetol/particle_dictionary.tsv").exists()
			or Path("aetol/word_dictionary.tsv").exists()
		):
			bot.load_extension("cogs.aetol")

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
