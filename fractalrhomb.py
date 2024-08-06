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
import re
from dataclasses import asdict, dataclass
from math import ceil
from os import getenv
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.fractalthorns_api import FractalthornsAPI, fractalthorns_api
from src.fractalthorns_exceptions import CachePurgeError

load_dotenv()

discord_logger = logging.getLogger("discord")

log_handler = logging.handlers.RotatingFileHandler(
	filename="discord.log", mode="w", encoding="utf-8", backupCount=10
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
log_formatter = logging.Formatter(
	"[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
log_handler.setFormatter(log_formatter)
discord_logger.addHandler(log_handler)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)


@dataclass
class BotData:
	"""Data class containing bot data/config."""

	bot_channels: list[str]
	purge_cooldowns: dict[str, dict[str, float]]

	def load(self, fp: Path) -> None:
		"""Load data from file."""
		if not fp.exists():
			return

		with fp.open("r") as f:
			data = json.load(f)
			if data.get("bot_channels") is not None:
				self.bot_channels = data["bot_channels"]
			if data.get("purge_cooldowns") is not None:
				self.purge_cooldowns = data["purge_cooldowns"]

	def save(self, fp: Path) -> None:
		"""Save data to file."""
		if fp.exists():
			backup = Path(f"{fp.resolve().as_posix()}.bak")
			fp.replace(backup)
		with fp.open("w") as f:
			json.dump(asdict(self), f)


bot_data = BotData([], {})

USER_PURGE_COOLDOWN = dt.timedelta(hours=12)
BOT_DATA_PATH = Path("bot_data.json")


@bot.event
async def on_ready() -> None:
	"""Do stuff when the bot finishes logging in."""
	print(f"Logged in as {bot.user}")


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
	"""Do stuff when there's a command error."""
	response = ""

	if isinstance(error, commands.CommandNotFound):
		response = f"i don't know what you mean by '{ctx.invoked_with}'"
	elif isinstance(error, commands.CommandOnCooldown):
		response = f"```\n{error}\n```"
	elif isinstance(error, commands.BadArgument):
		matches = re.compile(r'(?<=")[^"]*(?=")').findall(
			str(error)
		)  # this is cursed (it's a search for things in quotes)
		if len(matches) > 0:
			response = f"bad value for parameter '{matches[-1]}'"
		else:
			response = "bad value for parameter"
	else:
		response = "an unhandled exception occurred"
		await ctx.send(response)
		raise error

	await ctx.send(response)


@bot.command(help="Pong!")
async def ping(ctx: commands.Context) -> None:
	"""Pong."""
	response = "```\nPong!\n```"
	await ctx.send(response)


@bot.command(name="license")
async def show_license(ctx: commands.Context) -> None:
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
	await ctx.send(license_text)


@bot.command()
async def purge(ctx: commands.Context, *, cache: FractalthornsAPI.CacheTypes) -> None:
	"""Purge the bot's cache.

	Arguments:
	---------
	  cache Which cache to purge. Must be one of the following:
	        news, images, image contents, image descriptions,
	        chapters, records, record contents, search results.
	"""
	user = bot_data.purge_cooldowns.get(str(ctx.author.id))
	if user is not None:
		time = user.get(cache.value)
		if (
			time is not None
			and dt.datetime.now(dt.UTC)
			< dt.datetime.fromtimestamp(time, dt.UTC) + USER_PURGE_COOLDOWN
		):
			time += USER_PURGE_COOLDOWN.total_seconds()
			response = f"you cannot do that. try again <t:{ceil(time)}:R>"
			await ctx.send(response)
			return
	try:
		fractalthorns_api.purge_cache(cache)

	except CachePurgeError as exc:
		response = f"could not purge the cache: {exc.args[0].lower()}\ntry again <t:{ceil(exc.args[1].timestamp())}:R>"
		await ctx.send(response)

	else:
		response = f"successfully purged {cache.value}"
		await ctx.send(response)

		if str(ctx.author.id) not in bot_data.purge_cooldowns:
			bot_data.purge_cooldowns.update({str(ctx.author.id): {}})
		bot_data.purge_cooldowns[str(ctx.author.id)].update(
			{cache.value: dt.datetime.now(dt.UTC).timestamp()}
		)
		try:
			bot_data.save(BOT_DATA_PATH)
		except Exception:
			discord_logger.exception("Could not save bot data.")


@bot.command(hidden=True, aliases=["purgeall"])
async def purge_all(ctx: commands.Context) -> None:
	"""Purge the bot's entire cache.

	Does NOT purge "full record contents".
	"""
	user = bot_data.purge_cooldowns.get(str(ctx.author.id))
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
				< dt.datetime.fromtimestamp(time, dt.UTC) + USER_PURGE_COOLDOWN
			):
				cooldown.update({cache: time + USER_PURGE_COOLDOWN.total_seconds()})
				continue

		try:
			fractalthorns_api.purge_cache(cache)
		except CachePurgeError as exc:
			if len(exc.args) > 1:
				cooldown.update({cache: exc.args[1].timestamp()})
		else:
			purged.append(cache.value)

			if str(ctx.author.id) not in bot_data.purge_cooldowns:
				bot_data.purge_cooldowns.update({str(ctx.author.id): {}})
			bot_data.purge_cooldowns[str(ctx.author.id)].update(
				{cache.value: dt.datetime.now(dt.UTC).timestamp()}
			)

	if len(purged) > 0:
		response = f"successfully purged {", ".join(purged)}"
		await ctx.send(response)

		try:
			bot_data.save(BOT_DATA_PATH)
		except Exception:
			discord_logger.exception("Could not save bot data.")
	else:
		discord_logger.debug(cooldown)
		earliest = min(cooldown, key=cooldown.get)

		response = f"could not purge any caches.\nearliest available: '{earliest.value}' <t:{ceil(cooldown[earliest])}:R>"
		await ctx.send(response)


