# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Fractalthorns cog for the bot."""

import logging
import logging.handlers
import math
from io import BytesIO
from typing import Literal

import discord
import requests.exceptions as req
from discord.ext import commands

from src.fractalthorns_api import fractalthorns_api

MAX_MESSAGE_LENGTH = 1950
EMPTY_MESSAGE = "give me something to show"


def sign(x: int) -> int:
	"""Return 1 if x is positive or -1 if x is negative."""
	return round(math.copysign(1, x))


def truncated_message(
	total_items: int, shown_items: int, amount: int, start_index: int, items: str = "items"
) -> str | None:
	"""Get truncation message."""
	message = None

	if amount >= 0 and shown_items < total_items:
		if start_index == 0:
			message = f"the rest of the {total_items} {items} were truncated (limit was {amount})"
		elif start_index < 0:
			message = f"the rest of the {total_items} {items} were truncated (limit was {amount}, starting backwards from {total_items+start_index+1})"
		else:
			message = f"the rest of the {total_items} {items} were truncated (limit was {amount}, starting from {start_index+1})"

	return message


def get_formatting(args: list[str] | tuple[str]) -> dict[str, bool] | None:
	"""Get formatting parameters."""
	formatting = {}
	custom_formatting = False

	for i in args:
		if i is None:
			continue

		arg = i.lower()

		if custom_formatting:
			formatting.update({arg: True})

		if arg == "show":
			custom_formatting = True

	if not custom_formatting:
		return None

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
	ctx: commands.Context, logger: logging.Logger, exc: Exception, cmd: str
) -> None:
	"""Handle standard requests exceptions."""
	msg = f"An exception occurred in command {cmd}"
	logger.warning(msg, exc_info=True)

	response = ""
	if isinstance(exc, req.HTTPError):
		response = f"```\n{exc!s}\n```"
	elif isinstance(exc, req.Timeout):
		response = "```\nserver request timed out\n```"
	elif isinstance(exc, req.ConnectionError | req.TooManyRedirects):
		response = "```\na connection error occurred\n```"

	await ctx.send(response)


