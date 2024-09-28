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
__activity_emoji = os.getenv("NXEYE_EMOJI")
if __activity_emoji is not None:
	__activity_emoji = discord.PartialEmoji.from_str(__activity_emoji).to_dict()
activity = discord.CustomActivity(
	"observing you",
	emoji=__activity_emoji,
)
bot = discord.Bot(intents=intents, activity=activity)

MAX_MESSAGE_LENGTH = 1950
EMPTY_MESSAGE = "give me something to show"
NO_ITEMS_MATCH_SEARCH = "no items match the requested parameters"

# The full version number including anything extra.
FRACTALRHOMB_VERSION_FULL = "0.7.0-pre.2"
# Version number with only Major, Minor, and Patch version.
FRACTALRHOMB_VERSION_LONG = "0.7.0"
# Verison number with only Major and Minor version.
FRACTALRHOMB_VERSION_SHORT = "0.7"

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


discord_logger = logging.getLogger("discord")
session: aiohttp.ClientSession = None


@dataclass
class BotData:
	"""Data class containing bot data/config."""

	bot_channels: dict[str, list[str]]
	news_post_channels: list[str]
	purge_cooldowns: dict[str, dict[str, float]]
	gather_cooldowns: dict[str, float]

	async def load(self, fp: str) -> None:
		"""Load data from file."""
		discord_logger.info("Loading bot data.")

		if not Path(fp).exists():
			discord_logger.info("Did not find saved bot data.")
			return

		async with aiofiles.open(fp, "r") as f:
			data = json.loads(await f.read())
			if data.get("bot_channels") is not None:
				discord_logger.info("Loaded saved bot channels.")
				self.bot_channels = data["bot_channels"]
			if data.get("news_post_channels") is not None:
				discord_logger.info("Loaded saved news post channels.")
				self.news_post_channels = data["news_post_channels"]
			if data.get("purge_cooldowns") is not None:
				discord_logger.info("Loaded saved purge cooldowns.")
				self.purge_cooldowns = data["purge_cooldowns"]
			if data.get("gather_cooldowns") is not None:
				discord_logger.info("Loaded saved purge cooldowns.")
				self.gather_cooldowns = data["gather_cooldowns"]

	async def save(self, fp: str) -> None:
		"""Save data to file."""
		discord_logger.info("Saving bot data.")

		if Path(fp).exists():
			backup = f"{fp}.bak"
			await aiofiles.os.replace(fp, backup)
			discord_logger.info("Backed up old bot data file.")
		async with aiofiles.open(fp, "w") as f:
			await f.write(json.dumps(asdict(self), indent=4))
			discord_logger.info("Saved bot data.")


bot_data = BotData({}, [], {}, {})

USER_PURGE_COOLDOWN = dt.timedelta(hours=12)
FULL_GATHER_COOLDOWN = dt.timedelta(hours=72)
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

	await ctx.respond(response)


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
	if response is not None and warn_length is not None:
		total_length = 0
		for i in response:
			total_length += len(i)

		if total_length < warn_length:
			return True

		long = "long"
		if total_length >= 6 * warn_length:
			long = "**very long**"
		elif total_length >= 2.5 * warn_length:
			long = "very long"
		msg = f"❗ this command would produce a {long} response. are you sure?"
	else:
		msg = "❗ this command might produce a long response. are you sure?"

	confirmation = BotWarningView()
	await ctx.respond(
		msg,
		view=confirmation,
		ephemeral=True,
	)
	await confirmation.wait()
	return confirmation.value
