# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module containing dataclasses used the fractalthorns API handler."""

import os
import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsEntry:
	"""Data class containing a news entry."""

	title: str
	items: list[str]
	date: datetime
	version: str | None

	type NewsEntryType = dict[str, str | bool | list[str] | None]

	@staticmethod
	def from_obj(obj: NewsEntryType) -> "NewsEntry":
		"""Create a NewsEntry from an object.

		Argument: obj -- The object to create a NewsEntry from.
		(Expected: an item from all_news["items"].
		all_news needs to be converted from json first.)
		"""
		return NewsEntry(
			obj["title"],
			obj.get("items", []),
			obj["date"],
			obj.get("version"),
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"title: {self.title}",
				f"items: {self.items}",
				f"date: {self.date}",
				f"version: {self.version}",
			)
		)

		return "\n".join(str_list)

	def format(self, formatting: dict[str, bool] | None = None) -> str:
		"""Return a string with discord formatting.

		Keyword Arguments:
		-----------------
		formatting -- Defines which items to show and in what order (based on dict order).
		Items that shouldn't be shown don't need to be included. Non-existent items are ignored.

		Valid formatting items:
		-----------------------
		"title" -- Witty quip (default: True),
		"date" -- Date created (default: True),
		"items" -- List of changes (default: True),
		"version" -- The new version, if it changed (default: True).
		"""
		if formatting is None:
			formatting = {
				"title": True,
				"date": True,
				"items": True,
				"version": True,
			}

		valid_formatting = ["title", "date", "items", "version"]
		formatting = [
			i for i, j in formatting.items() if i in valid_formatting and j is True
		]

		news_join_list = []

		for format_ in formatting:
			if format_ == "title":
				title = f"> ## {self.title}"
				news_join_list.append(title)

			if format_ == "date":
				date = f"on {self.date}"
				date = f"> __{date}__"
				news_join_list.append(date)

			if format_ == "items" and len(self.items) > 0:
				changes_list = [f"> - {i}" for i in self.items]
				changes = "\n".join(changes_list)
				news_join_list.append(changes)
			elif format_ == "items":
				changes = "> no changes listed"
				news_join_list.append(changes)

			if format_ == "version" and self.version is not None:
				version = f"> _{self.version}_"
				news_join_list.append(version)
			elif format_ == "version":
				version = "> _no version change_"
				news_join_list.append(version)

		return "\n".join(news_join_list)


