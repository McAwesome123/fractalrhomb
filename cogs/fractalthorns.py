# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Fractalthorns cog for the bot."""

import asyncio
import datetime as dt
import logging
import logging.handlers
import random
import re
from io import BytesIO
from math import ceil

import aiohttp.client_exceptions as client_exc
import discord
import discord.utils

import src.fractalrhomb_globals as frg
import src.fractalthorns_dataclasses as ftd
import src.fractalthorns_exceptions as fte
from src.fractalthorns_api import fractalthorns_api


class Fractalthorns(discord.Cog):
	"""Class defining the fractalthorns cog."""

	def __init__(self, bot: discord.Bot) -> "Fractalthorns":
		"""Initialize the cog."""
		self.bot: discord.Bot = bot
		self.logger = logging.getLogger("discord.cogs.fractalthorns")

	MAX_EPISODIC_LINE_ITEMS = 100

	@staticmethod
	async def all_news_show(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for show."""
		options = ["title", "date", "items", "version"]

		used_options = ctx.value.split()
		if (
			len(used_options) > 0
			and not ctx.value.endswith(" ")
			and used_options[-1] not in options
		):
			used_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i]) for i in options if i not in used_options
			]
			return possible_options

		return options

	@discord.slash_command(name="news")
	@discord.option("limit", int, description="How much news to show (default: 1)")
	@discord.option(
		"start",
		int,
		description="Where to start (negative numbers start from the end) (default: 1)",
		parameter_name="start_index",
	)
	@discord.option(
		"show",
		str,
		description="What information to show and in what order (default: title date items version)",
		autocomplete=discord.utils.basic_autocomplete(all_news_show),
	)
	async def all_news(
		self,
		ctx: discord.ApplicationContext,
		limit: int = 1,
		start_index: int = 1,
		show: str | None = None,
	) -> None:
		"""Show the latest news."""
		self.logger.info(
			"All news command used (limit=%s, start_index=%s, show=%s)",
			limit,
			start_index,
			show,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		if start_index > 0:
			start_index -= 1

		if show is not None:
			show = show.split()

		formatting = frg.get_formatting(show)

		try:
			news = await fractalthorns_api.get_all_news(frg.session)

			total_items = len(news)
			news = news[start_index :: frg.sign(start_index)]

			if limit >= 0:
				news = news[:limit]

			response = [i.format(formatting) for i in news]

			if limit != 1:
				too_many = frg.truncated_message(
					total_items, len(response), limit, start_index, "news items"
				)
				if too_many is not None:
					response.append(too_many)

			responses = frg.split_message(response, "\n\n")

			if not await frg.message_length_warning(ctx, responses, 1000):
				return

			if len(responses[0].strip()) < 1:
				await ctx.respond(frg.EMPTY_MESSAGE)
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i.strip()}", silent=True)
					user = ""

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.NEWS_ITEMS
					)
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
				ctx, self.logger, exc, "Fractalthorns.all_news"
			)

	@staticmethod
	async def single_image_name(_: discord.AutocompleteContext) -> list[str]:
		"""Give available image names."""
		images = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.IMAGES, ignore_stale=True
		)

		images.pop(None, None)

		return list(images.keys())

	@staticmethod
	async def single_image_show(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for show."""
		options = [
			"title",
			"name",
			"ordinal",
			"date",
			"image",
			"thumb",
			"canon",
			"has_desc",
			"characters",
			"speedpaint",
			"primary",
			"secondary",
			"link",
		]

		used_options = ctx.value.split()
		if (
			len(used_options) > 0
			and not ctx.value.endswith(" ")
			and used_options[-1] not in options
		):
			used_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i]) for i in options if i not in used_options
			]
			return possible_options

		return options

	@discord.slash_command(name="image")
	@discord.option(
		"name",
		str,
		description="The (URL) name of the image (default: (latest))",
		autocomplete=discord.utils.basic_autocomplete(single_image_name),
	)
	@discord.option(
		"image",
		str,
		description="Which kind of image to show (default: image)",
		choices=["image", "thumbnail", "none"],
	)
	@discord.option(
		"show",
		str,
		description="What information to show and in what order (default: title canon characters speedpaint link)",
		autocomplete=discord.utils.basic_autocomplete(single_image_show),
	)
	async def single_image(
		self,
		ctx: discord.ApplicationContext,
		name: str | None = None,
		image: str = "image",
		show: str | None = None,
	) -> None:
		"""Show an image."""
		self.logger.info(
			"Single image command used (name=%s, image=%s, show=%s)", name, image, show
		)

		if not await frg.bot_channel_warning(ctx):
			return

		deferred = False
		if not ctx.response.is_done():
			await ctx.defer()
			deferred = True

		if name is not None:
			name = name.lower()

		if show is not None:
			show = show.split()
			for i in range(len(show)):
				match show[i]:
					case "image":
						show[i] = "image_url"
					case "thumb":
						show[i] = "thumb_url"
					case "has_desc":
						show[i] = "has_description"
					case "speedpaint":
						show[i] = "speedpaint_video_url"
					case "primary":
						show[i] = "primary_color"
					case "secondary":
						show[i] = "secondary_color"
					case "link":
						show[i] = "image_link"

		formatting = frg.get_formatting(show)

		try:
			response = await fractalthorns_api.get_single_image(frg.session, name)
			response_text = response[0].format(formatting)
			response_image = None
			if image == "image":
				response_image = response[1][0]
			elif image == "thumbnail":
				response_image = response[1][1]

			file = None
			if response_image is not None:
				io = BytesIO()
				response_image.save(io, "PNG")
				io.seek(0)
				file = discord.File(io, filename=f"{response[0].name}.png")
			elif len(response_text) < 1:
				response_text = frg.EMPTY_MESSAGE

			if deferred:
				if file is not None:
					await ctx.respond(response_text, file=file)
				else:
					await ctx.respond(response_text)
			elif file is not None:
				await ctx.send(
					f"<@{ctx.author.id}>\n{response_text}", file=file, silent=True
				)
			else:
				await ctx.send(f"<@{ctx.author.id}>\n{response_text}", silent=True)

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(fractalthorns_api.CacheTypes.IMAGES)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.IMAGE_CONTENTS
					)
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
				ctx, self.logger, exc, "Fractalthorns.single_image"
			)

	@discord.slash_command(name="description")
	@discord.option(
		"name",
		str,
		description="The (URL) name of the image",
		autocomplete=discord.utils.basic_autocomplete(single_image_name),
	)
	async def image_description(
		self,
		ctx: discord.ApplicationContext,
		name: str,
	) -> None:
		"""Show the description of an image."""
		self.logger.info("Image description command used (name=%s)", name)

		if not await frg.bot_channel_warning(ctx):
			return

		try:
			response = await fractalthorns_api.get_image_description(
				frg.session, name.lower()
			)

			responses = frg.split_message([response.format()], "")
			for i in range(len(responses)):
				if not responses[i].startswith("> ") and not responses[i].startswith(
					">>> "
				):
					responses[i] = f">>> {responses[i]}"

			if not await frg.message_length_warning(ctx, responses, 1000):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.IMAGE_DESCRIPTIONS
					)
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
				ctx, self.logger, exc, "Fractalthorns.image_description"
			)

	@discord.slash_command(name="allimages")
	@discord.option("limit", int, description="How many images to show (default: 10)")
	@discord.option(
		"start",
		int,
		description="Where to start from (negative numbers start from the end) (default: 1)",
		parameter_name="start_index",
	)
	async def all_images(
		self,
		ctx: discord.ApplicationContext,
		limit: int = 10,
		start_index: int = 1,
	) -> None:
		"""Show a list of all images."""
		self.logger.info(
			"All images command used (limit=%s, start_index=%s)", limit, start_index
		)

		if not await frg.bot_channel_warning(ctx):
			return

		if start_index > 0:
			start_index -= 1

		try:
			images = await fractalthorns_api.get_all_images(frg.session)

			total_items = len(images)
			images = images[start_index :: frg.sign(start_index)]

			if limit >= 0:
				images = images[:limit]

			response = [i.format_inline() for i in images]

			too_many = frg.truncated_message(
				total_items, len(response), limit, start_index, "images"
			)
			if too_many is not None:
				response.append(f"\n{too_many}")

			responses = frg.split_message(response, "\n")

			if not await frg.message_length_warning(ctx, responses, 1800):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(fractalthorns_api.CacheTypes.IMAGES)
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
				ctx, self.logger, exc, "Fractalthorns.all_images"
			)

	@staticmethod
	async def single_sketch_name(_: discord.AutocompleteContext) -> list[str]:
		"""Give available sketch names."""
		sketches = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.SKETCHES, ignore_stale=True
		)

		if sketches is None:
			return []

		return list(sketches[0].keys())

	@staticmethod
	async def single_sketch_show(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for show."""
		options = [
			"title",
			"name",
			"image_url",
			"thumb_url",
			"sketch_link",
		]

		used_options = ctx.value.split()
		if (
			len(used_options) > 0
			and not ctx.value.endswith(" ")
			and used_options[-1] not in options
		):
			used_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i]) for i in options if i not in used_options
			]
			return possible_options

		return options

	@discord.slash_command(name="sketch")
	@discord.option(
		"name",
		str,
		description="The (URL) name of the sketch (default: (latest))",
		autocomplete=discord.utils.basic_autocomplete(single_sketch_name),
	)
	@discord.option(
		"image",
		str,
		description="Which kind of image to show (default: image)",
		choices=["image", "thumbnail", "none"],
	)
	@discord.option(
		"show",
		str,
		description="What information to show and in what order (default: title sketch_link)",
		autocomplete=discord.utils.basic_autocomplete(single_sketch_show),
	)
	async def single_sketch(
		self,
		ctx: discord.ApplicationContext,
		name: str | None = None,
		image: str = "image",
		show: str | None = None,
	) -> None:
		"""Show a sketch."""
		self.logger.info(
			"Single sketch command used (name=%s, image=%s, show=%s)", name, image, show
		)

		if not await frg.bot_channel_warning(ctx):
			return

		deferred = False
		if not ctx.response.is_done():
			await ctx.defer()
			deferred = True

		if name is not None:
			name = name.lower()

		formatting = frg.get_formatting(show)

		try:
			response = await fractalthorns_api.get_single_sketch(frg.session, name)
			response_text = response[0].format(formatting)
			response_image = None
			if image == "image":
				response_image = response[1][0]
			elif image == "thumbnail":
				response_image = response[1][1]

			file = None
			if response_image is not None:
				io = BytesIO()
				response_image.save(io, "PNG")
				io.seek(0)
				file = discord.File(io, filename=f"{response[0].name}.png")
			elif len(response_text) < 1:
				response_text = frg.EMPTY_MESSAGE

			if deferred:
				if file is not None:
					await ctx.respond(response_text, file=file)
				else:
					await ctx.respond(response_text)
			elif file is not None:
				await ctx.send(
					f"<@{ctx.author.id}>\n{response_text}", file=file, silent=True
				)
			else:
				await ctx.send(f"<@{ctx.author.id}>\n{response_text}", silent=True)

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(fractalthorns_api.CacheTypes.SKETCHES)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.SKETCH_CONTENTS
					)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

		except* fte.SketchNotFoundError:
			response = "sketch not found"
			if deferred:
				await ctx.respond(response)
			else:
				await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.single_sketch"
			)

	@discord.slash_command(name="allsketches")
	@discord.option("limit", int, description="How many sketches to show (default: 10)")
	@discord.option(
		"start",
		int,
		description="Where to start from (negative numbers start from the end) (default: 1)",
		parameter_name="start_index",
	)
	async def all_sketches(
		self,
		ctx: discord.ApplicationContext,
		limit: int = 10,
		start_index: int = 1,
	) -> None:
		"""Show a list of all sketches."""
		self.logger.info(
			"All sketches command used (limit=%s, start_index=%s)", limit, start_index
		)

		if not await frg.bot_channel_warning(ctx):
			return

		if start_index > 0:
			start_index -= 1

		try:
			sketches = await fractalthorns_api.get_all_sketches(frg.session)

			total_items = len(sketches)
			sketches = sketches[start_index :: frg.sign(start_index)]

			if limit >= 0:
				sketches = sketches[:limit]

			response = [i.format_inline() for i in sketches]

			too_many = frg.truncated_message(
				total_items, len(response), limit, start_index, "sketches"
			)
			if too_many is not None:
				response.append(f"\n{too_many}")

			responses = frg.split_message(response, "\n")

			if not await frg.message_length_warning(ctx, responses, 1000):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(fractalthorns_api.CacheTypes.SKETCHES)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.all_sketches"
			)

	@staticmethod
	async def full_episodic_name(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available chapter names."""
		cached_chapters = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.CHAPTERS, ignore_stale=True
		)

		if cached_chapters is None:
			return []

		chapters = list(cached_chapters[0].keys())

		used_chapters = ctx.value.split()
		if (
			len(used_chapters) > 0
			and not ctx.value.endswith(" ")
			and used_chapters[-1] not in chapters
		):
			used_chapters.pop()

		if len(used_chapters) > 0:
			possible_chapters = [" ".join(used_chapters)]
			possible_chapters += [
				" ".join([*used_chapters, i])
				for i in chapters
				if i not in used_chapters
			]
			return possible_chapters

		return chapters

	@discord.slash_command(name="chapter")
	@discord.option(
		"chapter",
		str,
		description="The name of the chapter(s) (default: (latest))",
		autocomplete=discord.utils.basic_autocomplete(full_episodic_name),
	)
	async def full_episodic(
		self,
		ctx: discord.ApplicationContext,
		chapter: str | None = None,
	) -> None:
		"""Show a list of records in a chapter."""
		self.logger.info("Full episodic command used (chapter=%s)", chapter)

		if not await frg.bot_channel_warning(ctx):
			return

		try:
			chapters = await fractalthorns_api.get_full_episodic(frg.session)

			if chapter is None:
				chapter = (chapters[-1].name,)
			else:
				chapter = chapter.lower().split()

			response = []
			for i in chapter:
				response += [j.format() for j in chapters if i.lower() == j.name]

			responses = frg.split_message(response, "\n\n")

			if not await frg.message_length_warning(ctx, responses, 1200):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i.strip()}", silent=True)
					user = ""

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(fractalthorns_api.CacheTypes.CHAPTERS)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

				task = tg.create_task(
					fractalthorns_api.save_cache(fractalthorns_api.CacheTypes.RECORDS)
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
				ctx, self.logger, exc, "Fractalthorns.full_episodic"
			)

	@staticmethod
	async def single_record_name(_: discord.AutocompleteContext) -> list[str]:
		"""Give available record names."""
		records = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.RECORDS, ignore_stale=True
		)

		return list(records.keys())

	@staticmethod
	async def single_record_show(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for record show."""
		options = ["title", "name", "iteration", "chapter", "solved", "record_link"]

		used_options = ctx.value.split()
		if (
			len(used_options) > 0
			and not ctx.value.endswith(" ")
			and used_options[-1] not in options
		):
			used_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i]) for i in options if i not in used_options
			]
			return possible_options

		return options

	@discord.slash_command(name="record")
	@discord.option(
		"name",
		str,
		description="The (URL) name of the record",
		autocomplete=discord.utils.basic_autocomplete(single_record_name),
	)
	@discord.option(
		"show",
		str,
		description="What information to show and in what order (default: title name iteration chapter record_link)",
		autocomplete=discord.utils.basic_autocomplete(single_record_show),
	)
	async def single_record(
		self,
		ctx: discord.ApplicationContext,
		name: str,
		show: str | None = None,
	) -> None:
		"""Show a record entry."""
		self.logger.info("Single record command used (name=%s, show=%s)", name, show)

		if not await frg.bot_channel_warning(ctx):
			return

		if show is not None:
			show = show.split()

		try:
			response = await fractalthorns_api.get_single_record(
				frg.session, name.lower()
			)

			formatting = frg.get_formatting(show)

			response_text = response.format(formatting)

			if len(response_text.strip()) < 1:
				response_text = frg.EMPTY_MESSAGE

			if not ctx.response.is_done():
				await ctx.respond(response_text)
			else:
				await ctx.send(f"<@{ctx.author.id}>\n{response_text}", silent=True)

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(fractalthorns_api.CacheTypes.RECORDS)
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
				ctx, self.logger, exc, "Fractalthorns.single_record"
			)

	@discord.slash_command(name="recordtext")
	@discord.option(
		"name",
		str,
		description="The (URL) name of the record",
		autocomplete=discord.utils.basic_autocomplete(single_record_name),
	)
	async def record_text(self, ctx: discord.ApplicationContext, name: str) -> None:
		"""Show a record's text."""
		self.logger.info("Record text command used (name=%s)", name)

		if not await frg.bot_channel_warning(ctx):
			return

		try:
			response = await fractalthorns_api.get_record_text(
				frg.session, name.lower()
			)

			responses = frg.split_message([response.format()], "")
			for i in range(len(responses)):
				if not responses[i].startswith("> "):
					responses[i] = f"> {responses[i]}"

			if not await frg.message_length_warning(ctx, responses, 1000):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.RECORD_CONTENTS
					)
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
				ctx, self.logger, exc, "Fractalthorns.record_text"
			)

	@discord.slash_command(name="domainsearch")
	@discord.option("term", str, description="What to search")
	@discord.option(
		"type",
		str,
		description="What type of search",
		choices=["image", "episodic-item", "episodic-line"],
		parameter_name="type_",
	)
	@discord.option(
		"limit", int, description="How many search results to show (default: 10)"
	)
	@discord.option(
		"start",
		int,
		description="Where to start from (negative numbers start from the end) (default: 1)",
		parameter_name="start_index",
	)
	async def domain_search(
		self,
		ctx: discord.ApplicationContext,
		term: str,
		type_: str,
		limit: int = 10,
		start_index: int = 1,
	) -> None:
		"""Make a search."""
		self.logger.info(
			"Domain search command used (term=%s, type_=%s, limit=%s, start_index=%s)",
			term,
			type_,
			limit,
			start_index,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		msg = f"searching `{type_}` for `{term}`..."
		if not ctx.response.is_done():
			await ctx.respond(msg)
		else:
			await ctx.send(f"<@{ctx.author.id}> {msg}", silent=True)

		if start_index > 0:
			start_index -= 1

		try:
			results = await fractalthorns_api.get_domain_search(
				frg.session, term, type_
			)

			total_items = len(results)
			if total_items < 1:
				await ctx.send("nothing was found")
				return

			results = results[start_index :: frg.sign(start_index)]

			if limit >= 0:
				results = results[:limit]

			if type_ == "episodic-line":
				last_record = None
				response = []
				for i in results:
					response.append(i.format(last_record))
					last_record = i.record
			else:
				response = [i.format() for i in results]
			if type_ == "episodic-line" and total_items >= self.MAX_EPISODIC_LINE_ITEMS:
				too_many = frg.truncated_message(
					total_items + 1, len(response), limit, start_index, "results"
				)
				too_many = too_many.replace(
					str(total_items + 1), f"{total_items!s}+", 1
				)
			else:
				too_many = frg.truncated_message(
					total_items, len(response), limit, start_index, "results"
				)

			if too_many is not None:
				if type_ != "episodic-line":
					too_many = f"\n{too_many}"
				response.append(too_many)

			responses = frg.split_message(response, "\n")

			if not await frg.message_length_warning(ctx, responses, 1200):
				await ctx.send("the search was cancelled")
				return

			for i in responses:
				await ctx.send(i)

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.SEARCH_RESULTS
					)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.RECORD_CONTENTS
					)
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
				ctx, self.logger, exc, "Fractalthorns.domain_search"
			)

	get_random_group = discord.SlashCommandGroup(
		"random", "Get a select random item from fractalthorns"
	)

	@staticmethod
	async def get_image_canon(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for canons."""
		images_cache = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.IMAGES, ignore_stale=True
		)
		images: list[ftd.Image] = [i[0] for i in images_cache.values()]

		options = {i.canon.lower() for i in images if i.canon is not None}
		options.add("none")
		options = {i.lower() for i in options}

		canon_aliases = {
			"eykwyrm": "154373",
			"vollux": "209151",
			"moth": "209151",
			"llokin": "265404",
			"chevrin": "265404",
			"osmite": "768220",
			"nyxite": "768221",
		}

		used_options = ctx.value.lower().split()
		formatted_options = [canon_aliases.get(i, i) for i in used_options]

		if (
			len(formatted_options) > 0
			and not ctx.value.endswith(" ")
			and formatted_options[-1] not in options
		):
			used_options.pop()
			formatted_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i])
				for i in options
				if i not in formatted_options
			]
			return possible_options

		return list(options)

	@staticmethod
	async def get_image_characters(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for canons."""
		images_cache = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.IMAGES, ignore_stale=True
		)
		images: list[ftd.Image] = [i[0] for i in images_cache.values()]

		options = set()
		for i in images:
			options.update(i.characters)
		options.add("none")
		options.discard(None)
		options = {i.lower() for i in options}

		used_options = ctx.value.lower().split()

		if (
			len(used_options) > 0
			and not ctx.value.endswith(" ")
			and used_options[-1] not in options
		):
			used_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i]) for i in options if i not in used_options
			]
			return possible_options

		return list(options)

	@get_random_group.command(name="image")
	@discord.option(
		"name",
		str,
		description="Only images whose names contain this (regex)",
	)
	@discord.option(
		"description",
		str,
		description="Only images whose descriptions contain this (regex)",
	)
	@discord.option(
		"canon",
		str,
		description="Only images from these canons",
		autocomplete=discord.utils.basic_autocomplete(get_image_canon),
	)
	@discord.option(
		"character",
		str,
		description="Only images with these characters",
		autocomplete=discord.utils.basic_autocomplete(get_image_characters),
	)
	@discord.option(
		"has_description",
		bool,
		description="Only images that do or don't have a description",
	)
	async def get_random_image(
		self,
		ctx: discord.ApplicationContext,
		name: str | None = None,
		description: str | None = None,
		canon: str | None = None,
		character: str | None = None,
		*,
		has_description: bool | None = None,
	) -> None:
		"""Get a random image."""
		self.logger.info(
			"Random image command used (name=%s, description=%s, canon=%s, character=%s, has_description=%s)",
			name,
			description,
			canon,
			character,
			has_description,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		deferred = False
		if not ctx.response.is_done():
			deferred = True
			await ctx.defer()

		try:
			try:
				images_list = await fractalthorns_api.search_images(
					frg.session,
					name=name,
					description=description,
					canon=canon,
					character=character,
					has_description=has_description,
				)

			except re.error:
				if name is not None and description is not None:
					response = frg.regex_incorrectly_formatted(
						"name or description", "are"
					)
				elif description is not None:
					response = frg.regex_incorrectly_formatted("description")
				else:
					response = frg.regex_incorrectly_formatted("name")

				if deferred:
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			if len(images_list) < 1:
				response = frg.NO_ITEMS_MATCH_SEARCH
				if deferred:
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			random.seed()
			random_item = random.choice(images_list)  # noqa: S311  # this is not cryptographic you fuck

			random_item = await fractalthorns_api.get_single_image(
				frg.session, random_item.name
			)

			response_text = random_item[0].format()

			response_image = random_item[1][0]
			io = BytesIO()
			response_image.save(io, "PNG")
			io.seek(0)
			file = discord.File(io, filename=f"{random_item[0].name}.png")

			if deferred:
				await ctx.respond(response_text, file=file)
			else:
				await ctx.send(
					f"<@{ctx.author.id}>\n{response_text}", file=file, silent=True
				)

			await fractalthorns_api.save_all_caches()

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.get_random_image"
			)

	@staticmethod
	async def get_record_iteration(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for iteration."""
		chapters_cache = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.CHAPTERS, ignore_stale=True
		)
		records = []
		for i in chapters_cache[0].values():
			records.extend(i.records)

		options = {i.iteration.lower() for i in records}

		iteration_aliases = {
			"vollux": "209151",
			"moth": "209151",
			"llokin": "265404",
			"chevrin": "265404",
			"osmite": "768220",
			"nyxite": "768221",
			"director": "0",
		}

		used_options = ctx.value.lower().split()
		formatted_options = [iteration_aliases.get(i, i) for i in used_options]

		if (
			len(formatted_options) > 0
			and not ctx.value.endswith(" ")
			and formatted_options[-1] not in options
		):
			used_options.pop()
			formatted_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i])
				for i in options
				if i not in formatted_options
			]
			return possible_options

		return list(options)

	@staticmethod
	async def get_record_language(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for language."""
		records_cache = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.FULL_RECORD_CONTENTS, ignore_stale=True
		)
		records = records_cache[0].values()

		options = set()
		for i in records:
			options.update(i.languages)
		options = {i.lower() for i in options}

		used_options = ctx.value.lower().split()

		if (
			len(used_options) > 0
			and not ctx.value.endswith(" ")
			and used_options[-1] not in options
		):
			used_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i]) for i in options if i not in used_options
			]
			return possible_options

		return list(options)

	@staticmethod
	async def get_record_character(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for character."""
		records_cache = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.FULL_RECORD_CONTENTS, ignore_stale=True
		)
		records = records_cache[0].values()

		options = set()
		for i in records:
			options.update(i.characters)
		options = {i.lower() for i in options}

		used_options = ctx.value.lower().split()

		if (
			len(used_options) > 0
			and not ctx.value.endswith(" ")
			and used_options[-1] not in options
		):
			used_options.pop()

		if len(used_options) > 0:
			possible_options = [" ".join(used_options)]
			possible_options += [
				" ".join([*used_options, i]) for i in options if i not in used_options
			]
			return possible_options

		return list(options)

	@get_random_group.command(name="record")
	@discord.option(
		"name",
		str,
		description="Only images whose names contain this (regex)",
	)
	@discord.option(
		"chapter",
		str,
		description="Only records from these chapters",
		autocomplete=discord.utils.basic_autocomplete(full_episodic_name),
	)
	@discord.option(
		"iteration",
		str,
		description="Only records from these iterations",
		autocomplete=discord.utils.basic_autocomplete(get_record_iteration),
	)
	@discord.option(
		"language",
		str,
		description="Only records with these languages",
		autocomplete=discord.utils.basic_autocomplete(get_record_language),
	)
	@discord.option(
		"character",
		str,
		description="Only records with these characters",
		autocomplete=discord.utils.basic_autocomplete(get_record_character),
	)
	@discord.option(
		"requested",
		bool,
		description="Only records that are or aren't requested",
	)
	async def get_random_record(
		self,
		ctx: discord.ApplicationContext,
		name: str | None = None,
		chapter: str | None = None,
		iteration: str | None = None,
		language: str | None = None,
		character: str | None = None,
		*,
		requested: bool | None = None,
	) -> None:
		"""Get a random record."""
		self.logger.info(
			"Random record command used (name=%s, chapter=%s, iteration=%s, language=%s, character=%s, requested=%s)",
			name,
			chapter,
			iteration,
			language,
			character,
			requested,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		deferred = False
		record_contents_required = (
			language is not None or character is not None or requested is not None
		)
		if not ctx.response.is_done() and record_contents_required:
			try:
				await fractalthorns_api.get_full_record_contents(
					frg.session, gather=False
				)
			except fte.ItemsUngatheredError:
				await ctx.defer()
				deferred = True

		try:
			try:
				records_list = await fractalthorns_api.search_records(
					frg.session,
					name=name,
					chapter=chapter,
					iteration=iteration,
					language=language,
					character=character,
					requested=requested,
				)

			except re.error:
				response = frg.regex_incorrectly_formatted("name")
				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			if len(records_list) < 1:
				response = frg.NO_ITEMS_MATCH_SEARCH
				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			random.seed()
			random_item = random.choice(records_list)  # noqa: S311  # this is not cryptographic you fuck

			random_item = await fractalthorns_api.get_single_record(
				frg.session, random_item.name
			)

			response_text = random_item.format()

			if deferred or not ctx.response.is_done():
				await ctx.respond(response_text)
			else:
				await ctx.send(f"<@{ctx.author.id}>\n{response_text}", silent=True)

			await fractalthorns_api.save_all_caches()

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.get_random_record"
			)

	@get_random_group.command(name="line")
	@discord.option(
		"text",
		str,
		description="Only lines containing this text (regex)",
	)
	@discord.option(
		"language",
		str,
		description="Only lines from these languages",
		autocomplete=discord.utils.basic_autocomplete(get_record_language),
	)
	@discord.option(
		"character",
		str,
		description="Only lines from these characters",
		autocomplete=discord.utils.basic_autocomplete(get_record_character),
	)
	@discord.option(
		"emphasis",
		str,
		description="Only lines containing this emphasis (regex)",
	)
	@discord.option(
		"name",
		str,
		description="Only lines from records whose names contain this (regex)",
	)
	@discord.option(
		"chapter",
		str,
		description="Only lines from records from these chapters",
		autocomplete=discord.utils.basic_autocomplete(full_episodic_name),
	)
	@discord.option(
		"iteration",
		str,
		description="Only lines from records from these iterations",
		autocomplete=discord.utils.basic_autocomplete(get_record_iteration),
	)
	@discord.option(
		"requested",
		bool,
		description="Only lines from records that are or aren't requested",
	)
	async def get_random_record_line(
		self,
		ctx: discord.ApplicationContext,
		text: str,
		language: str | None = None,
		character: str | None = None,
		emphasis: str | None = None,
		name: str | None = None,
		chapter: str | None = None,
		iteration: str | None = None,
		*,
		requested: bool | None = None,
	) -> None:
		"""Get a random record line."""
		self.logger.info(
			"Random record line command used (text=%s, language=%s, character=%s, emphasis=%s, name=%s, chapter=%s, iteration=%s, requested=%s)",
			text,
			language,
			character,
			emphasis,
			name,
			chapter,
			iteration,
			requested,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		deferred = False
		if not ctx.response.is_done():
			try:
				await fractalthorns_api.get_full_record_contents(
					frg.session, gather=False
				)
			except fte.ItemsUngatheredError:
				await ctx.defer()
				deferred = True

		try:
			try:
				lines_list = await fractalthorns_api.search_record_lines(
					frg.session,
					text=text,
					language=language,
					character=character,
					emphasis=emphasis,
					name=name,
					chapter=chapter,
					iteration=iteration,
					requested=requested,
				)

			except re.error:
				response = frg.regex_incorrectly_formatted("name")
				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			if len(lines_list) < 1:
				response = frg.NO_ITEMS_MATCH_SEARCH
				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			random.seed()
			random_item = random.choice(lines_list)  # noqa: S311  # this is not cryptographic you fuck

			response_text = random_item.format()

			if deferred or not ctx.response.is_done():
				await ctx.respond(response_text)
			else:
				await ctx.send(f"<@{ctx.author.id}>\n{response_text}", silent=True)

			await fractalthorns_api.save_all_caches()

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.get_random_record_line"
			)

	search_group = discord.SlashCommandGroup(
		"search", "Search for items from fractalthorns"
	)

	@search_group.command(name="images")
	@discord.option(
		"name",
		str,
		description="Only images whose names contain this (regex)",
	)
	@discord.option(
		"description",
		str,
		description="Only images whose descriptions contain this (regex)",
	)
	@discord.option(
		"canon",
		str,
		description="Only images from these canons",
		autocomplete=discord.utils.basic_autocomplete(get_image_canon),
	)
	@discord.option(
		"character",
		str,
		description="Only images with these characters",
		autocomplete=discord.utils.basic_autocomplete(get_image_characters),
	)
	@discord.option(
		"has_description",
		bool,
		description="Only images that do or don't have a description",
	)
	@discord.option("limit", int, description="How many images to show (default: 10)")
	@discord.option(
		"start",
		int,
		description="Where to start from (negative numbers start from the end) (default: 1)",
		parameter_name="start_index",
	)
	async def search_images(
		self,
		ctx: discord.ApplicationContext,
		name: str | None = None,
		description: str | None = None,
		canon: str | None = None,
		character: str | None = None,
		*,
		has_description: bool | None = None,
		limit: int = 10,
		start_index: int = 1,
	) -> None:
		"""Search for images."""
		self.logger.info(
			"Search images command used (name=%s, description=%s, canon=%s, character=%s, has_description=%s, limit=%s, start_index=%s)",
			name,
			description,
			canon,
			character,
			has_description,
			limit,
			start_index,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		if start_index > 0:
			start_index -= 1

		deferred = False
		if not ctx.response.is_done() and description is not None:
			try:
				await fractalthorns_api.get_full_image_descriptions(
					frg.session, gather=False
				)
			except fte.ItemsUngatheredError:
				await ctx.defer()
				deferred = True

		try:
			try:
				images_list = await fractalthorns_api.search_images(
					frg.session,
					name=name,
					description=description,
					canon=canon,
					character=character,
					has_description=has_description,
				)

			except re.error:
				if name is not None and description is not None:
					response = frg.regex_incorrectly_formatted(
						"name or description", "are"
					)
				elif description is not None:
					response = frg.regex_incorrectly_formatted("description")
				else:
					response = frg.regex_incorrectly_formatted("name")

				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			if len(images_list) < 1:
				response = frg.NO_ITEMS_MATCH_SEARCH
				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			total_items = len(images_list)
			images_list = images_list[start_index :: frg.sign(start_index)]

			if limit >= 0:
				images_list = images_list[:limit]

			response = [i.format_inline() for i in images_list]

			too_many = frg.truncated_message(
				total_items, len(response), limit, start_index, "images"
			)
			if too_many is not None:
				response.append(f"\n{too_many}")

			responses = frg.split_message(response, "\n")

			if not await frg.message_length_warning(ctx, responses, 1800):
				return

			user = f"<@{ctx.author.id}>"
			for i in responses:
				if deferred or not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

			await fractalthorns_api.save_all_caches()

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.search_images"
			)

	@search_group.command(name="records")
	@discord.option(
		"name",
		str,
		description="Only images whose names contain this (regex)",
	)
	@discord.option(
		"chapter",
		str,
		description="Only records from these chapters",
		autocomplete=discord.utils.basic_autocomplete(full_episodic_name),
	)
	@discord.option(
		"iteration",
		str,
		description="Only records from these iterations",
		autocomplete=discord.utils.basic_autocomplete(get_record_iteration),
	)
	@discord.option(
		"language",
		str,
		description="Only records with these languages",
		autocomplete=discord.utils.basic_autocomplete(get_record_language),
	)
	@discord.option(
		"character",
		str,
		description="Only records with these characters",
		autocomplete=discord.utils.basic_autocomplete(get_record_character),
	)
	@discord.option(
		"requested",
		bool,
		description="Only records that are or aren't requested",
	)
	@discord.option("limit", int, description="How many records to show (default: 10)")
	@discord.option(
		"start",
		int,
		description="Where to start from (negative numbers start from the end) (default: 1)",
		parameter_name="start_index",
	)
	async def search_records(
		self,
		ctx: discord.ApplicationContext,
		name: str | None = None,
		chapter: str | None = None,
		iteration: str | None = None,
		language: str | None = None,
		character: str | None = None,
		*,
		requested: bool | None = None,
		limit: int = 10,
		start_index: int = 1,
	) -> None:
		"""Search for records."""
		self.logger.info(
			"Search records command used (name=%s, chapter=%s, iteration=%s, language=%s, character=%s, requested=%s, limit=%s, start_index=%s)",
			name,
			chapter,
			iteration,
			language,
			character,
			requested,
			limit,
			start_index,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		if start_index > 0:
			start_index -= 1

		deferred = False
		record_contents_required = (
			language is not None or character is not None or requested is not None
		)
		if not ctx.response.is_done() and record_contents_required:
			try:
				await fractalthorns_api.get_full_record_contents(
					frg.session, gather=False
				)
			except fte.ItemsUngatheredError:
				await ctx.defer()
				deferred = True

		try:
			try:
				records_list = await fractalthorns_api.search_records(
					frg.session,
					name=name,
					chapter=chapter,
					iteration=iteration,
					language=language,
					character=character,
					requested=requested,
				)

			except re.error:
				response = frg.regex_incorrectly_formatted("name")

				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			if len(records_list) < 1:
				response = frg.NO_ITEMS_MATCH_SEARCH
				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			total_items = len(records_list)
			records_list = records_list[start_index :: frg.sign(start_index)]

			if limit >= 0:
				records_list = records_list[:limit]

			response = [i.format_inline() for i in records_list]

			too_many = frg.truncated_message(
				total_items, len(response), limit, start_index, "records"
			)
			if too_many is not None:
				response.append(f"\n{too_many}")

			responses = frg.split_message(response, "\n")

			if not await frg.message_length_warning(ctx, responses, 1200):
				return

			user = f"<@{ctx.author.id}>"
			for i in responses:
				if deferred or not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

			await fractalthorns_api.save_all_caches()

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.search_records"
			)

	@search_group.command(name="text")
	@discord.option(
		"text",
		str,
		description="Only lines containing this text (regex)",
	)
	@discord.option(
		"language",
		str,
		description="Only lines from these languages",
		autocomplete=discord.utils.basic_autocomplete(get_record_language),
	)
	@discord.option(
		"character",
		str,
		description="Only lines from these characters",
		autocomplete=discord.utils.basic_autocomplete(get_record_character),
	)
	@discord.option(
		"emphasis",
		str,
		description="Only lines containing this emphasis (regex)",
	)
	@discord.option(
		"name",
		str,
		description="Only lines from records whose names contain this (regex)",
	)
	@discord.option(
		"chapter",
		str,
		description="Only lines from records from these chapters",
		autocomplete=discord.utils.basic_autocomplete(full_episodic_name),
	)
	@discord.option(
		"iteration",
		str,
		description="Only lines from records from these iterations",
		autocomplete=discord.utils.basic_autocomplete(get_record_iteration),
	)
	@discord.option(
		"requested",
		bool,
		description="Only lines from records that are or aren't requested",
	)
	@discord.option(
		"limit", int, description="How many record lines to show (default: 10)"
	)
	@discord.option(
		"start",
		int,
		description="Where to start from (negative numbers start from the end) (default: 1)",
		parameter_name="start_index",
	)
	async def search_record_lines(
		self,
		ctx: discord.ApplicationContext,
		text: str,
		language: str | None = None,
		character: str | None = None,
		emphasis: str | None = None,
		name: str | None = None,
		chapter: str | None = None,
		iteration: str | None = None,
		*,
		requested: bool | None = None,
		limit: int = 10,
		start_index: int = 1,
	) -> None:
		"""Search for record lines."""
		self.logger.info(
			"Search record lines command used (text=%s, language=%s, character=%s, emphasis=%s, name=%s, chapter=%s, iteration=%s, requested=%s, limit=%s, start_index=%s)",
			text,
			language,
			character,
			emphasis,
			name,
			chapter,
			iteration,
			requested,
			limit,
			start_index,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		if start_index > 0:
			start_index -= 1

		deferred = False
		if not ctx.response.is_done():
			try:
				await fractalthorns_api.get_full_record_contents(
					frg.session, gather=False
				)
			except fte.ItemsUngatheredError:
				await ctx.defer()
				deferred = True

		try:
			try:
				lines_list = await fractalthorns_api.search_record_lines(
					frg.session,
					text=text,
					language=language,
					character=character,
					emphasis=emphasis,
					name=name,
					chapter=chapter,
					iteration=iteration,
					requested=requested,
				)

			except re.error:
				response = frg.regex_incorrectly_formatted("name")

				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			if len(lines_list) < 1:
				response = frg.NO_ITEMS_MATCH_SEARCH
				if deferred or not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
				return

			total_items = len(lines_list)
			lines_list = lines_list[start_index :: frg.sign(start_index)]

			if limit >= 0:
				lines_list = lines_list[:limit]

			response = []
			last_record = None
			for i in lines_list:
				response.append(i.format(last_record))
				last_record = i.record

			too_many = frg.truncated_message(
				total_items, len(response), limit, start_index, "results"
			)
			if too_many is not None:
				response.append(f"\n{too_many}")

			responses = frg.split_message(response, "\n")

			if not await frg.message_length_warning(ctx, responses, 1800):
				return

			user = f"<@{ctx.author.id}>"
			for i in responses:
				if deferred or not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

			await fractalthorns_api.save_all_caches()

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.search_record_lines"
			)

	gather_group = discord.SlashCommandGroup(
		"fractalthorns", "Gather stuff from fractalthorns"
	)

	@gather_group.command(name="gather")
	async def gather_all(self, ctx: discord.ApplicationContext) -> None:
		"""Gather record texts and image descriptions in bulk."""
		self.logger.info("Gather all command used")

		if not await frg.bot_channel_warning(ctx):
			return

		user = str(ctx.author.id)

		time = frg.bot_data.gather_cooldowns.get(user)
		if (
			time is not None
			and dt.datetime.now(dt.UTC)
			< dt.datetime.fromtimestamp(time, dt.UTC) + frg.FULL_GATHER_COOLDOWN
		):
			time += frg.FULL_GATHER_COOLDOWN.total_seconds()
			response = f"you cannot do that. try again <t:{ceil(time)}:R>"
			if not ctx.response.is_done():
				await ctx.respond(response)
			else:
				await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)
			return

		try:

			async def delayed_send(delay: float = 0.25) -> None:
				await asyncio.sleep(delay)
				response = "gathering items. this may take a bit"
				if not ctx.response.is_done():
					await ctx.respond(response)
				else:
					await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.get_full_record_contents(frg.session, gather=True)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

				task = tg.create_task(
					fractalthorns_api.get_full_image_descriptions(
						frg.session, gather=True
					)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

				task = tg.create_task(delayed_send())
				tasks.add(task)
				task.add_done_callback(tasks.discard)

		except* fte.CachePurgeError as exc:
			exc = exc.exceptions[0]
			if exc.allowed_time is not None:
				response = f"this command was used too recently. try again <t:{ceil(exc.args[1].timestamp())}:R>"
			else:
				response = "this command was used too recently"

			if not ctx.response.is_done():
				await ctx.respond(response)
			else:
				await ctx.send(f"<@{ctx.author.id}> {response}", silent=True)

		else:
			await ctx.send("successfully gathered all records and descriptions")

			frg.bot_data.gather_cooldowns.update(
				{user: dt.datetime.now(dt.UTC).timestamp()}
			)
			try:
				await frg.bot_data.save(frg.BOT_DATA_PATH)
			except Exception:
				self.logger.exception("Could not save bot data.")

		await fractalthorns_api.save_all_caches()


def setup(bot: discord.Bot) -> None:
	"""Set up the cog."""
	bot.add_cog(Fractalthorns(bot))
