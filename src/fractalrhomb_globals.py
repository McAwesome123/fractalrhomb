# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""General functions for the bot."""

import datetime as dt
import inspect
import json
import logging
import logging.handlers
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import aiofiles
import aiohttp
import aiohttp.client_exceptions as client_exc
import discord
import discord.utils

intents = discord.Intents.default()

activity_emoji = os.getenv("NXEYE_EMOJI")
if activity_emoji is not None:
	activity_emoji = discord.PartialEmoji.from_str(activity_emoji).to_dict()

activity = discord.CustomActivity(
	"observing you",
	emoji=activity_emoji,
)

command_integration = [
	discord.IntegrationType.guild_install,
	discord.IntegrationType.user_install,
]

bot = discord.Bot(
	intents=intents,
	activity=activity,
	default_command_integration_types=command_integration,
)

MAX_MESSAGE_LENGTH = 1950
USER_BOT_WARN_MESSAGE_LENGTH = MAX_MESSAGE_LENGTH * 4
EMPTY_MESSAGE = "give me something to show"
NO_ITEMS_MATCH_SEARCH = "no items match the requested parameters"
INTERACTION_TOO_MANY_FOLLOW_UP_MESSAGES_ERROR_CODE = 40094

# The full version number including anything extra.
FRACTALRHOMB_VERSION_FULL = "0.9.0"
# Version number with only Major, Minor, and Patch version.
FRACTALRHOMB_VERSION_LONG = "0.9.0"
# Verison number with only Major and Minor version.
FRACTALRHOMB_VERSION_SHORT = "0.9"

FRACTALTHORNS_USER_AGENT = os.getenv(
	"FRACTALTHORNS_USER_AGENT", "Fractal-RHOMB/{VERSION_SHORT}"
)
FRACTALTHORNS_USER_AGENT = (
	FRACTALTHORNS_USER_AGENT.replace("{VERSION_FULL}", FRACTALRHOMB_VERSION_FULL)
	.replace("{VERSION_LONG}", FRACTALRHOMB_VERSION_LONG)
	.replace("{VERSION_SHORT}", FRACTALRHOMB_VERSION_SHORT)
)


def regex_incorrectly_formatted(regex: str = "regex", is_or_are: str = "is") -> str:
	"""Get a string for reporting an incorrectly formatted regex."""
	return f"the {regex} {is_or_are} not formatted correctly. please try again"


fractalrhomb_logger = logging.getLogger("fractalrhomb")
session: aiohttp.ClientSession = None


@dataclass
class BotData:
	"""Data class containing bot data/config."""

	bot_channels: dict[str, list[str]]
	news_post_channels: list[str]
	purge_cooldowns: dict[str, dict[str, float]]
	build_cache_cooldowns: dict[str, float]
	status: str | None

	async def load(self, fp: str) -> None:
		"""Load data from file."""
		fractalrhomb_logger.info("Loading bot data.")

		if not Path(fp).exists():
			fractalrhomb_logger.info("Did not find saved bot data.")
			return

		async with aiofiles.open(fp) as f:
			data = json.loads(await f.read())
			if data.get("bot_channels") is not None:
				fractalrhomb_logger.info("Loaded saved bot channels.")
				self.bot_channels = data["bot_channels"]
			if data.get("news_post_channels") is not None:
				fractalrhomb_logger.info("Loaded saved news post channels.")
				self.news_post_channels = data["news_post_channels"]
			if data.get("purge_cooldowns") is not None:
				fractalrhomb_logger.info("Loaded saved purge cooldowns.")
				self.purge_cooldowns = data["purge_cooldowns"]
			if data.get("build_cache_cooldowns") is not None:
				fractalrhomb_logger.info("Loaded saved build cache cooldowns.")
				self.build_cache_cooldowns = data["build_cache_cooldowns"]
			if data.get("status") is not None:
				fractalrhomb_logger.info("Loaded saved status.")
				self.status = data["status"]

	async def save(self, fp: str) -> None:
		"""Save data to file."""
		fractalrhomb_logger.info("Saving bot data.")

		if Path(fp).exists():
			backup = f"{fp}.bak"
			await aiofiles.os.replace(fp, backup)
			fractalrhomb_logger.info("Backed up old bot data file.")
		async with aiofiles.open(fp, "w") as f:
			await f.write(json.dumps(asdict(self), indent=4))
			fractalrhomb_logger.info("Saved bot data.")


bot_data = BotData({}, [], {}, {}, None)