@dataclass
class Image:
	"""Data class containing image metadata."""

	name: str
	title: str
	date: datetime
	ordinal: int
	image_url: str
	thumb_url: str
	canon: str | None
	has_description: bool
	characters: list[str]
	speedpaint_video_url: str | None
	primary_color: str | None
	secondary_color: str | None
	image_link: str

	type ImageType = dict[str, str | datetime | int | bool | list[str] | None]

	@staticmethod
	def from_obj(image_link: str, obj: ImageType) -> "Image":
		"""Create an Image from an object.

		Arguments:
		---------
		image_link -- The link to the image.
		obj -- The object to create an Image from.
		(Expected: single_image or an item from all_images["images"].
		single_image and all_images need to be converted from json first.
		["image_url"] and ["thumb_url"] should have the full URL.)
		"""
		return Image(
			obj["name"],
			obj["title"],
			obj["date"],
			obj["ordinal"],
			obj["image_url"],
			obj["thumb_url"],
			obj.get("canon"),
			obj["has_description"],
			obj["characters"],
			obj.get("speedpaint_video_url"),
			obj.get("primary_color"),
			obj.get("secondary_color"),
			image_link,
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"name: {self.name}",
				f"title: {self.title}",
				f"date: {self.date}",
				f"ordinal: {self.ordinal}",
				f"image url: {self.image_url}",
				f"thumb url: {self.thumb_url}",
				f"canon: {self.canon}",
				f"has description: {self.has_description}",
				f"characters: {self.characters}",
				f"speedpaint video url: {self.speedpaint_video_url}",
				f"primary color: {self.primary_color}",
				f"secondary color: {self.secondary_color}",
				f"image link: {self.image_link}",
			)
		)

		return "\n".join(str_list)

	def format(self, formatting: dict[str, bool] | None = None) -> str:
		"""Return a string with discord formatting.

		Keyword Arguments:
		-----------------
		formatting -- Defines which items to show and in what order (based on dict order).
		Items that shouldn't be shown don't need to be included. Non-existent items are ignored.

		Valid formatting items:
		-----------------------
		"title" -- The image title (can contain a link to the image) (default: True)
		"name" -- Identifying name of the image (default: False)
		"ordinal" -- Image index (1-based) (default: False)
		"date" -- Date created (default: False)
		"image_url" -- URL with the image data (default: False)
		"thumb_url" -- URL with the thumbnail data (default: False)
		"canon" -- Depicted iteration (if applicable) (default: True)
		"has_description" -- Whether a description exists (default: False)
		"characters" -- Depicted characters (default: True)
		"speedpaint_video_url" -- Link to the speedpaint (default: True)
		"primary_color" -- Approximation of most dominant color (default: False)
		"secondary_color" -- Approximation of second most dominant color (default: False)
		"image_link" -- URL to the image itself (default: True)
		"""
		if formatting is None:
			formatting = {
				"title": True,
				"name": False,
				"ordinal": False,
				"date": False,
				"image_url": False,
				"thumb_url": False,
				"canon": True,
				"has_description": False,
				"characters": True,
				"speedpaint_video_url": True,
				"primary_color": False,
				"secondary_color": False,
				"image_link": True,
			}

		valid_formatting = [
			"title",
			"name",
			"ordinal",
			"date",
			"image_url",
			"thumb_url",
			"canon",
			"has_description",
			"characters",
			"speedpaint_video_url",
			"primary_color",
			"secondary_color",
			"image_link",
		]
		formatting = [
			i for i, j in formatting.items() if i in valid_formatting and j is True
		]

		image_join_list = []
		image_url_done = False
		thumb_url_done = False
		primary_color_done = False
		secondary_color_done = False

		for format_ in formatting:
			if format_ == "name":
				image_join_list.append(f"> ___{self.name}___")

			if format_ == "title":
				title = self.title
				if "image_link" in formatting:
					title = f"[{title}](<{self.image_link}>)"
				image_join_list.append(f"> ## {title}")

			if format_ == "ordinal":
				image_join_list.append(
					"".join(("> _(image #", str(self.ordinal), ")_"))
				)

			if format_ == "date":
				date = f"on {self.date}"
				date = f"> __{date}__"
				image_join_list.append(date)

			if format_ == "image_url" and not thumb_url_done:
				image_url = f"{self.image_url}"
				image_url = f"> [image url](<{image_url}>)"
				if "thumb_url" in formatting:
					thumb_url = f"{self.thumb_url}"
					thumb_url = f"[thumbnail url](<{thumb_url}>)"
					image_url = f"{image_url} | {thumb_url}"
				image_join_list.append(image_url)
				image_url_done = True

			if format_ == "thumb_url" and not image_url_done:
				thumb_url = f"{self.thumb_url}"
				thumb_url = f"> [thumbnail url](<{thumb_url}>)"
				if "image_url" in formatting:
					image_url = f"{self.image_url}"
					image_url = f"[image url](<{image_url}>)"
					thumb_url = f"{thumb_url} | {image_url}"
				image_join_list.append(thumb_url)
				thumb_url_done = True

			if format_ == "canon":
				if self.canon is not None:
					canon = f"canon: {self.canon}"
				else:
					canon = "canon: none"
				canon = f"> _{canon}_"
				image_join_list.append(canon)

			if format_ == "has_description":
				has_description = " ".join(
					("> has description:", "yes" if self.has_description else "no")
				)
				image_join_list.append(has_description)

			if format_ == "characters":
				characters = ", ".join(self.characters)
				characters = " ".join(("> characters:", characters or "_none_"))
				image_join_list.append(characters)

			if format_ == "speedpaint_video_url":
				if self.speedpaint_video_url is not None:
					speedpaint = f"> [speedpaint video](<{self.speedpaint_video_url}>)"
				else:
					speedpaint = "> no speedpaint video"
				image_join_list.append(speedpaint)

			if format_ == "primary_color" and not secondary_color_done:
				colors = f"> primary color: {self.primary_color if self.primary_color is not None else "none"}"

				if "secondary_color" in formatting:
					colors = "".join(
						(
							colors,
							", secondary color: ",
							self.secondary_color
							if self.secondary_color is not None
							else "none",
						)
					)

				image_join_list.append(colors)
				primary_color_done = True

			if format_ == "secondary_color" and not primary_color_done:
				colors = f"> secondary color: {self.secondary_color if self.secondary_color is not None else "none"}"

				if "primary_color" in formatting:
					colors = "".join(
						(
							colors,
							", primary color: ",
							self.primary_color
							if self.primary_color is not None
							else "none",
						)
					)

				image_join_list.append(colors)
				secondary_color_done = True

			if format_ == "image_link" and "title" not in formatting:
				image_link = f"> <{self.image_link}>"
				image_join_list.append(image_link)

		return "\n".join(image_join_list)

	def format_inline(self) -> str:
		"""Return a string with discord formatting (without linebreaks)."""
		if self.speedpaint_video_url is None:
			speedpaint_video_url = "no speedpaint video"
		else:
			speedpaint_video_url = f"[speedpaint video](<{self.speedpaint_video_url}>)"

		return f"> **[{self.title}](<{self.image_link}>)** (_{self.name}, #{self.ordinal}, canon: {self.canon if self.canon is not None else "none"}, {speedpaint_video_url}_)"