@bot.command(hidden=True, aliases=["forcepurge"])
async def force_purge(
	ctx: commands.Context, *, cache: FractalthornsAPI.CacheTypes
) -> None:
	"""Force purge the bot's cache, regardless of cooldowns.

	Limited to specific users.
	"""
	force_purge_allowed = json.loads(getenv("FORCE_PURGE_ALLOWED"))

	if str(ctx.author.id) in force_purge_allowed:
		fractalthorns_api.purge_cache(cache, force_purge=True)

		msg = f"'{cache.value}' purged by {ctx.author.id}."
		discord_logger.info(msg)

		response = f"successfully force purged {cache.value}"
		await ctx.send(response)
	else:
		msg = f"Unauthorized force purge attempt by {ctx.author.id}."
		discord_logger.info(msg)

		response = "you cannot do that."
		await ctx.send(response)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog="Fractal-RHOMB", description="Discord bot for fractalthorns.com"
	)
	parser.add_argument("-V", "--version", action="version", version="%(prog)s 0.2.0")
	parser.add_argument(
		"-v", "--verbose", action="store_true", help="verbose logging for the bot"
	)
	parser.add_argument(
		"-rv",
		"--root-verbose",
		action="store_true",
		help="verbose logging for everything",
	)
	parser.add_argument(
		"--log-level",
		choices=["none", "critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for the bot. this is ignored when using --verbose. if not set, uses root log level",
		default="notset",
	)
	parser.add_argument(
		"--root-log-level",
		choices=["none", "critical", "error", "warning", "info", "debug", "notset"],
		help="set a log level for everything. this is ignored when using --root-verbose. default: warning",
		default="warning",
	)
	args = parser.parse_args()

	root_logger = logging.getLogger()

	args.log_level = args.log_level.upper()
	args.root_log_level = args.root_log_level.upper()

	if args.log_level == "NONE":
		discord_logger.setLevel(logging.CRITICAL + 10)
	else:
		discord_logger.setLevel(args.log_level)

	if args.root_log_level == "NONE":
		root_logger.setLevel(logging.CRITICAL + 10)
	else:
		root_logger.setLevel(args.root_log_level)

	if args.verbose:
		discord_logger.setLevel(logging.DEBUG)
	if args.root_verbose:
		root_logger.setLevel(logging.DEBUG)

	try:
		bot_data.load(BOT_DATA_PATH)
	except Exception:
		discord_logger.exception("Could not load bot data.")

	bot.load_extension("cogs.fractalthorns")

	token = getenv("DISCORD_BOT_TOKEN")
	bot.run(token)
