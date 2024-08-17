# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module containing dataclasses used the fractalthorns API handler."""

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

	type ImageType = dict[str, str | datetime | int | bool | list[str] | None]

	@staticmethod
	def from_obj(obj: ImageType) -> "Image":
		"""Create an Image from an object.

		Argument: obj -- The object to create an Image from.
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
		"title" -- The image title (default: True)
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
				image_join_list.append(f"> ## {self.title}")

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

		return "\n".join(image_join_list)

	def format_inline(self) -> str:
		"""Return a string with discord formatting (without linebreaks)."""
		if self.speedpaint_video_url is None:
			return f"> **{self.title}** (_{self.name}, #{self.ordinal}, canon: {self.canon if self.canon is not None else "none"}, [image url](<{self.image_url}>), no speedpaint video_)"

		return f"> **{self.title}** (_{self.name}, #{self.ordinal}, canon: {self.canon if self.canon is not None else "none"}, [image url](<{self.image_url}>), [speedpaint video](<{self.speedpaint_video_url}>)_)"


@dataclass
class ImageDescription:
	"""Data class containing an image description."""

	title: str
	description: str | None

	type ImageDescriptionType = dict[str, str | None]

	@staticmethod
	def from_obj(obj: ImageDescriptionType) -> "ImageDescription":
		"""Create an ImageDescription from an object.

		Argument: obj -- The object to create a ImageDescription from.
		(Expected: image_description with an added title.
		image_description needs to be converted from json first.)
		"""
		return ImageDescription(
			obj["title"],
			obj.get("description"),
		)

	def __str__(self) -> str:
		"""Return the class' contents, separated by newlines."""
		str_list = []

		str_list.extend(
			(
				f"title: {self.title}",
				f"description: {self.description}",
			)
		)

		return "\n".join(str_list)

	def format(self) -> str:
		"""Return a string with discord formatting."""
		description_join_list = []

		description_join_list.extend(
			(
				f"> # {self.title}",
				(
					f">>> {self.description.rstrip()}"
					if self.description is not None
					else "no description"
				),
			)
		)

		return "\n".join(description_join_list)