@dataclass
class ImageDescription:
	"""Data class containing an image description."""

	title: str
	description: str | None
	image_link: str

	type ImageDescriptionType = dict[str, str | None]

	@staticmethod
	def from_obj(
		title: str, image_link: str, obj: ImageDescriptionType
	) -> "ImageDescription":
		"""Create an ImageDescription from an object.

		Argument:
		---------
		title -- The title of the image.
		image_link -- The link to the image.
		obj -- The object to create a ImageDescription from.
		(Expected: image_description, converted from json.)
		"""
		return ImageDescription(
			title,
			obj.get("description"),
			image_link,
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"title: {self.title}",
				f"description: {self.description}",
				f"image link: {self.image_link}",
			)
		)

		return "\n".join(str_list)

	def format(self) -> str:
		"""Return a string with discord formatting."""
		description_join_list = []

		description_join_list.extend(
			(
				f"> ## [{self.title}](<{self.image_link}>)",
				(
					f">>> {self.description.rstrip()}"
					if self.description is not None
					else "no description"
				),
			)
		)

		return "\n".join(description_join_list)


@dataclass
class Sketch:
	"""Data class containing a sketch."""

	name: str
	title: str
	image_url: str
	thumb_url: str
	sketch_link: str

	type SketchType = dict[str, str]

	@staticmethod
	def from_obj(sketch_link: str, obj: SketchType) -> "Sketch":
		"""Create a Sketch from an object.

		Arguments:
		---------
		sketch_link -- The link to the sketch.
		obj -- The object to create a Sketch from.
		(Expected: an item from all_sketches["sketches"].
		all_sketches needs to be converted from json first.
		["image_url"] and ["thumb_url"] should have the full URL.)
		"""
		return Sketch(
			obj["name"], obj["title"], obj["image_url"], obj["thumb_url"], sketch_link
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"name: {self.name}",
				f"title: {self.title}",
				f"image url: {self.image_url}",
				f"thumb url: {self.thumb_url}",
				f"sketch link: {self.sketch_link}",
			)
		)

		return "\n".join(str_list)

	def format(self, formatting: dict[str, bool] | None = None) -> str:
		"""Return a string with discord formatting.

		Keyword Arguments:
		-----------------
		formatting -- Defines which items to show and in what order (based on dict order).
		Items that shouldn't be shown don't need to be included. Non-existent items are ignored.

		Valid formatting items:
		-----------------------
		"title" -- Title of the sketch (can contain a link to the sketch) (default: True),
		"name" -- Identifying name of the sketch (default: False),
		"image_url" -- URL with the image data (default: False)
		"thumb_url" -- URL with the thumbnail data (default: False)
		"sketch_link" -- URL to the sketch itself (default: True)
		"""
		if formatting is None:
			formatting = {
				"title": True,
				"name": False,
				"image_url": False,
				"thumb_url": False,
				"sketch_link": True,
			}

		valid_formatting = [
			"title",
			"name",
			"image_url",
			"thumb_url",
			"sketch_link",
		]
		formatting = [
			i for i, j in formatting.items() if i in valid_formatting and j is True
		]

		image_join_list = []
		image_url_done = False
		thumb_url_done = False

		for format_ in formatting:
			if format_ == "name":
				image_join_list.append(f"> ___{self.name}___")

			if format_ == "title":
				title = self.title
				if "sketch_link" in formatting:
					title = f"[{title}](<{self.sketch_link}>)"
				image_join_list.append(f"> ## {title}")

			if format_ == "image_url" and not thumb_url_done:
				image_url = f"{self.image_url}"
				image_url = f"> [image url](<{image_url}>)"
				if "thumb_url" in formatting:
					thumb_url = f"{self.thumb_url}"
					thumb_url = f"[thumbnail url](<{thumb_url}>)"
					image_url = f"{image_url} | {thumb_url}"
				image_join_list.append(image_url)
				image_url_done = True

			if format_ == "thumb_url" and not image_url_done:
				thumb_url = f"{self.thumb_url}"
				thumb_url = f"> [thumbnail url](<{thumb_url}>)"
				if "image_url" in formatting:
					image_url = f"{self.image_url}"
					image_url = f"[image url](<{image_url}>)"
					thumb_url = f"{thumb_url} | {image_url}"
				image_join_list.append(thumb_url)
				thumb_url_done = True

			if format_ == "sketch_link" and "title" not in formatting:
				sketch_link = f"> <{self.sketch_link}>"
				image_join_list.append(sketch_link)

		return "\n".join(image_join_list)

	def format_inline(self) -> str:
		"""Return a string with discord formatting (without linebreaks)."""
		return f"> **[{self.title}](<{self.sketch_link}>)** (_{self.name}_)"