class Fractalthorns(commands.Cog):
	"""Class defining the fractalthorns cog."""

	def __init__(self, bot: commands.Bot) -> "Fractalthorns":
		"""Initialize the cog."""
		self.bot: commands.Bot = bot
		self.logger = logging.getLogger("discord.cogs.fractalthorns")

	@commands.command(
		name="news",
		usage="[amount] [start] [show [title | date | items | version]...]",
	)
	async def all_news(
		self,
		ctx: commands.Context,
		*args: str,
	) -> None:
		"""Show the latest news.

		Arguments:
		---------
		  amount How much news to show (-1 for all) (default: 1)
		  start  Where to start (negative numbers start from the end) (default: 1)
		  show   Add "show ..." to specify what to show and the order.
		         The following may be specified: title, date, items, version
		         (default: "show title date items version")
		"""
		try:
			amount = int(args[0])
		except (ValueError, IndexError):
			amount = 1

		try:
			start_index = int(args[1])
		except (ValueError, IndexError):
			start_index = 1

		if start_index > 0:
			start_index = start_index - 1

		formatting = get_formatting(args)

		try:
			news = fractalthorns_api.get_all_news()

			total_items = len(news)
			news = news[start_index :: sign(start_index)]

			if amount >= 0:
				news = news[:amount]

			response = [i.format(formatting) for i in news]

			if amount != 1:
				too_many = truncated_message(
					total_items, len(response), amount, start_index, "news items"
				)
				if too_many is not None:
					response.append(too_many)

			responses = split_message(response, "\n\n")

			for i in responses:
				if len(i) > 0:
					await ctx.send(i)
				else:
					await ctx.send(EMPTY_MESSAGE)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await standard_exception_handler(ctx, self.logger, exc, "all_news")

	@commands.command(name="image", usage="[name] [image] [show [...]...]")
	async def single_image(
		self,
		ctx: commands.Context,
		name: str | None = None,
		image: str | None = None,
		*args: str,
	) -> None:
		"""Show an image.

		Arguments:
		---------
		  name  Name of the image to show (default: (latest))
		  image What to show. Can be: image, thumbnail, none.
		        Must specify a name first (default: image)
		  show  Add "show ..." to specify what to show and the order.
		        The following may be specified: title, name, ordinal, date,
		        image | image_url, thumb | thumb_url, canon, description
		        has_description, characters, speedpaint | speedpaint_video_url,
		        primary | primary_color, secondary | secondary_color
		        (default: "show title canon characters speedpaint_video_url")
		"""
		if name is not None:
			name = name.lower()

		args = list(args)
		if name == "show":
			args.insert(0, name)
			args.insert(1, image)
			name = None
			image = "image"
		elif image == "show":
			args.insert(0, image)
			image = "image"

		if image is None:
			image = "image"
		image = image.lower()

		for i in range(len(args)):
			match args[i]:
				case "image":
					args[i] = "image_url"
				case "thumb":
					args[i] = "thumb_url"
				case "description":
					args[i] = "has_description"
				case "speedpaint":
					args[i] = "speedpaint_video_url"
				case "primary":
					args[i] = "primary_color"
				case "secondary":
					args[i] = "secondary_color"

		formatting = get_formatting(args)

		try:
			response = fractalthorns_api.get_single_image(name)
			response_text = response[0].format(formatting)
			response_image = None
			if image == "image":
				response_image = response[1][0]
			elif image == "thumbnail" or image == "thumb":
				response_image = response[1][1]

			if response_image is not None:
				io = BytesIO()
				response_image.save(io, "PNG")
				io.seek(0)
				await ctx.send(
					response_text,
					file=discord.File(io, filename=f"{response[0].name}.png"),
				)
			elif len(response_text) > 0:
				await ctx.send(response_text)
			else:
				await ctx.send(EMPTY_MESSAGE)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await standard_exception_handler(ctx, self.logger, exc, "single_image")

	@commands.command(name="description")
	async def image_description(
		self,
		ctx: commands.Context,
		name: str,
	) -> None:
		"""Show the description of an image.

		Arguments:
		---------
		  name Which image description to show
		"""
		try:
			response = fractalthorns_api.get_image_description(name.lower())

			responses = split_message([response.format()], "")

			for i in responses:
				await ctx.send(i)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await standard_exception_handler(ctx, self.logger, exc, "image_description")

	@commands.command(aliases=["allimages"], usage="[amount] [start]")
	async def all_images(
		self, ctx: commands.Context, amount: int = 10, start_index: int = 0
	) -> None:
		"""Show a list of all images.

		Arguments:
		---------
		    amount How many images to show (-1 for all) (default: 10)
		    start  Where to start (negative numbers start from the end) (default: 1)
		"""
		if start_index > 0:
			start_index -= 1

		try:
			images = fractalthorns_api.get_all_images()

			total_items = len(images)
			images = images[start_index :: sign(start_index)]

			if amount >= 0:
				images = images[:amount]

			response = [i.format_inline() for i in images]

			too_many = truncated_message(total_items, len(response), amount, start_index, "images")
			if too_many is not None:
				response.append(f"\n{too_many}")

			responses = split_message(response, "\n")

			for i in responses:
				await ctx.send(i)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await standard_exception_handler(ctx, self.logger, exc, "all_images")

	@commands.command(name="chapter", aliases=["episodic"], usage="[chapter]...")
	async def full_episodic(
		self,
		ctx: commands.Context,
		*chapter: str,
	) -> None:
		"""Show a list of records in a chapter.

		Arguments:
		---------
		    chapter The name of the chapter. Can specify multiple. (default: (latest))
		"""
		try:
			chapters = fractalthorns_api.get_full_episodic()

			if len(chapter) < 1:
				chapter = (chapters[-1].name,)

			response = []
			for i in chapter:
				response += [j.format() for j in chapters if i.lower() == j.name]

			responses = split_message(response, "\n\n")

			for i in responses:
				await ctx.send(i)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await standard_exception_handler(ctx, self.logger, exc, "full_episodic")

	@commands.command(name="record", usage="<name> [show [...]...]")
	async def single_record(
		self,
		ctx: commands.Context,
		name: str,
		*args: str,
	) -> None:
		"""Show a record entry.

		Arguments:
		---------
		    name The name of the record.
		    show Add "show ..." to specify what to show and the order.
		         The following may be specified:
		         title, name, iteration, chapter, solved
		         (default: "show title name iteration chapter")
		"""
		try:
			response = fractalthorns_api.get_single_record(name.lower())

			formatting = get_formatting(args)

			response_text = response.format(formatting)

			if len(response_text) > 0:
				await ctx.send(response.format(formatting))
			else:
				await ctx.send(EMPTY_MESSAGE)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await standard_exception_handler(ctx, self.logger, exc, "single_record")

	@commands.command(aliases=["recordtext"], usage="<name>")
	async def record_text(
		self,
		ctx: commands.Context,
		name: str,
	) -> None:
		"""Show a record's text.

		Arguments:
		---------
		    name The name of the record.
		"""
		try:
			response = fractalthorns_api.get_record_text(name.lower())

			responses = split_message([response.format()], "")
			for i in range(0, len(responses)):
				if not responses[i].startswith("> "):
					responses[i] = f"> {responses[i]}"

			for i in responses:
				await ctx.send(i)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await standard_exception_handler(ctx, self.logger, exc, "single_record")

	@commands.command(aliases=["domainsearch"], usage="<term> <type> [amount] [start]")
	async def domain_search(
		self,
		ctx: commands.Context,
		term: str,
		type_: Literal[
			"image", "episodic-item", "record", "episodic-line", "record-text", "text"
		],
		amount: int = 10,
		start_index: int = 1,
	) -> None:
		"""Make a search.

		Arguments:
		---------
		    term   The search term. Use quotes for multiple words.
		    type   What to search. Must be one of the following:
		           image, episodic-item | record, episodic-line | text
		    amount How many results to show (-1 for all) (default: 10)
		    start  Where to start (negative numbers start from the end) (default: 1)
		"""
		if type_ == "record":
			type_ = "episodic-item"
		elif type_ == "text":
			type_ = "episodic-line"

		if start_index > 0:
			start_index -= 1

		try:
			results = fractalthorns_api.get_domain_search(term, type_)

			total_items = len(results)
			if total_items < 1:
				await ctx.send("nothing was found")
				return

			results = results[start_index :: sign(start_index)]

			if amount >= 0:
				results = results[:amount]

			response = [i.format() for i in results]
			if type_ == "episodic-line" and total_items >= 100:
				too_many = truncated_message(total_items+1, len(response), amount, start_index, "results")
				too_many = too_many.replace(str(total_items+1), f"{str(total_items)}+", 1)
			else:
				too_many = truncated_message(total_items, len(response), amount, start_index, "results")

			if too_many is not None:
				if type_ == "episodic-line":
					response.append(too_many)
				else:
					response.append(f"\n{too_many}")

			responses = split_message(response, "\n")

			for i in responses:
				await ctx.send(i)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await standard_exception_handler(ctx, self.logger, exc, "domain_search")


def setup(bot: commands.Bot) -> None:
	"""Set up the cog."""
	bot.add_cog(Fractalthorns(bot))