USER_PURGE_COOLDOWN = dt.timedelta(hours=12)
BUILD_CACHE_COOLDOWN = dt.timedelta(hours=72)
BOT_DATA_PATH = "bot_data.json"


def sign(x: int) -> int:
	"""Return 1 if x is positive or -1 if x is negative."""
	return round(math.copysign(1, x))


def truncated_message(
	total_items: int,
	shown_items: int,
	amount: int,
	start_index: int,
	items: str = "items",
) -> str | None:
	"""Get truncation message."""
	message = None

	if amount >= 0 and shown_items < total_items:
		if start_index == 0:
			message = f"the rest of the {total_items} {items} were truncated (limit was {amount})"
		elif start_index < 0:
			message = f"the rest of the {total_items} {items} were truncated (limit was {amount}, starting backwards from {total_items + start_index + 1})"
		else:
			message = f"the rest of the {total_items} {items} were truncated (limit was {amount}, starting from {start_index + 1})"

	return message


def get_formatting(show: list[str] | tuple[str] | None) -> dict[str, bool] | None:
	"""Get formatting parameters."""
	if show is None:
		return None

	formatting = {}

	for i in show:
		formatting.update({i.lower(): True})

	return formatting


def split_message(message: list[str], join_str: str) -> list[str]:
	"""Split a message that's too long into multiple messages.

	Tries to split by items, then newlines, then spaces, and finally, characters.

	Splitting by anything other than items may eat formatting.
	"""
	split_messages = []
	message_current = ""

	i = 0
	max_loop = 100000
	while i < len(message):
		max_loop -= 1
		if max_loop < 0:  # infinite loop safeguard
			msg = "Loop running for too long."
			raise RuntimeError(msg)

		if len(message[i]) <= MAX_MESSAGE_LENGTH:
			i += 1
			continue

		max_message_length_formatting = MAX_MESSAGE_LENGTH
		if message[i].rfind("\n", 0, max_message_length_formatting) != -1:
			message.insert(
				i + 1,
				message[i][
					message[i].rfind("\n", 0, max_message_length_formatting) + 1 :
				],
			)
			message[i] = message[i][
				: message[i].rfind("\n", 0, max_message_length_formatting)
			]
		elif message[i].rfind(" ", 0, max_message_length_formatting) != -1:
			message.insert(
				i + 1,
				message[i][
					message[i].rfind(" ", 0, max_message_length_formatting) + 1 :
				],
			)
			message[i] = message[i][
				: message[i].rfind(" ", 0, max_message_length_formatting)
			]
		else:
			message.insert(i + 1, message[i][max_message_length_formatting - 1 :])
			message[i] = message[i][: max_message_length_formatting - 1] + "-"

		i += 1

	for i in range(len(message)):
		if len(message_current) + len(message[i]) + len(join_str) > MAX_MESSAGE_LENGTH:
			split_messages.append(message_current)
			message_current = ""

		message_current = join_str.join((message_current, message[i]))

	split_messages.append(message_current)

	return split_messages


async def standard_exception_handler(
	ctx: discord.ApplicationContext,
	logger: logging.Logger,
	exc: Exception | ExceptionGroup,
	cmd: str,
	*,
	is_deferred: bool = False,
) -> None:
	"""Handle standard requests exceptions."""
	cmd_name = cmd
	try:
		frame = inspect.currentframe()
		if frame is not None:
			cmd_name = frame.f_back.f_code.co_qualname
	finally:
		del frame

	max_loop = 1000
	while isinstance(exc, ExceptionGroup):
		max_loop -= 1
		if max_loop < 0:
			logger.warning("Loop running for too long.", stack_info=True)
			break

		exc = exc.exceptions[0]

	msg = f"A request exception occurred in command {cmd_name}"

	response = "an unknown client/connection error occurred"
	level = logging.ERROR
	if isinstance(exc, client_exc.ClientResponseError):
		response = f"server returned: {exc.status!s} {exc.message.lower()}"
		level = logging.WARNING
	elif isinstance(exc, TimeoutError):
		response = "request timed out"
	elif isinstance(exc, client_exc.ServerTimeoutError):
		response = "server timed out"
	elif isinstance(exc, client_exc.ClientConnectionError):
		response = "a connection error occurred"

	logger.log(level, msg, exc_info=True)

	await send_message(ctx, response, is_deferred=is_deferred)