@dataclass
class Record:
	"""Data class containing record metadata."""

	chapter: str
	name: str
	title: str
	solved: bool
	iteration: str | None
	linked_puzzles: list[str] | None
	record_link: str | None
	puzzle_links: list[str] | None

	type RecordType = dict[str, str | bool | None]

	@staticmethod
	def from_obj(record_link: str | None, puzzle_links: list[str] | None, obj: RecordType) -> "Record":
		"""Create a Record from an object.

		Arguments:
		---------
		record_link -- The link to the record.
		obj -- The object to create a Record from.
		(Expected: single_record or an item from ["records"] from full_episodic.
		single_record and full_episodic need to be converted from json first.)
		"""
		return Record(
			obj["chapter"],
			obj["name"],
			obj["title"],
			obj["solved"],
			obj.get("iteration"),
			obj.get("linked_puzzles"),
			record_link,
			puzzle_links,
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"chapter: {self.chapter}",
				f"name: {self.name}",
				f"title: {self.title}",
				f"solved: {self.solved}",
				f"iteration: {self.iteration}",
				f"linked puzzles: {self.linked_puzzles}",
				f"record link: {self.record_link}",
				f"puzzle links: {self.puzzle_links}",
			)
		)

		return "\n".join(str_list)

	def format(self, formatting: dict[str, bool] | None = None) -> str:
		"""Return a string with discord formatting.

		Keyword Arguments:
		-----------------
		formatting -- Defines which items to show and in what order (based on dict order).
		Items that shouldn't be shown don't need to be included. Non-existent items are ignored.

		Valid formatting items:
		-----------------------
		"title" -- The record title (can contain a link to the record) (default: True)
		"name" -- Identifying name of the record (default: True)
		"iteration" -- The record's iteration (default: True)
		"chapter" -- Chapter the record belongs to (default: True)
		"solved" -- Whether the record is solved (default: False)
		"puzzles" -- Any puzzles linked to this record (default: False unless unsolved)
		"record_link" -- URL to the record itself (default: True)
		"puzzle_links" -- URLs to linked puzzles (default: False unless unsolved)
		"""
		if formatting is None:
			formatting = {
				"title": True,
				"name": True,
				"iteration": True,
				"chapter": True,
				"solved": False,
				"puzzles": not self.solved,
				"record_link": True,
				"puzzle_links": not self.solved,
			}

		valid_formatting = [
			"title",
			"name",
			"iteration",
			"chapter",
			"solved",
			"puzzles",
			"record_link",
			"puzzle_links",
		]
		formatting = [
			i for i, j in formatting.items() if i in valid_formatting and j is True
		]

		record_join_list = []
		name_done = False
		iteration_done = False

		for format_ in formatting:
			if format_ == "chapter" and self.chapter:
				chapter = f"> _chapter {self.chapter}_"
				record_join_list.append(chapter)

			if format_ == "name" and not iteration_done:
				name = f"> (_{self.name}"
				if "iteration" in formatting and self.iteration is not None:
					name = f"{name}, in {self.iteration}"
				name = f"{name}_)"
				record_join_list.append(name)
				name_done = True

			if format_ == "title":
				title = self.title
				if not self.solved:
					title = f"_{title} →_"
				if "record_link" in formatting and self.record_link is not None:
					title = f"[{title}]({self.record_link})"
				record_join_list.append(f"> ## {title}")

			if format_ == "solved":
				solved = "".join(("> _solved: ", "yes" if self.solved else "no", "_"))
				record_join_list.append(solved)

			if format_ == "iteration" and self.iteration is not None and not name_done:
				iteration = f"> (_in {self.iteration}"
				if "name" in formatting:
					iteration = f"{iteration}, {self.name}"
				iteration = f"{iteration}_)"
				record_join_list.append(iteration)
				iteration_done = True

			if format_ == "puzzles":
				puzzles_list = self.linked_puzzles
				if puzzles_list is not None and "puzzle_links" in formatting and self.puzzle_links is not None:
					for i in range(len(puzzles_list)):
						puzzles_list[i] = f"[{puzzles_list[i]}](<{self.puzzle_links[i]}>)"
				puzzles = "".join((("> _linked puzzles: " if (self.linked_puzzles is not None and len(self.linked_puzzles) > 1) else "> _linked puzzle: "), ("none" if puzzles_list is None else ", ".join(puzzles_list)), "_"))
				record_join_list.append(puzzles)

			if (
				format_ == "record_link"
				and self.record_link is not None
				and "title" not in formatting
			):
				record_link = f"> <{self.record_link}>"
				record_join_list.append(record_link)

			if (
				format_ == "puzzle_links"
				and self.puzzle_links is not None
				and ("puzzles" not in formatting or self.linked_puzzles is None)
			):
				puzzle_links = f"> _[solve more puzzles to reveal this record](<{self.puzzle_links[0]}>)_" if self.linked_puzzles is None else f"> <{">\n> <".join(self.puzzle_links)}>"
				record_join_list.append(puzzle_links)

		return "\n".join(record_join_list)

	def format_inline(
		self, *, show_iteration: bool = True, show_chapter: bool = True, show_puzzles: bool = True
	) -> str:
		"""Return a string with discord formatting (without linebreaks).

		If the record is unsolved, arguments are ignored and returns ?s.

		Keyword Arguments:
		-----------------
		show_iteration -- Include the iteration in the string (default: True)
		show_chapter -- Include the chapter in the string (default: True)
		"""
		name = self.name
		title = self.title
		if not self.solved:
			title = f"_{title} →_"
		if self.record_link is not None:
			title = f"[{title}](<{self.record_link}>)"
		iteration = None if self.iteration is None else f"in {self.iteration}"
		chapter = f"chapter {self.chapter}"

		parentheses = [name]
		if show_iteration and iteration is not None:
			parentheses.append(iteration)
		if show_chapter:
			parentheses.append(chapter)

		puzzles = ""
		if show_puzzles and self.linked_puzzles is not None:
			puzzles = " - linked puzzles: " if len(self.linked_puzzles) > 1 else " - linked puzzle: "
			puzzles_list = self.linked_puzzles
			if self.puzzle_links is not None:
				for i in range(len(puzzles_list)):
					puzzles_list[i] = f"[{puzzles_list[i]}](<{self.puzzle_links[i]}>)"
			puzzles += ", ".join(puzzles_list)

		return f"> **{title}** (_{', '.join(parentheses)}_){puzzles}"