@dataclass
class Record:
	"""Data class containing record metadata."""

	chapter: str
	name: str | None
	title: str | None
	solved: bool
	iteration: str | None

	type RecordType = dict[str, str | bool | None]

	@staticmethod
	def from_obj(obj: RecordType) -> "Record":
		"""Create a Record from an object.

		Argument: obj -- The object to create a Record from.
		(Expected: single_record or an item from ["records"] from full_episodic.
		single_record and full_episodic need to be converted from json first.)
		"""
		return Record(
			obj["chapter"],
			obj.get("name"),
			obj.get("title"),
			obj["solved"],
			obj.get("iteration"),
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
		"title" -- The record title (default: True)
		"name" -- Identifying name of the record (default: True)
		"iteration" -- The record's iteration (default: True)
		"chapter" -- Chapter the record belongs to (default: True)
		"solved" -- Whether the record is solved (default: False)
		"""
		if formatting is None:
			formatting = {
				"title": True,
				"name": True,
				"iteration": True,
				"chapter": True,
				"solved": False,
			}

		valid_formatting = ["title", "name", "iteration", "chapter", "solved"]
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

			if format_ == "name" and not iteration_done and self.solved:
				name = f"> (_{self.name}"
				if "iteration" in formatting:
					name = f"{name}, in {self.iteration}"
				name = f"{name}_)"
				record_join_list.append(name)
				name_done = True

			if format_ == "title" and self.solved:
				title = f"> ## {self.title}"
				record_join_list.append(title)
			elif format_ == "title" and not self.solved:
				title = "> ## ??????"
				record_join_list.append(title)

			if format_ == "solved":
				solved = "".join(("> _solved: ", "yes" if self.solved else "no", "_"))
				record_join_list.append(solved)

			if format_ == "iteration" and not name_done and self.solved:
				iteration = f"> (_in {self.iteration}"
				if "name" in formatting:
					iteration = f"{iteration}, {self.name}"
				iteration = f"{iteration}_)"
				record_join_list.append(iteration)
				iteration_done = True

		return "\n".join(record_join_list)

	def format_inline(
		self, *, show_iteration: bool = True, show_chapter: bool = True
	) -> str:
		"""Return a string with discord formatting (without linebreaks).

		If the record is unsolved, arguments are ignored and returns ?s.

		Keyword Arguments:
		-----------------
		show_iteration -- Include the iteration in the string (default: True)
		show_chapter -- Include the chapter in the string (default: True)
		"""
		if self.solved:
			name = self.name
			title = self.title
			iteration = f"in {self.iteration}"
			chapter = f"chapter {self.chapter}"

			parentheses = [name]
			if show_iteration:
				parentheses.append(iteration)
			if show_chapter:
				parentheses.append(chapter)

			return f"> **{title}** (_{', '.join(parentheses)}_)"

		return "> **??????**"


@dataclass
class Chapter:
	"""Data class containing chapter metadata."""

	name: str
	records: list[Record]

	type ChapterType = dict[str, str | list[Record.RecordType]]

	@staticmethod
	def from_obj(obj: ChapterType) -> "Chapter":
		"""Create a Chapter from an object.

		Argument: obj -- The object to create a Chapter from.
		(Expected: an item from full_episodic["chapters"].
		full_episodic needs to be converted from json first.)
		"""
		return Chapter(
			obj["name"],
			[Record.from_obj(i) for i in obj["records"]],
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
			record.format_inline(show_chapter=False) for record in self.records
		)

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
		text = self.text
		if not (re.search(r"\n *\* ", text) or re.search(r"\n *- ", text)):
			text = text.replace("\n", " ")
			text = re.sub(r" {2,}", " ", text)

		if text.startswith(("- ", "* ")):
			text = f"\n{text}"

		if self.character is None:
			line_string = f"`< {text} >`" if text == "..." else f"`< {text}>`"
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
			if text.startswith("* "):
				line_string = f"{line_string} :\n{text}"
			else:
				line_string = f"{line_string} **:** {text}"

			last_character = self.character
			last_language = self.language

		line_string = f"> {line_string}"
		line_string = line_string.replace("\n", "\n> ")
		line_string = line_string.removesuffix("\n> ")
		return (line_string, last_character, last_language)


@dataclass
class RecordText:
	"""Data class containing a record's text."""

	title: str
	iteration: str
	header_lines: list[str]
	languages: list[str]
	characters: list[str]
	lines: list[RecordLine]

	type RecordTextType = dict[str, str | list[str] | list[RecordLine.RecordLineType]]

	@staticmethod
	def from_obj(title: str, obj: RecordTextType) -> "RecordText":
		"""Create a RecordText from an object.

		Arguments:
		---------
		title -- The title of the record.
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
			record_join_list.extend(
				(
					"> <:nsirp_11:1271772847806877727><:nsirp_12:1271772877300957247>",
					"> <:nsirp_21:1271772902915706943><:nsirp_22:1271772919286206495>",
				)
			)
		record_join_list.append(f"> ## {self.title}")

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
	def from_obj(obj: SearchResultType) -> "SearchResult":
		"""Create a SearchResult from an object.

		Argument: obj -- The object to create a SearchResult from.
		(Expected: an item from domain_search["results"].
		search_results needs to be converted from json first.
		If the type is "episodic-line", obj["record_line"] should be a RecordLine or a compatible dictionary.)
		"""
		if obj.get("record_line") is not None and isinstance(obj["record_line"], dict):
			obj["record_line"] = RecordLine.from_obj(obj["record_line"])

		return SearchResult(
			obj["type"],
			None if obj.get("image") is None else Image.from_obj(obj["image"]),
			None if obj.get("record") is None else Record.from_obj(obj["record"]),
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
				return self.record.format_inline()

			case "episodic-line":
				if last_record != self.record:
					if last_record is not None:
						results_join_list.append("")

					record_str = self.record.format_inline(
						show_iteration=False, show_chapter=False
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