class BotWarningView(discord.ui.View):
	"""A view for bot channel warnings."""

	def __init__(self) -> "BotWarningView":
		"""Create a bot channel warning view."""
		super().__init__(disable_on_timeout=True)
		self.value = None

	async def finish_callback(
		self, button: discord.ui.Button, interaction: discord.Interaction
	) -> None:
		"""Finish a callback after pressing a button."""
		for i in self.children:
			i.style = discord.ButtonStyle.secondary
		button.style = discord.ButtonStyle.success

		self.disable_all_items()
		await interaction.response.edit_message(view=self)

		self.stop()

	@discord.ui.button(emoji="✔️", label="Yes", style=discord.ButtonStyle.primary)
	async def confirm_button_callback(
		self, button: discord.ui.Button, interaction: discord.Interaction
	) -> None:
		"""Give True if the Yes button is clicked."""
		self.value = True

		await self.finish_callback(button, interaction)

	@discord.ui.button(emoji="❌", label="No", style=discord.ButtonStyle.primary)
	async def decline_button_callback(
		self, button: discord.ui.Button, interaction: discord.Interaction
	) -> None:
		"""Give False if the No button is clicked."""
		self.value = False

		await self.finish_callback(button, interaction)


async def bot_channel_warning(ctx: discord.ApplicationContext) -> bool | None:
	"""Give a warning if the command is not run in a bot channel (if any exist).

	If a warning was not given, or was accepted, returns True. If declined, returns False. If timed out, returns None.
	"""
	if ctx.guild_id is None:
		return True

	guild_id = str(ctx.guild_id)
	if (
		guild_id not in bot_data.bot_channels
		or len(bot_data.bot_channels[guild_id]) < 1
	):
		return True

	channel_id = str(ctx.channel_id)
	if channel_id in bot_data.bot_channels[guild_id]:
		return True

	confirmation = BotWarningView()
	await ctx.respond(
		"❗ you are trying to use a command in a non-bot channel. are you sure?",
		view=confirmation,
		ephemeral=True,
	)
	await confirmation.wait()
	return confirmation.value


async def message_length_warning(
	ctx: discord.ApplicationContext, response: list[str] | None, warn_length: int | None
) -> bool | None:
	"""Give a warning if the command would produce a long response.

	If respones or warn_length are None, or the length of the responses is longer than the warn length, gives a warning.
	If a warning was not given, or was accepted, returns True. If declined, returns False. If timed out, returns None.
	"""
	warn_user_bot_message_limit = True
	if response is not None and warn_length is not None:
		total_length = 0
		for i in response:
			total_length += len(i)

		if total_length < warn_length:
			return True

		if total_length < USER_BOT_WARN_MESSAGE_LENGTH:
			warn_user_bot_message_limit = False

		long = "long"
		if total_length >= 6 * warn_length:
			long = "**very long**"
		elif total_length >= 2.5 * warn_length:
			long = "very long"
		msg = f"❗ this command would produce a {long} response. are you sure?"
	else:
		msg = "❗ this command might produce a long response. are you sure?"

	if (
		warn_user_bot_message_limit
		and ctx.interaction.authorizing_integration_owners.guild_id is None
	):
		msg += "\nthe response will be truncated if it is longer than 5 messages."

	confirmation = BotWarningView()
	await ctx.respond(
		msg,
		view=confirmation,
		ephemeral=True,
	)
	await confirmation.wait()
	return confirmation.value


async def send_message(
	ctx: discord.ApplicationContext,
	message: str,
	separator: str = " ",
	*,
	ping_user: bool = True,
	is_deferred: bool = False,
	file: discord.File | None = None,
) -> bool:
	"""Send a message using either respond or, if possible, send.

	Returns False if too many follow up messages have been sent
	and True if the message was sent successfully.
	"""
	user = ""
	if ping_user:
		user = f"<@{ctx.author.id}>{separator}"

	message = message.strip()

	try:
		if not ctx.response.is_done() or is_deferred:
			if file is not None:
				await ctx.respond(message, file=file)
			else:
				await ctx.respond(message)
		elif file is not None:
			await ctx.send(f"{user}{message}", silent=ping_user, file=file)
		else:
			await ctx.send(f"{user}{message}", silent=ping_user)
	except discord.errors.Forbidden:
		try:
			if file is not None:
				await ctx.respond(f"{user}{message}", file=file)
			else:
				await ctx.respond(f"{user}{message}")
		except discord.errors.HTTPException as exc:
			if exc.code == INTERACTION_TOO_MANY_FOLLOW_UP_MESSAGES_ERROR_CODE:
				fractalrhomb_logger.debug(
					"Too many follow up messages have been sent. Truncating."
				)
				return False
			raise

	return True