@dataclass
class Chapter:
	"""Data class containing chapter metadata."""

	name: str
	records: list[Record]

	type ChapterType = dict[str, str | list[Record.RecordType]]

	@staticmethod
	def from_obj(record_base: str, puzzle_base: str, obj: ChapterType) -> "Chapter":
		"""Create a Chapter from an object.

		Arguments:
		---------
		record_base -- The base URL for records.
		puzzle_base -- The base URL for puzzles.
		obj -- The object to create a Chapter from.
		(Expected: an item from full_episodic["chapters"].
		full_episodic needs to be converted from json first.)
		"""
		records = []
		for i in obj["records"]:
			record_link = f"{record_base}{i["name"]}"
			puzzle_links = None
			if not i["solved"]:
				if i.get("linked_puzzles") is not None:
					puzzle_links = [f"{puzzle_base}{j}" for j in i["linked_puzzles"]]
				else:
					puzzle_links = [puzzle_base]
			records.append(Record.from_obj(record_link, puzzle_links, i))

		return Chapter(
			obj["name"],
			records,
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"name: {self.name}",
				f"records: {[i.name for i in self.records]}",
			)
		)

		return "\n".join(str_list)

	def format(self) -> str:
		"""Return a string with discord formatting."""
		episodic_join_list = []

		episodic_join_list.append(f"> ## {self.name}")

		episodic_join_list.extend(
			record.format_inline(show_chapter=False, show_puzzles=not record.solved) for record in self.records
		)

		unsolved_records = None
		num_unsolved_records = 0
		for record in self.records:
			if not record.solved is None:
				num_unsolved_records += 1
				if record.linked_puzzles is None and record.puzzle_links is not None and unsolved_records is None:
					unsolved_records = record.puzzle_links[0]

		if unsolved_records is not None:
			episodic_join_list.append(f"> _[solve more puzzles to reveal the remaining {"records" if num_unsolved_records > 1 else "record"}](<{unsolved_records}>)_")

		return "\n".join(episodic_join_list)


