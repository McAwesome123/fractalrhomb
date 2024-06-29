# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module for accessing the fractalthorns API"""

import json
import datetime as dt
import re

from typing import Dict, List, Tuple, Optional, Union
from enum import StrEnum
from io import BytesIO
from os import getenv
from PIL import Image
from dotenv import load_dotenv

import requests

from api_access import RequestArgument, Request, API

load_dotenv()

class FractalthornsAPI(API):
	"""A class for accessing the fractalthorns API"""
	class ValidRequests(StrEnum):
		"""An enum containing all valid API endpoints"""
		ALL_NEWS = "all_news"
		SINGLE_IMAGE = "single_image"
		IMAGE_DESCRIPTION = "image_description"
		ALL_IMAGES = "all_images"
		FULL_EPISODIC = "full_episodic"
		SINGLE_RECORD = "single_record"
		RECORD_TEXT = "record_text"
		DOMAIN_SEARCH = "domain_search"

	class InvalidPurgeReasons(StrEnum):
		"""An enum containing reasons for not allowing a purge"""
		CACHE_PURGE = "Too soon since last cache purge"
		ALL_IMAGES_REQUEST = "Too soon after a request for all images"
		ALL_RECORDS_TEXT_REQUEST = "Too soon after a request for all record contents"

	def __init__(self):
		__all_news = Request(
			self.ValidRequests.ALL_NEWS.value,
			None
		)

		__single_image = Request(
			self.ValidRequests.SINGLE_IMAGE.value,
			[RequestArgument("name", True)]
		)

		__image_description = Request(
			self.ValidRequests.IMAGE_DESCRIPTION.value,
			[RequestArgument("name", False)]
		)

		__all_images = Request(
			self.ValidRequests.ALL_IMAGES.value,
			None
		)

		__full_episodic = Request(
			self.ValidRequests.FULL_EPISODIC.value,
			None
		)

		__single_record = Request(
			self.ValidRequests.SINGLE_RECORD.value,
			[RequestArgument("name", False)]
		)

		__record_text = Request(
			self.ValidRequests.RECORD_TEXT.value,
			[RequestArgument("name", False)]
		)

		__domain_search = Request(
			self.ValidRequests.DOMAIN_SEARCH.value,
			[
				RequestArgument("term", False),
				RequestArgument("type", False),
			]
		)

		__requests_list = {
			self.ValidRequests.ALL_NEWS.value: __all_news,
			self.ValidRequests.SINGLE_IMAGE.value: __single_image,
			self.ValidRequests.IMAGE_DESCRIPTION.value: __image_description,
			self.ValidRequests.ALL_IMAGES.value: __all_images,
			self.ValidRequests.FULL_EPISODIC.value: __full_episodic,
			self.ValidRequests.SINGLE_RECORD.value: __single_record,
			self.ValidRequests.RECORD_TEXT.value: __record_text,
			self.ValidRequests.DOMAIN_SEARCH.value: __domain_search,
		}

		super().__init__("https://fractalthorns.com", "/api/v1/", __requests_list)

		self.__valid_image_urls: Optional[Tuple[List[str], dt.datetime]] = None
		self.__valid_record_urls: Optional[Tuple[List[str], dt.datetime]] = None
		self.__cached_news_items: Optional[Tuple[List[Dict[str, str]], dt.datetime]] = None
		self.__cached_images: Dict[str, Tuple[Dict[str, Union[str, int, bool, List[str], None]],
											  dt.datetime]] = {}
		self.__cached_image_contents: Dict[str, Tuple[Tuple[Image.Image, Image.Image], dt.datetime]] = {}
		self.__cached_image_descriptions: Dict[str, Tuple[Optional[str], dt.datetime]] = {}
		self.__cached_chapters: Optional[Tuple[Dict[str, List[Dict[str, Union[str, bool, None]]]],
											   dt.datetime]] = None
		self.__cached_records: Dict[str, Tuple[Dict[str, Union[str, bool, None]], dt.datetime]] = {}
		self.__cached_record_contents: \
			Dict[str, Tuple[Dict[str, Union[bool, str, List[str],List[Optional[str]], None]],
							dt.datetime]] = {}
		self.__cache_purge_allowed: Tuple[dt.datetime, str] = (dt.datetime.now(dt.UTC),)

	__CACHE_DURATION: dt.timedelta = dt.timedelta(days = 1)
	__CACHE_PURGE_COOLDOWN: dt.timedelta = dt.timedelta(hours = 2)
	__REQUEST_TIMEOUT: float = 10.0
	__NOT_FOUND_ERROR: str = "Item not found"
	__DEFAULT_HEADERS: Dict[str, str] = {"User-Agent": getenv("FRACTALTHORNS_USER_AGENT")}

	def make_request(self, endpoint: str, request_payload: Optional[Dict[str, str]],
					 *, strictly_match_request_arguments: bool = True,
					 headers: Optional[Dict[str, str]] = None):
		if headers is None:
			headers = self.__DEFAULT_HEADERS

		return super().make_request(
			endpoint,
			request_payload,
			strictly_match_request_arguments = strictly_match_request_arguments,
			headers = headers
		)

	def purge_cache(self, *, force_purge: bool = False):
		"""Purges stored cache items unless it's too soon since last purge

		Keyword Arguments:
		force_purge -- Forces a cache purge regardless of time

		Raises:
		PermissionError -- Cannot purge now. Try again later. Contains:
			datetime.datetime -- When a purge will be allowed.
			str -- Reason
		"""
		if force_purge or dt.datetime.now(dt.UTC) > self.__cache_purge_allowed[0]:
			self.__valid_image_urls = None
			self.__valid_record_urls = None
			self.__cached_news_items = None
			self.__cached_images = {}
			self.__cached_image_contents = {}
			self.__cached_image_descriptions = {}
			self.__cached_chapters = {}
			self.__cached_records = {}
			self.__cached_record_contents = {}
			new_time = dt.datetime.now(dt.UTC) + self.__CACHE_PURGE_COOLDOWN
			if self.__cache_purge_allowed[0] < new_time:
				self.__cache_purge_allowed = (new_time,
											  self.InvalidPurgeReasons.CACHE_PURGE.value)
		else:
			raise PermissionError(self.__cache_purge_allowed)

	def get_news_items(
			self,
			*,
			formatting: Dict[str, bool] = None,
			start_index = 0,
			amount = 1
	) -> str:
		"""Get news items from fractalthorns.

		Keyword Arguments:
		formatting -- Items set to True appear in the order they're defined in.
		Valid items (default): "title" (True), "date" (True),
		"changes" (True), "version" (True).
		start_index -- Which news item to start at (default 0)
		amount -- How many news items to display (default 1)
		"""
		if formatting is None:
			formatting = {
				"title": True,
				"date": True,
				"changes": True,
				"version": True,
			}

		news_items = []
		news_list = []

		if start_index >= 0:
			if amount < 0:
				news_items = self.__get_news_items()[start_index::1]
			else:
				news_items = self.__get_news_items()[start_index:start_index+amount:1]
		else:
			if amount < 0:
				news_items = self.__get_news_items()[start_index::-1]
			else:
				news_items = self.__get_news_items()[start_index:start_index-amount:-1]

		for i in news_items:
			news_list.append(self.__format_news_item(i, formatting))

		return "\n\n".join(news_list)

	def get_single_image(
			self,
			name: Optional[str],
			*,
			formatting: Dict[str, bool] = None
		) -> Tuple[str, Tuple[Image.Image, Image.Image]]:
		"""Get an image from fractalthorns.

		Arguments:
		name -- Identifying name of the image.

		Keyword Arguments:
		formatting -- Items set to True appear in the order they're defined in.
		Valid items (default): "title" (True), "name" (False),
		"ordinal" (False), "date" (False), "image_url" (False),
		"thumb_url" (False), "canon" (True), "has_description" (False),
		"characters" (True), "speedpaint_video_url" (True)
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
			}

		image = self.__get_single_image(name)
		image_info = self.__format_single_image(image, formatting)
		image_contents = self.__get_image_contents(name)
		return (image_info, image_contents)

	def get_image_description(self, name: str) -> str:
		"""Get image description from fractalthorns.

		Arguments:
		name -- Identifying name of the image.
		"""
		image_title = self.__get_single_image(name)["title"]
		image_description = self.__get_image_description(name)

		image_title = "".join((">>> ## ", image_title))
		image_description = image_description.rstrip() if image_description is not None \
				else "no description"

		return "\n".join((image_title, image_description))

	def get_all_images(self, *, start_index = 0, amount = 10) -> str:
		"""Get all images from fractalthorns.

		Keyword Arguments:
		start_index -- Which image to start at (default 0).
		amount -- How many images to show (default 10).
		"""
		image_join_list = []

		if start_index >= 0:
			if amount < 0:
				images = self.__get_all_images()[start_index::1]
			else:
				images = self.__get_all_images()[start_index:start_index+amount:1]
		else:
			if amount < 0:
				images = self.__get_all_images()[start_index::-1]
			else:
				images = self.__get_all_images()[start_index:start_index-amount:-1]

		for image in images:
			image_str = "".join(("> **", image["title"], "** (_#",
								 str(image["ordinal"]), ", ", image["name"], "_)"))
			image_join_list.append(image_str)
		return "\n".join(image_join_list)

	def get_full_episodic(self, *, display_chapters: List[str] = None) -> str:
		"""Get the full episodic from fractalthorns

		Keyword Arguments:
		display_chapters -- Names of chapters to display (default: latest one)
		"""
		if display_chapters is None:
			display_chapters = []
			display_chapters.append(list(self.__get_full_episodic().keys())[-1])

		chapters = self.__get_full_episodic()
		chapters_dict = {}

		for chapter in chapters:
			if chapter in display_chapters:
				chapters_dict.update({chapter: chapters[chapter]})

		return self.__format_full_episodic(chapters_dict)

	def get_single_record(self, name: str, *, formatting: Dict[str, bool] = None) -> str:
		"""Get a record from fractalthorns.

		Arguments:
		name -- Identifying name of the record.

		Keyword Arguments:
		formatting -- Items set to True appear in the order they're defined in.
		Valid items (default): "title" (True), "name" (True),
		"iteration" (True), "chapter" (True), "solved" (False)
		"""
		if formatting is None:
			formatting = {
				"title": True,
				"name": True,
				"iteration": True,
				"chapter": True,
				"solved": False,
			}

		record = self.__get_single_record(name)

		return self.__format_single_record(record, formatting)

	def get_record_text(self, name: str):
		"""Get the contents of a record from fractalthorns.

		Arguments:
		name -- Identifying name of the record.
		"""
		record = self.__get_single_record(name)
		if record["solved"]:
			title = record["title"]
		else:
			title = "??????"

		record_text = self.__get_record_text(name)

		return self.__format_record_text((title, record_text))

	def get_domain_search(self, term: str, type_: str):
		"""not implemented"""
		return self.make_request("domain_search", {"term": term, "type": type_})


	def __get_images_list(self) -> List[str]:
		if self.__valid_image_urls is None or dt.datetime.now(dt.UTC) > self.__valid_image_urls[1]:
			self.__get_all_images()

		return self.__valid_image_urls[0]

	def __get_records_list(self) -> List[str]:
		if self.__valid_record_urls is None or dt.datetime.now(dt.UTC) > self.__valid_record_urls[1]:
			self.__get_full_episodic()

		return self.__valid_record_urls[0]

	def __get_news_items(self) -> List[Dict[str, str]]:
		if self.__cached_news_items is None or dt.datetime.now(dt.UTC) > self.__cached_news_items[1]:
			r = self.make_request(self.ValidRequests.ALL_NEWS.value, None)
			r.raise_for_status()

			self.__cached_news_items = (json.loads(r.text)["items"],
										dt.datetime.now(dt.UTC) + self.__CACHE_DURATION)

		return self.__cached_news_items[0]

	def __get_single_image(self, image: str) -> Dict[str, str]:
		if image is not None and image not in self.__get_images_list():
			raise ValueError(self.__NOT_FOUND_ERROR)

		if image not in self.__cached_images or dt.datetime.now(dt.UTC) > self.__cached_images[image][1]:
			r = self.make_request(self.ValidRequests.SINGLE_IMAGE.value, {"name": image})
			r.raise_for_status()
			image_metadata = json.loads(r.text)

			self.__cached_images.update({image: (image_metadata,
												 dt.datetime.now(dt.UTC) + self.__CACHE_DURATION)})

		return self.__cached_images[image][0]

	def __get_image_contents(self, image: str) -> Tuple[Image.Image, Image.Image]:
		if image is not None and image not in self.__get_images_list():
			raise ValueError(self.__NOT_FOUND_ERROR)

		if image not in self.__cached_image_contents \
				or dt.datetime.now(dt.UTC) > self.__cached_image_contents[image][1]:
			image_metadata = self.__get_single_image(image)

			image_req = requests.get(''.join((self._base_url, image_metadata["image_url"])),
									 timeout = self.__REQUEST_TIMEOUT, headers = self.__DEFAULT_HEADERS)
			image_req.raise_for_status()
			image_contents = Image.open(BytesIO(image_req.content))

			thumb_req = requests.get(''.join((self._base_url, image_metadata["thumb_url"])),
									 timeout = self.__REQUEST_TIMEOUT, headers = self.__DEFAULT_HEADERS)
			thumb_req.raise_for_status()
			image_thumbnail = Image.open(BytesIO(thumb_req.content))

			self.__cached_image_contents.update({image: ((image_contents, image_thumbnail),
														 dt.datetime.now(dt.UTC) + self.__CACHE_DURATION)})

		return self.__cached_image_contents[image][0]

	def __get_image_description(self, image: str) -> Optional[str]:
		if image is not None and image not in self.__get_images_list():
			raise ValueError(self.__NOT_FOUND_ERROR)

		if image not in self.__cached_image_descriptions \
				or dt.datetime.now(dt.UTC) > self.__cached_image_descriptions[image][1]:
			r = self.make_request(self.ValidRequests.IMAGE_DESCRIPTION.value, {"name": image})
			r.raise_for_status()

			image_description = json.loads(r.text)

			self.__cached_image_descriptions.update({image: (image_description.get("description"),
															 dt.datetime.now(dt.UTC) + self.__CACHE_DURATION)})

		return self.__cached_image_descriptions[image][0]

	def __get_all_images(self) -> List[Dict[str, Union[str, int, bool, List[str], None]]]:
		outdated = (self.__valid_image_urls is None
					or dt.datetime.now(dt.UTC) > self.__valid_image_urls[1])
		if not outdated:
			for image in self.__get_images_list():
				if image not in self.__cached_images \
						or dt.datetime.now(dt.UTC) > self.__cached_images[image][1]:
					outdated = True
					break

		if outdated:
			r = self.make_request(self.ValidRequests.ALL_IMAGES.value, None)
			r.raise_for_status()

			images = json.loads(r.text)["images"]
			cache_time = dt.datetime.now(dt.UTC) + self.__CACHE_DURATION

			image_urls = []
			for image in images:
				self.__cached_images.update({image["name"]: (image, cache_time)})
				image_urls.append(image["name"])

			self.__valid_image_urls = (image_urls, cache_time)

		return [i[0] for i in self.__cached_images.values()]

	def __get_full_episodic(self) -> Dict[str, List[Dict[str, Union[str, bool, None]]]]:
		if self.__cached_chapters is None or dt.datetime.now(dt.UTC) > self.__cached_chapters[1] \
			or self.__valid_record_urls is None or dt.datetime.now(dt.UTC) > self.__valid_record_urls[1]:
			r = self.make_request(self.ValidRequests.FULL_EPISODIC.value, None)
			r.raise_for_status()

			chapters_list = json.loads(r.text)["chapters"]
			cache_time = dt.datetime.now(dt.UTC) + self.__CACHE_DURATION

			chapters = {}
			for chapter in chapters_list:
				chapters.update({chapter["name"]: chapter["records"]})

			self.__cached_chapters = (chapters, cache_time)

			record_urls = []
			for chapter in chapters.values():
				for record in chapter:
					if record["solved"]:
						self.__cached_records.update({record["name"]: (record, cache_time)})
						record_urls.append(record["name"])

			self.__valid_record_urls = (record_urls, cache_time)

		return self.__cached_chapters[0]

	def __get_single_record(self, name: str) -> Dict[str, Union[str, bool, None]]:
		if name not in self.__get_records_list():
			raise ValueError(self.__NOT_FOUND_ERROR)

		if name not in self.__cached_records or dt.datetime.now(dt.UTC) > self.__cached_records[name][1]:
			r = self.make_request(self.ValidRequests.SINGLE_RECORD, {"name": name})
			r.raise_for_status()

			record = json.loads(r.text)
			if record["solved"]:
				self.__cached_records.update({record["name"]: (record, dt.datetime.now(dt.UTC))})

		return self.__cached_records[name][0]

	def __get_record_text(self, name: str) \
		-> Dict[str, Union[bool, str, List[str], List[Optional[str]], None]]:
		if name not in self.__get_records_list():
			raise ValueError(self.__NOT_FOUND_ERROR)

		if name not in self.__cached_record_contents \
				or dt.datetime.now(dt.UTC) > self.__cached_record_contents[name][1]:
			r = self.make_request(self.ValidRequests.RECORD_TEXT.value, {"name": name})
			r.raise_for_status()

			record_contents = json.loads(r.text)
			self.__cached_record_contents.update({name: (record_contents, dt.datetime.now(dt.UTC))})

		return self.__cached_record_contents[name][0]

	def __format_news_item(self, item: Dict[str, str], formatting: Dict[str, bool]) -> str:
		news_join_list = []

		for format_ in formatting.keys():
			if format_ == "title" and formatting[format_]:
				title = " ".join((">", "##", item["title"]))
				news_join_list.append(title)

			if format_ == "date" and formatting[format_]:
				date = " ".join(("on ", item["date"]))
				date = "".join(("> __", date, "__"))
				news_join_list.append(date)

			if format_ == "changes" and formatting[format_] and len(item["items"]) > 0:
				changes_list = [" ".join(("> -", i)) for i in item["items"]]
				changes = "\n".join(changes_list)
				news_join_list.append(changes)

			if format_ == "version" and formatting[format_] and item.get("version") is not None:
				version = "".join(("> _", item["version"], "_"))
				news_join_list.append(version)

		return "\n".join(news_join_list)

	def __format_single_image(self, item: Dict[str, str], formatting: Dict[str, bool]) -> str:
		image_join_list = []
		image_url_done = False
		thumb_url_done = False

		for format_ in formatting.keys():
			if format_ == "name" and formatting[format_]:
				name = "".join(("> ___", item["name"], "___"))
				image_join_list.append(name)

			if format_ == "title" and formatting[format_]:
				title = " ".join(("> ##", item["name"]))
				image_join_list.append(title)

			if format_ == "ordinal" and formatting[format_]:
				ordinal = "".join(("> _(image #", str(item["ordinal"]), ")_"))
				image_join_list.append(ordinal)

			if format_ == "date" and formatting[format_]:
				date = " ".join(("on", item["date"]))
				date = "".join(("> __", date, "__"))
				image_join_list.append(date)

			if format_ == "image_url" and formatting[format_] and not thumb_url_done:
				image_url = "".join((self._base_url, item["image_url"]))
				image_url = "".join(("> [image url](<", image_url, ">)"))
				if "thumb_url" in formatting and formatting["thumb_url"]:
					thumb_url = "".join((self._base_url, item["thumb_url"]))
					thumb_url = "".join(("[thumbnail url](<", thumb_url, ">)"))
					image_url = " | ".join((image_url, thumb_url))
				image_join_list.append(image_url)
				image_url_done = True

			if format_ == "thumb_url" and formatting[format_] and not image_url_done:
				thumb_url = "".join((self._base_url, item["thumb_url"]))
				thumb_url = "".join(("> [thumbnail url](<", thumb_url, ">)"))
				if "image_url" in formatting and formatting["image_url"]:
					image_url = "".join((self._base_url, item["image_url"]))
					image_url = "".join(("[image url](<", image_url, ">)"))
					thumb_url = " | ".join((thumb_url, image_url))
				image_join_list.append(thumb_url)
				thumb_url_done = True

			if format_ == "canon" and formatting[format_]:
				if item.get("canon") is not None:
					canon = " ".join(("canon:", item["canon"]))
				else:
					canon = "canon: none"
				canon = "".join(("> _", canon, "_"))
				image_join_list.append(canon)

			if format_ == "has_description" and formatting[format_]:
				has_description = " ".join(("> has description:", "yes" if item["has_description"] else "no"))
				image_join_list.append(has_description)

			if format_ == "characters" and formatting[format_]:
				characters = ", ".join(item["characters"])
				characters = " ".join(("> characters:", characters if characters != "" else "_none_"))
				image_join_list.append(characters)

			if format_ == "speedpaint_video_url" and formatting[format_]:
				if item.get("speedpaint_video_url") is not None:
					speedpaint = "".join(("> [speedpaint video](<", item["speedpaint_video_url"], ">)"))
				else:
					speedpaint = "> no speedpaint video"
				image_join_list.append(speedpaint)

		return "\n".join(image_join_list)

	def __format_full_episodic(self, item: Dict[str, List[Dict[str, Union[str, bool, None]]]]) -> str:
		episodic_join_list = []

		for chapter in item.keys():
			chapter_string = "".join(("\n> ## ", chapter))
			episodic_join_list.append(chapter_string)

			for record in item[chapter]:
				if record["solved"]:
					name = record["name"]
					title = record["title"]
					iteration = record["iteration"]
					record_string = "".join(("> **", title, "** (_", name, ", in ", iteration, "_)"))
					episodic_join_list.append(record_string)
				else:
					episodic_join_list.append("> **??????**")

		return ("\n".join(episodic_join_list)).lstrip()

	def __format_single_record(self, item: Dict[str, Union[str, bool, None]], \
							   formatting: Dict[str, bool]) -> str:
		record_join_list = []
		name_done = False
		iteration_done = False

		for format_ in formatting.keys():
			if format_ == "chapter" and formatting[format_]:
				chapter = "".join(("> _chapter ", item["chapter"], "_"))
				record_join_list.append(chapter)

			if format_ == "name" and formatting[format_] and not iteration_done and item["solved"]:
				name = "".join(("> (_", item["name"]))
				if "iteration" in formatting:
					name = "".join((name, ", in ", item["iteration"]))
				name = "".join((name, "_)"))
				record_join_list.append(name)
				name_done = True

			if format_ == "title" and formatting[format_] and item["solved"]:
				title = "".join(("> ## ", item["title"]))
				record_join_list.append(title)
			elif format_ == "title" and formatting[format_] and not item["solved"]:
				title = "> ## ??????"
				record_join_list.append(title)

			if format_ == "solved" and formatting[format_]:
				solved = "".join(("> _solved: ", "yes" if item["solved"] else "no", "_"))
				record_join_list.append(solved)

			if format_ == "iteration" and formatting[format_] and not name_done and item["solved"]:
				iteration = "".join(("> (_in ", item["iteration"]))
				if "name" in formatting:
					iteration = "".join((iteration, ", ", item["name"]))
				iteration = "".join((iteration, "_)"))
				record_join_list.append(iteration)
				iteration_done = True

		return "\n".join(record_join_list)

	def __format_record_text(self, item: Tuple[str, Dict[str, Union[bool, str, List[str],
																	List[Optional[str]], None]]]) -> str:
		record_title = item[0]
		record_contents = item[1]

		record_join_list = []

		requested = True
		for line in record_contents["header_lines"]:
			if "unrequested" in line:
				requested = False
				break

		if requested:
			record_join_list.append("> NSIrP")
		record_join_list.append("".join(("> ## ", record_title)))

		pre_header = "".join(("> (_iteration: ", record_contents["iteration"], "; language(s): "))

		languages_list = []
		for language in record_contents["languages"]:
			languages_list.append(language)
		languages = ", ".join(languages_list)
		pre_header = "".join((pre_header, languages, "; character(s): "))

		characters_list = []
		for character in record_contents["characters"]:
			characters_list.append(character)
		characters = ", ".join(characters_list)
		pre_header = "".join((pre_header, characters, "_)"))

		record_join_list.append(pre_header)

		record_join_list.append("> _ _\n> ```")
		for line in record_contents["header_lines"]:
			record_join_list.append("".join(("> ", line)))
		record_join_list.append("> ```")

		first = True
		last_character = None
		for line in record_contents["lines"]:
			text: str = line["text"]
			if not re.search(r"\n +\*", text):
				text = text.replace("\n", " ")
				text = re.sub(r" {2,}", " ", text)

			if line.get("character") is None:
				if text == "...":
					line_string = "".join(("`< ", text, " >`"))
				else:
					line_string = "".join(("`< ", text, ">`"))
				last_character = None
			else:
				speaker = []

				if line.get("language") is not None:
					speaker.append("".join(("(in ", line["language"], ")")))

				if line["character"] != last_character:
					speaker.append(line["character"])
					last_character = line["character"]

				if line.get("emphasis") is not None:
					speaker.append("".join(("(", line["emphasis"], ")")))

				line_string = " ".join(speaker)
				if text.startswith("*"):
					line_string = "".join((line_string, ":\n", text))
				else:
					line_string = "".join((line_string, ": ", text))

			if first:
				first = False
				line_string = "".join((">>> ", line_string))

			record_join_list.append(line_string)

		full_text = "\n".join(record_join_list)

		return full_text


api = FractalthornsAPI()

print("")
print("# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)")
print("# This script is licensed under the GNU Affero General Public License version 3 or later.")
print("# For more information, view the LICENSE file provided with this project")
print("# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html")
print("")
print("# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).")
print("# View it here: https://fractalthorns.com")
print("")
