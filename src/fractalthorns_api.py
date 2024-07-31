# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module for accessing the fractalthorns API."""

import datetime as dt
import json
import re
import traceback
from dataclasses import asdict
from enum import Enum, StrEnum
from io import BytesIO
from os import getenv
from pathlib import Path
from typing import ClassVar

import requests
from dotenv import load_dotenv
from PIL import Image

import src.fractalthorns_dataclasses as ftd
import src.fractalthorns_exceptions as fte
from src.api_access import API, Request, RequestArgument

load_dotenv()


class FractalthornsAPI(API):
	"""A class for accessing the fractalthorns API."""

	class ValidRequests(StrEnum):
		"""An enum containing all valid API endpoints."""

		ALL_NEWS = "all_news"
		SINGLE_IMAGE = "single_image"
		IMAGE_DESCRIPTION = "image_description"
		ALL_IMAGES = "all_images"
		FULL_EPISODIC = "full_episodic"
		SINGLE_RECORD = "single_record"
		RECORD_TEXT = "record_text"
		DOMAIN_SEARCH = "domain_search"

	class InvalidPurgeReasons(StrEnum):
		"""An enum containing reasons for not allowing a purge."""

		CACHE_PURGE = "Too soon since last cache purge"
		INVALID_CACHE = "Not a valid cache type"

	class CacheTypes(Enum):
		"""An enum containing cache types."""

		NEWS_ITEMS = "news items"
		IMAGES = "images"
		IMAGE_CONTENTS = "image contents"
		IMAGE_DESCRIPTIONS = "image descriptions"
		CHAPTERS = "chapters"
		RECORDS = "records"
		RECORD_CONTENTS = "record contents"
		SEARCH_RESULTS = "search results"
		FULL_RECORD_CONTENTS = "full record contents"
		CACHE_METADATA = "cache metadata"

	def __init__(self) -> None:
		"""Initialize the API handler."""
		__all_news = Request(self.ValidRequests.ALL_NEWS.value, None)

		__single_image = Request(
			self.ValidRequests.SINGLE_IMAGE.value,
			[RequestArgument("name", optional=True)],
		)

		__image_description = Request(
			self.ValidRequests.IMAGE_DESCRIPTION.value,
			[RequestArgument("name", optional=False)],
		)

		__all_images = Request(self.ValidRequests.ALL_IMAGES.value, None)

		__full_episodic = Request(self.ValidRequests.FULL_EPISODIC.value, None)

		__single_record = Request(
			self.ValidRequests.SINGLE_RECORD.value,
			[RequestArgument("name", optional=False)],
		)

		__record_text = Request(
			self.ValidRequests.RECORD_TEXT.value,
			[RequestArgument("name", optional=False)],
		)

		__domain_search = Request(
			self.ValidRequests.DOMAIN_SEARCH.value,
			[
				RequestArgument("term", optional=False),
				RequestArgument("type", optional=False),
			],
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

		self.__cached_news_items: tuple[list[ftd.NewsEntry], dt.datetime] | None = None
		self.__cached_images: dict[str, tuple[ftd.Image, dt.datetime]] = {}
		self.__cached_image_contents: dict[
			str, tuple[tuple[Image.Image, Image.Image], dt.datetime]
		] = {}
		self.__cached_image_descriptions: dict[
			str, tuple[ftd.ImageDescription, dt.datetime]
		] = {}
		self.__cached_chapters: tuple[dict[str, ftd.Chapter], dt.datetime] | None = None
		self.__cached_records: dict[str, tuple[ftd.Record, dt.datetime]] = {}
		self.__cached_record_contents: dict[
			str,
			tuple[
				ftd.RecordText,
				dt.datetime,
			],
		] = {}
		self.__cached_search_results: dict[
			tuple[str, str], tuple[list[ftd.SearchResult], dt.datetime]
		] = {}
		self.__cached_full_record_contents: (
			tuple[dict[str, ftd.RecordText], dt.datetime] | None
		) = None
		self.__last_all_images_cache: dt.datetime | None = None
		self.__last_full_episodic_cache: dt.datetime | None = None
		self.__last_cache_purge: dict[self.CacheTypes, dt.datetime] = {}

		self.__load_all_cache()

	__CACHE_DURATION: ClassVar[dict[CacheTypes, dt.timedelta]] = {
		CacheTypes.NEWS_ITEMS: dt.timedelta(hours=12),
		CacheTypes.IMAGES: dt.timedelta(hours=12),
		CacheTypes.IMAGE_CONTENTS: dt.timedelta(hours=72),
		CacheTypes.IMAGE_DESCRIPTIONS: dt.timedelta(hours=72),
		CacheTypes.CHAPTERS: dt.timedelta(hours=12),
		CacheTypes.RECORDS: dt.timedelta(hours=12),
		CacheTypes.RECORD_CONTENTS: dt.timedelta(hours=72),
		CacheTypes.SEARCH_RESULTS: dt.timedelta(hours=12),
		CacheTypes.FULL_RECORD_CONTENTS: dt.timedelta(hours=730),
	}
	__CACHE_PURGE_COOLDOWN: ClassVar[dict[CacheTypes, dt.timedelta]] = {
		CacheTypes.NEWS_ITEMS: dt.timedelta(hours=1),
		CacheTypes.IMAGES: dt.timedelta(hours=1),
		CacheTypes.IMAGE_CONTENTS: dt.timedelta(hours=3),
		CacheTypes.IMAGE_DESCRIPTIONS: dt.timedelta(hours=3),
		CacheTypes.CHAPTERS: dt.timedelta(hours=1),
		CacheTypes.RECORDS: dt.timedelta(hours=1),
		CacheTypes.RECORD_CONTENTS: dt.timedelta(hours=3),
		CacheTypes.SEARCH_RESULTS: dt.timedelta(hours=1),
		CacheTypes.FULL_RECORD_CONTENTS: dt.timedelta(hours=24),
	}
	__REQUEST_TIMEOUT: float = 10.0
	__DEFAULT_HEADERS: ClassVar[dict[str, str]] = {
		"User-Agent": getenv("FRACTALTHORNS_USER_AGENT")
	}
	__CACHE_PATH: str = "__apicache__/cache_"
	__CACHE_EXT: str = ".json"
	__CACHE_BAK: str = ".bak"

	def _make_request(
		self,
		endpoint: str,
		request_payload: dict[str, str] | None,
		*,
		strictly_match_request_arguments: bool = True,
		headers: dict[str, str] | None = None,
	) -> requests.Request:
		"""Make a request at one of the predefined endpoints.

		Arguments:
		---------
		endpoint -- Name of the endpoint
		request_payload -- Arguments that will be passed as JSON to ?body={}

		Keyword Arguments:
		-----------------
		strictly_match_request_arguments -- If True, raises a ParameterError if
		request_payload contains undefined arguments (default True)
		headers -- Headers to pass to requests.get() (default {})

		Raises:
		------
		fractalthorns_exceptions.ParameterError (from Request.make_request) -- A required request argument is missing
		fractalthorns_exceptions.ParameterError (from Request.__check_arguments) -- Unexpected request argument
		requests.ConnectionError (from Request.make_request) -- A connection error occurred
		requests.TooManyRedirects (from Request.make_request) -- Too many redirects
		requests.Timeout (from Request.make_request) -- The request timed out
		"""
		if headers is None:
			headers = self.__DEFAULT_HEADERS

		return super()._make_request(
			endpoint,
			request_payload,
			strictly_match_request_arguments=strictly_match_request_arguments,
			headers=headers,
		)

	def purge_cache(self, cache: CacheTypes, *, force_purge: bool = False) -> None:
		"""Purges stored cache items unless it's too soon since last purge.

		Arguments:
		---------
		caches -- Which caches to purge

		Keyword Arguments:
		-----------------
		force_purge -- Forces a cache purge regardless of time

		Raises:
		------
		fractalthorns_exceptions.CachePurgeError -- Cannot purge the cache.
		Contains:
			str -- Reason
			datetime.datetime (Optional) -- When a purge will be allowed.
		"""
		if (
			not force_purge
			and self.__last_cache_purge.get(cache) is not None
			and dt.datetime.now(dt.UTC)
			< self.__last_cache_purge[cache] + self.__CACHE_PURGE_COOLDOWN[cache]
		):
			raise fte.CachePurgeError(
				self.InvalidPurgeReasons.CACHE_PURGE.value,
				self.__last_cache_purge[cache] + self.__CACHE_PURGE_COOLDOWN[cache],
			)

		match cache:
			case self.CacheTypes.NEWS_ITEMS:
				self.__cached_news_items = None
			case self.CacheTypes.IMAGES:
				self.__cached_images = {}
				self.__last_all_images_cache = None
			case self.CacheTypes.IMAGE_CONTENTS:
				self.__cached_image_contents = {}
			case self.CacheTypes.IMAGE_DESCRIPTIONS:
				self.__cached_image_descriptions = {}
			case self.CacheTypes.CHAPTERS:
				self.__cached_chapters = None
				self.__last_full_episodic_cache = None
			case self.CacheTypes.RECORDS:
				self.__cached_records = {}
			case self.CacheTypes.RECORD_CONTENTS:
				self.__cached_record_contents = {}
			case self.CacheTypes.SEARCH_RESULTS:
				self.__cached_search_results = {}
			case self.CacheTypes.FULL_RECORD_CONTENTS:
				self.__full_record_contents = None
			case _:
				msg = f"{self.InvalidPurgeReasons.INVALID_CACHE.value}: {cache}"
				raise fte.CachePurgeError(msg)

		self.__last_cache_purge.update({cache: dt.datetime.now(dt.UTC)})

	def get_all_news(self) -> list[ftd.NewsEntry]:
		"""Get news items from fractalthorns.

		Raises
		------
		requests.ConnectionError (from __get_all_news) -- A connection error occurred
		requests.TooManyRedirects (from __get_all_news) -- Too many redirects
		requests.Timeout (from __get_all_news) -- The request timed out
		requests.HTTPError (from __get_all_news) -- An HTTP error ocurred
		"""
		return self.__get_all_news()

	def get_single_image(
		self, name: str | None
	) -> tuple[str, tuple[Image.Image, Image.Image]]:
		"""Get an image from fractalthorns.

		Arguments:
		---------
		name -- Identifying name of the image.

		Raises:
		------
		requests.ConnectionError (from __get_single_image and __get_image_contents) -- A connection error occurred
		requests.TooManyRedirects (from __get_single_image and __get_image_contents) -- Too many redirects
		requests.Timeout (from __get_single_image and __get_image_contents) -- The request timed out
		requests.HTTPError (from __get_single_image and __get_image_contents) -- An HTTP error ocurred
		"""
		image_info = self.__get_single_image(name)
		image_contents = self.__get_image_contents(name)
		return (image_info, image_contents)

	def get_image_description(self, name: str) -> ftd.ImageDescription:
		"""Get image description from fractalthorns.

		Arguments:
		---------
		name -- Identifying name of the image.

		Raises:
		------
		requests.ConnectionError (from __get_image_description) -- A connection error occurred
		requests.TooManyRedirects (from __get_image_description) -- Too many redirects
		requests.Timeout (from __get_image_description) -- The request timed out
		requests.HTTPError (from __get_image_description) -- An HTTP error ocurred
		"""
		return self.__get_image_description(name)

	def get_all_images(self) -> list[ftd.Image]:
		"""Get all images from fractalthorns.

		Raises
		------
		requests.ConnectionError (from __get_all_images) -- A connection error occurred
		requests.TooManyRedirects (from __get_all_images) -- Too many redirects
		requests.Timeout (from __get_all_images) -- The request timed out
		requests.HTTPError (from __get_all_images) -- An HTTP error ocurred
		"""
		return self.__get_all_images()

	def get_full_episodic(self) -> list[ftd.Chapter]:
		"""Get the full episodic from fractalthorns.

		Raises
		------
		requests.ConnectionError (from __get_full_episodic) -- A connection error occurred
		requests.TooManyRedirects (from __get_full_episodic) -- Too many redirects
		requests.Timeout (from __get_full_episodic) -- The request timed out
		requests.HTTPError (from __get_full_episodic) -- An HTTP error ocurred
		"""
		return self.__get_full_episodic()

	def get_single_record(self, name: str) -> ftd.Record:
		"""Get a record from fractalthorns.

		Arguments:
		---------
		name -- Identifying name of the record.

		Raises:
		------
		requests.ConnectionError (from __get_single_record) -- A connection error occurred
		requests.TooManyRedirects (from __get_single_record) -- Too many redirects
		requests.Timeout (from __get_single_record) -- The request timed out
		requests.HTTPError (from __get_single_record) -- An HTTP error ocurred
		"""
		return self.__get_single_record(name)

	def get_record_text(self, name: str) -> ftd.RecordText:
		"""Get the contents of a record from fractalthorns.

		Arguments:
		---------
		name -- Identifying name of the record.

		Raises:
		------
		requests.ConnectionError (from __get_record_text) -- A connection error occurred
		requests.TooManyRedirects (from __get_record_text) -- Too many redirects
		requests.Timeout (from __get_record_text) -- The request timed out
		requests.HTTPError (from __get_record_text) -- An HTTP error ocurred
		"""
		return self.__get_record_text(name)

	def get_domain_search(self, term: str, type_: str) -> list[ftd.SearchResult]:
		"""Get domain search results from fractalthorns.

		Arguments:
		---------
		term -- The term to search for.
		type_ -- Type of search (valid: "image", "episodic-item", "episodic-line").

		Raises:
		------
		fractalthorns_exceptions.InvalidSearchType (from __get_domain_search) -- Not a valid search type
		requests.ConnectionError (from __get_domain_search) -- A connection error occurred
		requests.TooManyRedirects (from __get_domain_search) -- Too many redirects
		requests.Timeout (from __get_domain_search) -- The request timed out
		requests.HTTPError (from __get_domain_search) -- An HTTP error ocurred
		"""
		return self.__get_domain_search(term, type_)

	def __get_all_news(self) -> list[ftd.NewsEntry]:
		"""Get a list all news items.

		Raises
		------
		requests.ConnectionError (from _make_request) -- A connection error occurred
		requests.TooManyRedirects (from _make_request) -- Too many redirects
		requests.Timeout (from _make_request) -- The request timed out
		requests.HTTPError (from __raise_for_status) -- An HTTP error ocurred
		"""
		if (
			self.__cached_news_items is None
			or dt.datetime.now(dt.UTC)
			> self.__cached_news_items[1]
			+ self.__CACHE_DURATION[self.CacheTypes.NEWS_ITEMS]
		):
			r = self._make_request(self.ValidRequests.ALL_NEWS.value, None)
			self.__raise_for_status(r)

			news_items = [
				ftd.NewsEntry.from_obj(i) for i in json.loads(r.text)["items"]
			]

			self.__cached_news_items = (
				news_items,
				dt.datetime.now(dt.UTC),
			)
			self.__save_cache(self.CacheTypes.NEWS_ITEMS)

		return self.__cached_news_items[0]

	def __get_single_image(self, image: str | None) -> ftd.Image:
		"""Get a single image.

		Raises
		------
		requests.ConnectionError (from _make_request) -- A connection error occurred
		requests.TooManyRedirects (from _make_request) -- Too many redirects
		requests.Timeout (from _make_request) -- The request timed out
		requests.HTTPError (from __raise_for_status) -- An HTTP error ocurred
		"""
		if (
			image not in self.__cached_images
			or dt.datetime.now(dt.UTC)
			> self.__cached_images[image][1]
			+ self.__CACHE_DURATION[self.CacheTypes.IMAGES]
		):
			r = self._make_request(
				self.ValidRequests.SINGLE_IMAGE.value, {"name": image}
			)
			self.__raise_for_status(r)
			image_metadata = json.loads(r.text)
			image_metadata["image_url"] = (
				f"{self._base_url}{image_metadata["image_url"]}"
			)
			image_metadata["thumb_url"] = (
				f"{self._base_url}{image_metadata["thumb_url"]}"
			)

			self.__cached_images.update(
				{
					image: (
						ftd.Image.from_obj(image_metadata),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			self.__save_cache(self.CacheTypes.IMAGES)

		return self.__cached_images[image][0]

	def __get_image_contents(self, image: str) -> tuple[Image.Image, Image.Image]:
		"""Get the contents of an image.

		Raises
		------
		requests.ConnectionError (from requests.get) -- A connection error occurred
		requests.TooManyRedirects (from requests.get) -- Too many redirects
		requests.Timeout (from requests.get) -- The request timed out
		requests.HTTPError (from __raise_for_status) -- An HTTP error ocurred
		"""
		if (
			image not in self.__cached_image_contents
			or dt.datetime.now(dt.UTC)
			> self.__cached_image_contents[image][1]
			+ self.__CACHE_DURATION[self.CacheTypes.IMAGE_CONTENTS]
		):
			image_metadata = self.__get_single_image(image)

			image_req = requests.get(
				f"{image_metadata.image_url}",
				timeout=self.__REQUEST_TIMEOUT,
				headers=self.__DEFAULT_HEADERS,
			)
			self.__raise_for_status(image_req)
			image_contents = Image.open(BytesIO(image_req.content))

			thumb_req = requests.get(
				f"{image_metadata.thumb_url}",
				timeout=self.__REQUEST_TIMEOUT,
				headers=self.__DEFAULT_HEADERS,
			)
			self.__raise_for_status(thumb_req)
			image_thumbnail = Image.open(BytesIO(thumb_req.content))

			self.__cached_image_contents.update(
				{
					image: (
						(image_contents, image_thumbnail),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			self.__save_cache(self.CacheTypes.IMAGE_CONTENTS)

		return self.__cached_image_contents[image][0]

	def __get_image_description(self, image: str) -> ftd.ImageDescription:
		"""Get the description of an image.

		Raises
		------
		requests.ConnectionError (from _make_request) -- A connection error occurred
		requests.TooManyRedirects (from _make_request) -- Too many redirects
		requests.Timeout (from _make_request) -- The request timed out
		requests.HTTPError (from __raise_for_status) -- An HTTP error ocurred
		"""
		if (
			image not in self.__cached_image_descriptions
			or dt.datetime.now(dt.UTC)
			> self.__cached_image_descriptions[image][1]
			+ self.__CACHE_DURATION[self.CacheTypes.IMAGE_DESCRIPTIONS]
		):
			r = self._make_request(
				self.ValidRequests.IMAGE_DESCRIPTION.value, {"name": image}
			)
			self.__raise_for_status(r)

			image_description = json.loads(r.text)

			self.__cached_image_descriptions.update(
				{
					image: (
						ftd.ImageDescription(image_description.get("description")),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			self.__save_cache(self.CacheTypes.IMAGE_DESCRIPTIONS)

		return self.__cached_image_descriptions[image][0]

	def __get_all_images(self) -> list[ftd.Image]:
		"""Get all images.

		Raises
		------
		requests.ConnectionError (from _make_request) -- A connection error occurred
		requests.TooManyRedirects (from _make_request) -- Too many redirects
		requests.Timeout (from _make_request) -- The request timed out
		requests.HTTPError (from __raise_for_status) -- An HTTP error ocurred
		"""
		if (
			self.__last_all_images_cache is None
			or dt.datetime.now(dt.UTC)
			> self.__last_all_images_cache
			+ self.__CACHE_DURATION[self.CacheTypes.IMAGES]
		):
			r = self._make_request(self.ValidRequests.ALL_IMAGES.value, None)
			self.__raise_for_status(r)

			images = json.loads(r.text)["images"]
			cache_time = dt.datetime.now(dt.UTC)

			for image in images:
				image["image_url"] = f"{self._base_url}{image["image_url"]}"
				image["thumb_url"] = f"{self._base_url}{image["thumb_url"]}"
				self.__cached_images.update(
					{image["name"]: (ftd.Image.from_obj(image), cache_time)}
				)

			self.__last_all_images_cache = cache_time

			self.__save_cache(self.CacheTypes.IMAGES)
			self.__save_cache(self.CacheTypes.CACHE_METADATA)

		return [i[0] for i in self.__cached_images.values()]

	def __get_full_episodic(self) -> list[ftd.Chapter]:
		"""Get the full episodic.

		Raises
		------
		requests.ConnectionError (from _make_request) -- A connection error occurred
		requests.TooManyRedirects (from _make_request) -- Too many redirects
		requests.Timeout (from _make_request) -- The request timed out
		requests.HTTPError (from __raise_for_status) -- An HTTP error ocurred
		"""
		if (
			self.__last_full_episodic_cache is None
			or dt.datetime.now(dt.UTC)
			> self.__last_full_episodic_cache
			+ self.__CACHE_DURATION[self.CacheTypes.CHAPTERS]
		):
			r = self._make_request(self.ValidRequests.FULL_EPISODIC.value, None)
			self.__raise_for_status(r)

			chapters_list = json.loads(r.text)["chapters"]
			cache_time = dt.datetime.now(dt.UTC)

			chapters = {
				chapter["name"]: ftd.Chapter.from_obj(chapter)
				for chapter in chapters_list
			}

			self.__cached_chapters = (chapters, cache_time)

			for chapter in chapters.values():
				for record in chapter.records:
					if record.solved:
						self.__cached_records.update(
							{record.name: (record, cache_time)}
						)

			self.__last_full_episodic_cache = cache_time

			self.__save_cache(self.CacheTypes.CHAPTERS)
			self.__save_cache(self.CacheTypes.RECORDS)
			self.__save_cache(self.CacheTypes.CACHE_METADATA)

		return list(self.__cached_chapters[0].values())

	def __get_single_record(self, name: str) -> ftd.Record:
		"""Get a single record.

		Raises
		------
		requests.ConnectionError (from _make_request) -- A connection error occurred
		requests.TooManyRedirects (from _make_request) -- Too many redirects
		requests.Timeout (from _make_request) -- The request timed out
		requests.HTTPError (from __raise_for_status) -- An HTTP error ocurred
		"""
		if (
			name not in self.__cached_records
			or dt.datetime.now(dt.UTC)
			> self.__cached_records[name][1]
			+ self.__CACHE_DURATION[self.CacheTypes.RECORDS]
		):
			r = self._make_request(self.ValidRequests.SINGLE_RECORD, {"name": name})
			self.__raise_for_status(r)

			record = json.loads(r.text)
			self.__cached_records.update(
				{
					name: (
						ftd.Record.from_obj(record),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			self.__save_cache(self.CacheTypes.RECORDS)

		return self.__cached_records[name][0]

	def __get_record_text(self, name: str) -> ftd.RecordText:
		"""Get a record's contents.

		Raises
		------
		requests.ConnectionError (from _make_request and __get_single_record) -- A connection error occurred
		requests.TooManyRedirects (from _make_request and __get_single_record) -- Too many redirects
		requests.Timeout (from _make_request and __get_single_record) -- The request timed out
		requests.HTTPError (from __raise_for_status and __get_single_record) -- An HTTP error ocurred
		"""
		if (
			name not in self.__cached_record_contents
			or dt.datetime.now(dt.UTC)
			> self.__cached_record_contents[name][1]
			+ self.__CACHE_DURATION[self.CacheTypes.RECORD_CONTENTS]
		):
			r = self._make_request(self.ValidRequests.RECORD_TEXT.value, {"name": name})
			self.__raise_for_status(r)

			record_contents = json.loads(r.text)
			record_title = self.__get_single_record(name).title
			self.__cached_record_contents.update(
				{
					name: (
						ftd.RecordText.from_obj(record_title, record_contents),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			self.__save_cache(self.CacheTypes.RECORD_CONTENTS)

		return self.__cached_record_contents[name][0]

	def __get_domain_search(self, term: str, type_: str) -> list[ftd.SearchResult]:
		"""Get a domain search.

		Raises
		------
		fractalthorns_exceptions.InvalidSearchType -- Not a valid search type
		requests.ConnectionError (from _make_request) -- A connection error occurred
		requests.TooManyRedirects (from _make_request) -- Too many redirects
		requests.Timeout (from _make_request) -- The request timed out
		requests.HTTPError (from __raise_for_status) -- An HTTP error ocurred
		"""
		if type_ not in ["image", "episodic-item", "episodic-line"]:
			msg = "Invalid search type"
			raise fte.InvalidSearchTypeError(msg)

		if (term, type_) not in self.__cached_search_results or dt.datetime.now(
			dt.UTC
		) > self.__cached_search_results[(term, type_)][1] + self.__CACHE_DURATION[
			self.CacheTypes.SEARCH_RESULTS
		]:
			r = self._make_request(
				self.ValidRequests.DOMAIN_SEARCH.value, {"term": term, "type": type_}
			)
			self.__raise_for_status(r)

			search_results = json.loads(r.text)["results"]

			for i in search_results:
				if i.get("image") is not None:
					i["image"]["image_url"] = (
						f"{self._base_url}{i["image"]["image_url"]}"
					)
					i["image"]["thumb_url"] = (
						f"{self._base_url}{i["image"]["thumb_url"]}"
					)

			self.__cached_search_results.update(
				{
					(term, type_): (
						[ftd.SearchResult.from_obj(i) for i in search_results],
						dt.datetime.now(dt.UTC),
					)
				}
			)

			self.__save_cache(self.CacheTypes.SEARCH_RESULTS)

		return self.__cached_search_results[(term, type_)][0]

	def __load_cache(self, cache: CacheTypes) -> None:
		try:
			if cache == self.CacheTypes.IMAGE_CONTENTS:
				cache_path = "".join((self.__CACHE_PATH, cache.value.replace(" ", "_")))

				if not Path(cache_path).exists():
					return

				cache_meta = f"{cache_path}{self.__CACHE_EXT}"

				if not Path(cache_meta).exists():
					return

				with Path.open(cache_meta, "r", encoding="utf-8") as f:
					saved_images = json.load(f)

				for i in saved_images:
					timestamp = dt.datetime.fromtimestamp(saved_images[i], tz=dt.UTC)

					image_path = f"{cache_path}/image_{i}.png"
					thumb_path = f"{cache_path}/thumb_{i}.png"

					if not (Path(image_path).exists() and Path(thumb_path).exists()):
						continue

					image_bytes = Path(image_path).read_bytes()
					thumb_bytes = Path(thumb_path).read_bytes()
					image = Image.open(BytesIO(image_bytes))
					thumb = Image.open(BytesIO(thumb_bytes))

					name = i
					if name == "__None__":
						name = None

					self.__cached_image_contents.update(
						{
							name: (
								(image, thumb),
								timestamp,
							)
						}
					)

			else:
				cache_path = "".join(
					(self.__CACHE_PATH, cache.value.replace(" ", "_"), self.__CACHE_EXT)
				)

				if not Path(cache_path).exists():
					return

				with Path.open(cache_path, "r", encoding="utf-8") as f:
					cache_contents = json.load(f)

				match cache:
					case self.CacheTypes.NEWS_ITEMS:
						cache_contents = (
							[ftd.NewsEntry.from_obj(i) for i in cache_contents[0]],
							dt.datetime.fromtimestamp(cache_contents[1], tz=dt.UTC),
						)
						self.__cached_news_items = cache_contents
					case self.CacheTypes.IMAGES:
						cache_contents = {
							(i if i != "__None__" else None): (
								ftd.Image.from_obj(j[0]),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_images = cache_contents
					case self.CacheTypes.IMAGE_DESCRIPTIONS:
						cache_contents = {
							i: (
								ftd.ImageDescription(j[0]["description"]),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_image_descriptions = cache_contents
					case self.CacheTypes.CHAPTERS:
						cache_contents = (
							{
								i: ftd.Chapter.from_obj(j)
								for i, j in cache_contents[0].items()
							},
							dt.datetime.fromtimestamp(cache_contents[1], tz=dt.UTC),
						)
						self.__cached_chapters = cache_contents
					case self.CacheTypes.RECORDS:
						cache_contents = {
							i: (
								ftd.Record.from_obj(j[0]),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_records = cache_contents
					case self.CacheTypes.RECORD_CONTENTS:
						cache_contents = {
							i: (
								ftd.RecordText.from_obj(j[0]["title"], j[0]),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_record_contents = cache_contents
					case self.CacheTypes.SEARCH_RESULTS:
						cache_contents = {
							(i[: i.rindex("|")], i[i.rindex("|") + 1 :]): (
								[ftd.SearchResult.from_obj(k) for k in j[0]],
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_search_results = cache_contents
					case self.CacheTypes.FULL_RECORD_CONTENTS:
						cache_contents = (
							{
								i: ftd.RecordText.from_obj(j["title"], j)
								for i, j in cache_contents[0].items()
							},
							dt.datetime.fromtimestamp(cache_contents[1], tz=dt.UTC),
						)
						self.__cached_full_record_contents = cache_contents
					case self.CacheTypes.CACHE_METADATA:
						self.__last_all_images_cache = cache_contents.get(
							"__last_all_images_cache"
						)
						self.__last_full_episodic_cache = cache_contents.get(
							"__last_full_episodic_cache"
						)

						if self.__last_all_images_cache is not None:
							self.__last_all_images_cache = dt.datetime.fromtimestamp(
								self.__last_all_images_cache, tz=dt.UTC
							)
						if self.__last_full_episodic_cache is not None:
							self.__last_full_episodic_cache = dt.datetime.fromtimestamp(
								self.__last_full_episodic_cache, tz=dt.UTC
							)
						self.__last_cache_purge = {
							i: dt.datetime.fromtimestamp(j, tz=dt.UTC)
							for i, j in self.__last_cache_purge.items()
						}

		except (json.decoder.JSONDecodeError, ValueError):
			print(f"Error while loading cache for {cache.value}")
			print(traceback.format_exc())

	def __load_all_cache(self) -> None:
		for i in self.CacheTypes:
			self.__load_cache(i)

	def __save_cache(self, cache: CacheTypes) -> None:
		if cache == self.CacheTypes.IMAGE_CONTENTS:
			cache_path = "".join((self.__CACHE_PATH, cache.value.replace(" ", "_")))

			Path(cache_path).mkdir(parents=True, exist_ok=True)

			saved_images = {}

			for i, j in self.__cached_image_contents.items():
				name = i
				if name is None:
					name = "__None__"
				image, image_path = (j[0][0], f"{cache_path}/image_{name}.png")
				thumb, thumb_path = (j[0][1], f"{cache_path}/thumb_{name}.png")

				if Path(image_path).exists():
					Path(image_path).replace(f"{image_path}{self.__CACHE_BAK}")
				if Path(thumb_path).exists():
					Path(thumb_path).replace(f"{thumb_path}{self.__CACHE_BAK}")

				image.save(image_path)
				thumb.save(thumb_path)

				saved_images.update({name: j[1].timestamp()})

			cache_meta = f"{cache_path}{self.__CACHE_EXT}"

			if Path(cache_meta).exists():
				Path(cache_meta).replace(f"{cache_meta}{self.__CACHE_BAK}")

			with Path.open(cache_meta, "w", encoding="utf-8") as f:
				json.dump(saved_images, f, indent=4)

		else:
			cache_path = "".join(
				(self.__CACHE_PATH, cache.value.replace(" ", "_"), self.__CACHE_EXT)
			)

			Path(cache_path).parent.mkdir(parents=True, exist_ok=True)

			if Path(cache_path).exists():
				Path(cache_path).replace(f"{cache_path}{self.__CACHE_BAK}")

			match cache:
				case self.CacheTypes.NEWS_ITEMS:
					cache_contents = self.__cached_news_items
					cache_contents = (
						[asdict(i) for i in cache_contents[0]],
						cache_contents[1].timestamp(),
					)
				case self.CacheTypes.IMAGES:
					cache_contents = self.__cached_images
					cache_contents = {
						(i if i is not None else "__None__"): (
							asdict(j[0]),
							j[1].timestamp(),
						)
						for i, j in cache_contents.items()
					}
				case self.CacheTypes.IMAGE_DESCRIPTIONS:
					cache_contents = self.__cached_image_descriptions
					cache_contents = {
						i: (asdict(j[0]), j[1].timestamp())
						for i, j in cache_contents.items()
					}
				case self.CacheTypes.CHAPTERS:
					cache_contents = self.__cached_chapters
					cache_contents = (
						{i: asdict(j) for i, j in cache_contents[0].items()},
						cache_contents[1].timestamp(),
					)
				case self.CacheTypes.RECORDS:
					cache_contents = self.__cached_records
					cache_contents = {
						i: (asdict(j[0]), j[1].timestamp())
						for i, j in cache_contents.items()
					}
				case self.CacheTypes.RECORD_CONTENTS:
					cache_contents = self.__cached_record_contents
					cache_contents = {
						i: (asdict(j[0]), j[1].timestamp())
						for i, j in cache_contents.items()
					}
				case self.CacheTypes.SEARCH_RESULTS:
					cache_contents = self.__cached_search_results
					cache_contents = {
						f"{i[0]}|{i[1]}": ([asdict(k) for k in j[0]], j[1].timestamp())
						for i, j in cache_contents.items()
					}
				case self.CacheTypes.FULL_RECORD_CONTENTS:
					cache_contents = self.__cached_full_record_contents
					cache_contents = (
						{i: asdict(j) for i, j in cache_contents[0].items()},
						cache_contents[1].timestamp(),
					)
				case self.CacheTypes.CACHE_METADATA:
					cache_contents = {}
					if self.__last_all_images_cache is not None:
						cache_contents.update(
							{
								"__last_all_images_cache": self.__last_all_images_cache.timestamp()
							}
						)
					if self.__last_full_episodic_cache is not None:
						cache_contents.update(
							{
								"__last_full_episodic_cache": self.__last_full_episodic_cache.timestamp()
							}
						)
					cache_contents.update(
						{
							"__last_cache_purge": {
								i: j.timestamp()
								for i, j in self.__last_cache_purge.items()
							}
						}
					)

			with Path.open(cache_path, "w", encoding="utf-8") as f:
				json.dump(cache_contents, f, indent=4)

	@staticmethod
	def __raise_for_status(response: requests.Response) -> None:
		"""Raise a requests.HTTPError, with the URL stripped out, if one exists."""
		try:
			response.raise_for_status()
		except requests.HTTPError as e:
			matching = re.search(r" for url:.*", str(e))

			if matching is not None:
				raise requests.HTTPError(
					str(e).removesuffix(matching.group(0)), response=e.response
				) from None

			raise


fractalthorns_api = FractalthornsAPI()

# fmt: off
if __name__ == "__main__":
	print()
	print("# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)")
	print("# This script is licensed under the GNU Affero General Public License version 3 or later.")
	print("# For more information, view the LICENSE file provided with this project")
	print("# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html")
	print()
	print("# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).")
	print("# View it here: https://fractalthorns.com")
	print()
# fmt: on