@dataclass
class RecordLine:
	"""Data class containing a record line."""

	character: str | None
	language: str | None
	emphasis: str | None
	text: str

	type RecordLineType = dict[str, str | None]

	@staticmethod
	def from_obj(obj: RecordLineType) -> "RecordLine":
		"""Create a RecordLine from an object.

		Argument: obj -- The object to create a RecordLine from.
		(Expected: an item from record_text["lines"].
		record_text needs to be converted from json first.)
		"""
		return RecordLine(
			obj.get("character"),
			obj.get("language"),
			obj.get("emphasis"),
			obj["text"],
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"character: {self.character}",
				f"language: {self.language}",
				f"emphasis: {self.emphasis}",
				f"text: {self.text}",
			)
		)

		return "\n".join(str_list)

	def format(
		self, last_character: str | None, last_language: str | None
	) -> tuple[str, str | None, str | None]:
		"""Return a tuple of string with discord formatting, last character, and last language.

		Arguments:
		---------
		last_character -- The character returned by the last formatted line (or None).
		last_language -- The language returned by the last formatted line (or None).
		"""
		text = self.format_text()

		if text.startswith(("- ", "* ")):
			text = f"\n{text}"

		if self.character is None:
			if text.count("**") == 2:  # noqa: PLR2004
				text = text.replace("**", "")
				line_string = f"`< {text}>`" if text.endswith(" ") else f"`< {text} >`"
				line_string = f"**{line_string}**"
			else:
				line_string = f"`< {text}>`" if text.endswith(" ") else f"`< {text} >`"
		else:
			speaker = []

			if self.language != last_language:
				if self.language is None:
					speaker.append("(in unknown language)")
				else:
					speaker.append(f"(in {self.language})")

			if self.character != last_character:
				if self.character == "Narrator":
					speaker.append(self.character)
				else:
					speaker.append(f"`{self.character}`")

			if self.emphasis is not None:
				speaker.append(f"({self.emphasis})")

			line_string = " ".join(speaker)
			if text.startswith(("* ", "- ")):
				line_string = f"{line_string} **:**\n{text}"
			else:
				line_string = f"{line_string} **:** {text}"

			last_character = self.character
			last_language = self.language

		line_string = f"> {line_string}"
		line_string = line_string.replace("\n", "\n> ")
		line_string = line_string.removesuffix("\n> ")
		return (line_string, last_character, last_language)

	def format_text(self) -> str:
		"""Get the text without newlines and whitespace in the middle."""
		text = self.text

		if self.character is None:
			return text

		text = re.sub(r"(  ++|\n *+)(?![\*-])", " ", text)

		if text.startswith(("- ", "* ")):
			text = f"\n{text}"

		return text


