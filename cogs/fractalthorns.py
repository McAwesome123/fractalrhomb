# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Fractalthorns cog for the bot."""

import logging
import logging.handlers
from io import BytesIO

import discord
import discord.utils
import requests.exceptions as req

import src.fractalrhomb_globals as frf
from src.fractalthorns_api import fractalthorns_api


class Fractalthorns(discord.Cog):
	"""Class defining the fractalthorns cog."""

	def __init__(self, bot: discord.Bot) -> "Fractalthorns":
		"""Initialize the cog."""
		self.bot: discord.Bot = bot
		self.logger = logging.getLogger("discord.cogs.fractalthorns")

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
		if not await frf.bot_channel_warning(ctx):
			return

		if start_index > 0:
			start_index = start_index - 1

		if show is not None:
			show = show.split()

		formatting = frf.get_formatting(show)

		try:
			news = fractalthorns_api.get_all_news()

			total_items = len(news)
			news = news[start_index :: frf.sign(start_index)]

			if limit >= 0:
				news = news[:limit]

			response = [i.format(formatting) for i in news]

			if limit != 1:
				too_many = frf.truncated_message(
					total_items, len(response), limit, start_index, "news items"
				)
				if too_many is not None:
					response.append(too_many)

			responses = frf.split_message(response, "\n\n")

			if not await frf.message_length_warning(ctx, responses, 1000):
				return

			if len(responses[0].strip()) < 1:
				await ctx.respond(frf.EMPTY_MESSAGE)
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i.strip()}", silent=True)
					user = ""

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await frf.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.all_news"
			)

	@staticmethod
	async def single_image_name(_: discord.AutocompleteContext) -> list[str]:
		"""Give available image names."""
		images = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.IMAGES, ignore_stale=True
		)

		if images is None:
			return []

		non_duplicate = []
		for i in images:
			if i.name not in non_duplicate:
				non_duplicate.append(i.name)

		return non_duplicate

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
		description="What information to show and in what order (default: title canon characters speedpaint)",
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
		if not await frf.bot_channel_warning(ctx):
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

		formatting = frf.get_formatting(show)

		try:
			response = fractalthorns_api.get_single_image(name)
			response_text = response[0].format(formatting)
			response_image = None
			if image == "image":
				response_image = response[1][0]
			elif image == "thumbnail" or image == "thumb":
				response_image = response[1][1]

			file = None
			if response_image is not None:
				io = BytesIO()
				response_image.save(io, "PNG")
				io.seek(0)
				file = discord.File(io, filename=f"{response[0].name}.png")
			elif len(response_text) < 1:
				response_text = frf.EMPTY_MESSAGE

			if deferred:
				await ctx.respond(response_text, file=file)
			else:
				await ctx.send(
					f"<@{ctx.author.id}>\n{response_text}", file=file, silent=True
				)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await frf.standard_exception_handler(
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
		if not await frf.bot_channel_warning(ctx):
			return

		try:
			response = fractalthorns_api.get_image_description(name.lower())

			responses = frf.split_message([response.format()], "")
			for i in range(len(responses)):
				if not responses[i].startswith("> ") and not responses[i].startswith(
					">>> "
				):
					responses[i] = f">>> {responses[i]}"

			if not await frf.message_length_warning(ctx, responses, 1000):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await frf.standard_exception_handler(
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
		if not await frf.bot_channel_warning(ctx):
			return

		if start_index > 0:
			start_index -= 1

		try:
			images = fractalthorns_api.get_all_images()

			total_items = len(images)
			images = images[start_index :: frf.sign(start_index)]

			if limit >= 0:
				images = images[:limit]

			response = [i.format_inline() for i in images]

			too_many = frf.truncated_message(
				total_items, len(response), limit, start_index, "images"
			)
			if too_many is not None:
				response.append(f"\n{too_many}")

			responses = frf.split_message(response, "\n")

			if not await frf.message_length_warning(ctx, responses, 1800):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await frf.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.all_images"
			)

	@staticmethod
	async def full_episodic_name(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available chapter names."""
		cached_chapters = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.CHAPTERS, ignore_stale=True
		)

		if cached_chapters is None:
			return []

		chapters = [i.name for i in cached_chapters]

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
		if not await frf.bot_channel_warning(ctx):
			return

		try:
			chapters = fractalthorns_api.get_full_episodic()

			if chapter is None:
				chapter = (chapters[-1].name,)
			else:
				chapter = chapter.lower().split()

			response = []
			for i in chapter:
				response += [j.format() for j in chapters if i.lower() == j.name]

			responses = frf.split_message(response, "\n\n")

			if not await frf.message_length_warning(ctx, responses, 600):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i.strip()}", silent=True)
					user = ""

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await frf.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.full_episodic"
			)

	@staticmethod
	async def single_record_name(_: discord.AutocompleteContext) -> list[str]:
		"""Give available record names."""
		records = fractalthorns_api.get_cached_items(
			fractalthorns_api.CacheTypes.RECORDS, ignore_stale=True
		)

		if records is None:
			return []

		return [i.name for i in records]

	@staticmethod
	async def single_record_show(ctx: discord.AutocompleteContext) -> list[str]:
		"""Give available items for record show."""
		options = ["title", "name", "iteration", "chapter", "solved"]

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
		description="What information to show and in what order (default: title name iteration chapter)",
		autocomplete=discord.utils.basic_autocomplete(single_record_show),
	)
	async def single_record(
		self,
		ctx: discord.ApplicationContext,
		name: str,
		show: str | None = None,
	) -> None:
		"""Show a record entry."""
		if not await frf.bot_channel_warning(ctx):
			return

		if show is not None:
			show = show.split()

		try:
			response = fractalthorns_api.get_single_record(name.lower())

			formatting = frf.get_formatting(show)

			response_text = response.format(formatting)

			if len(response_text.strip()) < 1:
				response_text = frf.EMPTY_MESSAGE

			if not ctx.response.is_done():
				await ctx.respond(response_text)
			else:
				await ctx.send(f"<@{ctx.author.id}>\n{response_text}", silent=True)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await frf.standard_exception_handler(
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
		if not await frf.bot_channel_warning(ctx):
			return

		try:
			response = fractalthorns_api.get_record_text(name.lower())

			responses = frf.split_message([response.format()], "")
			for i in range(len(responses)):
				if not responses[i].startswith("> "):
					responses[i] = f"> {responses[i]}"

			if not await frf.message_length_warning(ctx, responses, 1000):
				return

			user = f"<@{ctx.author.id}>\n"
			for i in responses:
				if not ctx.response.is_done():
					await ctx.respond(i)
				else:
					await ctx.send(f"{user}{i}", silent=True)
					user = ""

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await frf.standard_exception_handler(
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
		if not await frf.bot_channel_warning(ctx):
			return

		msg = f"searching `{type_}` for `{term}`..."
		if not ctx.response.is_done():
			await ctx.respond(msg)
		else:
			await ctx.send(f"<@{ctx.author.id}> {msg}", silent=True)

		if start_index > 0:
			start_index -= 1

		try:
			results = fractalthorns_api.get_domain_search(term, type_)

			total_items = len(results)
			if total_items < 1:
				await ctx.send("nothing was found")
				return

			results = results[start_index :: frf.sign(start_index)]

			if limit >= 0:
				results = results[:limit]

			response = [i.format() for i in results]
			if type_ == "episodic-line" and total_items >= 100:
				too_many = frf.truncated_message(
					total_items + 1, len(response), limit, start_index, "results"
				)
				too_many = too_many.replace(
					str(total_items + 1), f"{total_items!s}+", 1
				)
			else:
				too_many = frf.truncated_message(
					total_items, len(response), limit, start_index, "results"
				)

			if too_many is not None:
				if type_ != "episodic-line":
					too_many = f"\n{too_many}"
				response.append(too_many)

			responses = frf.split_message(response, "\n")

			if not await frf.message_length_warning(ctx, responses, 1200):
				await ctx.send("the search was cancelled.")
				return

			for i in responses:
				await ctx.send(i)

		except (
			req.HTTPError,
			req.Timeout,
			req.ConnectionError,
			req.TooManyRedirects,
		) as exc:
			await frf.standard_exception_handler(
				ctx, self.logger, exc, "Fractalthorns.domain_search"
			)


def setup(bot: discord.Bot) -> None:
	"""Set up the cog."""
	bot.add_cog(Fractalthorns(bot))