@dataclass
class RecordText:
	"""Data class containing a record's text."""

	title: str
	iteration: str
	header_lines: list[str]
	languages: list[str]
	characters: list[str]
	lines: list[RecordLine]
	record_link: str

	type RecordTextType = dict[str, str | list[str] | list[RecordLine.RecordLineType]]

	@staticmethod
	def from_obj(title: str, record_link: str, obj: RecordTextType) -> "RecordText":
		"""Create a RecordText from an object.

		Arguments:
		---------
		title -- The title of the record.
		record_link -- The link to the record.
		obj -- The object to create a RecordText from.
		(Expected: record_text, converted from json.)
		"""
		return RecordText(
			title,
			obj["iteration"],
			obj["header_lines"],
			obj["languages"],
			obj["characters"],
			[RecordLine.from_obj(i) for i in obj["lines"]],
			record_link,
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"title: {self.title}",
				f"iteration: {self.iteration}",
				f"header_lines: {self.header_lines}",
				f"languages: {self.languages}",
				f"characters: {self.characters}",
				f"num lines: {len(self.lines)}",
				f"record link: {self.record_link}",
			)
		)

		return "\n".join(str_list)

	def format(self) -> str:
		"""Return a string with discord formatting."""
		record_join_list = []

		requested = True
		for line in self.header_lines:
			if "unrequested" in line:
				requested = False
				break

		if requested:
			record_join_list.append(os.getenv("NSIRP_EMOJI", "> NSIRP"))
		record_join_list.append(f"> ## [{self.title}](<{self.record_link}>)")

		pre_header = f"> (_iteration: {self.iteration}; language(s): "

		languages = ", ".join(self.languages)
		pre_header = f"{pre_header}{languages}; character(s): "

		characters = ", ".join(self.characters)
		pre_header = f"{pre_header}{characters}_)"

		record_join_list.extend(
			(
				pre_header,
				"> _ _\n> ```",
				*(f"> {line}" for line in self.header_lines),
				"> ```",
			)
		)

		last_character = None
		last_language = None
		for line in self.lines:
			line_string, last_character, last_language = line.format(
				last_character, last_language
			)

			record_join_list.append(line_string)

		return "\n".join(record_join_list)


@dataclass
class SearchResult:
	"""Data class containing a search result."""

	type: str
	image: Image | None
	record: Record | None
	record_line: RecordLine | None
	record_matched_text: str | None
	record_line_index: int | None

	type SearchResultType = dict[
		str,
		str
		| Image.ImageType
		| Record.RecordType
		| RecordLine.RecordLineType
		| RecordLine
		| int
		| None,
	]

	@staticmethod
	def from_obj(
		image_base: str, record_base: str, puzzle_base: str, obj: SearchResultType
	) -> "SearchResult":
		"""Create a SearchResult from an object.

		Arguments:
		---------
		record_base -- The base URL for records.
		image_base -- The base URL for images.
		obj -- The object to create a SearchResult from.
		(Expected: an item from domain_search["results"].
		search_results needs to be converted from json first.
		If the type is "episodic-line", obj["record_line"] should be a RecordLine or a compatible dictionary.)
		"""
		if obj.get("record_line") is not None and isinstance(obj["record_line"], dict):
			obj["record_line"] = RecordLine.from_obj(obj["record_line"])

		image_link = None
		record_link = None
		puzzle_links = None
		if obj.get("image") is not None:
			image_link = f"{image_base}{obj["image"]["name"]}"
		if obj.get("record") is not None:
			if obj["record"]["solved"]:
				record_link = f"{record_base}{obj["record"]["name"]}"
			if obj["record"].get("linked_puzzles") is not None:
				puzzle_links = [f"{puzzle_base}{i}" for i in obj["record"]["linked_puzzles"]]

		return SearchResult(
			obj["type"],
			None
			if obj.get("image") is None
			else Image.from_obj(image_link, obj["image"]),
			None
			if obj.get("record") is None
			else Record.from_obj(record_link, puzzle_links, obj["record"]),
			obj.get("record_line"),
			obj.get("record_matched_text"),
			obj.get("record_line_index"),
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"type: {self.type}",
				f"image: {self.image}",
				f"record: {self.record}",
				f"record_line: {self.record_line}",
				f"record_matched_text: {self.record_matched_text}",
				f"record_line_index: {self.record_line_index}",
			)
		)

		return "\n".join(str_list)

	def format(self, last_record: Record | None = None) -> str:
		"""Return a string with discord formatting."""
		results_join_list = []

		match self.type:
			case "image":
				return self.image.format_inline()

			case "episodic-item":
				return self.record.format_inline(show_puzzles=not self.record.solved)

			case "episodic-line":
				if last_record != self.record:
					if last_record is not None:
						results_join_list.append("")

					record_str = self.record.format_inline(
						show_iteration=False, show_chapter=False, show_puzzles=False
					)
					results_join_list.append(record_str)

				if self.record.solved:
					matching_text = self.record_line.text

					if not (
						re.search(r"\n *\* ", matching_text)
						or re.search(r"\n *- ", matching_text)
					):
						matching_text = matching_text.replace("\n", " ")
						matching_text = re.sub(r" {2,}", " ", matching_text)
					matching_text = matching_text.strip()

					matching_text = matching_text.replace(
						self.record_matched_text,
						f"**{self.record_matched_text}**",
					)

					split_text = matching_text.split("\n")
					for i in range(len(split_text)):
						if self.record_matched_text not in split_text[i]:
							split_text[i] = None

					for i in range(1, len(split_text)):
						while (
							i < len(split_text)
							and split_text[i] is None
							and split_text[i - 1] is None
						):
							split_text.pop(i)
						if (
							i < len(split_text)
							and split_text[i - 1] is None
							and split_text[i].startswith("  ")
						):
							split_text[i] = split_text[i].lstrip(" ")

					for i in range(len(split_text)):
						if split_text[i] is None:
							split_text[i] = "[ ... ]"

					edited_line = RecordLine(
						self.record_line.character,
						self.record_line.language,
						self.record_line.emphasis,
						"\n".join(split_text),
					)
					record_text = edited_line.format(None, None)[0]
					results_join_list.append(f"{record_text}")

				return "\n".join(results_join_list)


@dataclass
class MatchResult:
	"""Data class containing a search result."""

	record: Record
	record_line: RecordLine
	line_match: re.Match

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"record: {self.record}",
				f"record_line: {self.record_line}",
				f"line_match: {self.line_match}",
			)
		)

		return "\n".join(str_list)

	def format(self, last_record: Record | None = None) -> str:
		"""Return a string with discord formatting."""
		results_join_list = []

		if last_record != self.record:
			if last_record is not None:
				results_join_list.append("")

			record_str = self.record.format_inline(
				show_iteration=False, show_chapter=False, show_puzzles=False
			)
			results_join_list.append(record_str)

		if self.record.solved:
			matching_text: str = self.record_line.text

			match_start = self.line_match.start()
			match_end = self.line_match.end()
			matching_text = f"{matching_text[:match_start]}**{matching_text[match_start:match_end]}**{matching_text[match_end:]}"

			split_text = matching_text.split("\n")
			scan_len = 0
			for i in range(len(split_text)):
				current_len = len(split_text[i])
				if (
					scan_len < match_start and scan_len + current_len < match_start
				) or (scan_len > match_end and scan_len + current_len > match_end):
					split_text[i] = None
				scan_len += current_len

			for i in range(1, len(split_text)):
				while (
					i < len(split_text)
					and split_text[i] is None
					and split_text[i - 1] is None
				):
					split_text.pop(i)
				if (
					i < len(split_text)
					and split_text[i - 1] is None
					and split_text[i].startswith("  ")
				):
					split_text[i] = split_text[i].lstrip(" ")

			for i in range(len(split_text)):
				if split_text[i] is None:
					split_text[i] = "[ ... ]"

			edited_line = RecordLine(
				self.record_line.character,
				self.record_line.language,
				self.record_line.emphasis,
				"\n".join(split_text),
			)
			record_text = edited_line.format(None, None)[0]
			results_join_list.append(f"{record_text}")

		return "\n".join(results_join_list)
