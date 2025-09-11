# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module for accessing the fractalthorns API."""

import asyncio
import datetime as dt
import json
import logging
import re
from copy import deepcopy
from dataclasses import asdict
from enum import Enum, StrEnum
from io import BytesIO
from os import getenv
from pathlib import Path
from typing import ClassVar, Literal

import aiofiles
import aiofiles.os
import aiohttp
from dotenv import load_dotenv
from PIL import Image

import src.fractalthorns_dataclasses as ftd
import src.fractalthorns_exceptions as fte
from src.api_access import API, Request, RequestArgument
from src.fractalrhomb_globals import FRACTALTHORNS_USER_AGENT

load_dotenv()


class FractalthornsAPI(API):
	"""A class for accessing the fractalthorns API."""

	class ValidRequests(StrEnum):
		"""An enum containing all valid API endpoints."""

		ALL_NEWS = "all_news"
		SINGLE_IMAGE = "single_image"
		IMAGE_DESCRIPTION = "image_description"
		ALL_IMAGES = "all_images"
		SINGLE_SKETCH = "single_sketch"
		ALL_SKETCHES = "all_sketches"
		FULL_EPISODIC = "full_episodic"
		SINGLE_RECORD = "single_record"
		RECORD_TEXT = "record_text"
		DOMAIN_SEARCH = "domain_search"
		CURRENT_SPLASH = "current_splash"
		PAGED_SPLASHES = "paged_splashes"
		SUBMIT_DISCORD_SPLASH = "submit_discord_splash"

	class InvalidPurgeReasons(StrEnum):
		"""An enum containing reasons for not allowing a purge."""

		CACHE_PURGE = "Too soon since last cache purge"
		INVALID_CACHE = "Not a valid cache type"

	class CacheTypes(Enum):
		"""An enum containing cache types."""

		NEWS_ITEMS = "news"
		IMAGES = "images"
		IMAGE_CONTENTS = "image contents"
		IMAGE_DESCRIPTIONS = "image descriptions"
		SKETCHES = "sketches"
		SKETCH_CONTENTS = "sketch contents"
		CHAPTERS = "chapters"
		RECORDS = "records"
		RECORD_CONTENTS = "record contents"
		SEARCH_RESULTS = "search results"
		CURRENT_SPLASH = "current splash"
		SPLASH_PAGES = "splash pages"
		FULL_RECORD_CONTENTS = "full record contents"
		FULL_IMAGE_DESCRIPTIONS = "full image descriptions"
		CACHE_METADATA = "cache metadata"

	def __init__(self) -> None:
		"""Initialize the API handler."""
		self.logger = logging.getLogger("fractalthorns_api")

		all_news = Request(self.ValidRequests.ALL_NEWS.value, None, "GET")

		single_image = Request(
			self.ValidRequests.SINGLE_IMAGE.value,
			[RequestArgument("name", optional=True)],
			"GET",
		)

		image_description = Request(
			self.ValidRequests.IMAGE_DESCRIPTION.value,
			[RequestArgument("name", optional=False)],
			"GET",
		)

		all_images = Request(self.ValidRequests.ALL_IMAGES.value, None, "GET")

		single_sketch = Request(
			self.ValidRequests.SINGLE_SKETCH.value,
			[RequestArgument("name", optional=True)],
			"GET",
		)

		all_sketches = Request(self.ValidRequests.ALL_SKETCHES.value, None, "GET")

		full_episodic = Request(self.ValidRequests.FULL_EPISODIC.value, None, "GET")

		single_record = Request(
			self.ValidRequests.SINGLE_RECORD.value,
			[RequestArgument("name", optional=True)],
			"GET",
		)

		record_text = Request(
			self.ValidRequests.RECORD_TEXT.value,
			[RequestArgument("name", optional=True)],
			"GET",
		)

		domain_search = Request(
			self.ValidRequests.DOMAIN_SEARCH.value,
			[
				RequestArgument("term", optional=False),
				RequestArgument("type", optional=False),
			],
			"GET",
		)

		current_splash = Request(self.ValidRequests.CURRENT_SPLASH.value, None, "GET")

		paged_splashes = Request(
			self.ValidRequests.PAGED_SPLASHES.value,
			[RequestArgument("page", optional=False)],
			"GET",
		)

		submit_discord_splash = Request(
			self.ValidRequests.SUBMIT_DISCORD_SPLASH.value,
			[
				RequestArgument("text", optional=False),
				RequestArgument("submitter_display_name", optional=False),
				RequestArgument("submitter_user_id", optional=False),
			],
			"POST",
		)

		requests_list = {
			self.ValidRequests.ALL_NEWS.value: all_news,
			self.ValidRequests.SINGLE_IMAGE.value: single_image,
			self.ValidRequests.IMAGE_DESCRIPTION.value: image_description,
			self.ValidRequests.ALL_IMAGES.value: all_images,
			self.ValidRequests.SINGLE_SKETCH.value: single_sketch,
			self.ValidRequests.ALL_SKETCHES.value: all_sketches,
			self.ValidRequests.FULL_EPISODIC.value: full_episodic,
			self.ValidRequests.SINGLE_RECORD.value: single_record,
			self.ValidRequests.RECORD_TEXT.value: record_text,
			self.ValidRequests.DOMAIN_SEARCH.value: domain_search,
			self.ValidRequests.CURRENT_SPLASH.value: current_splash,
			self.ValidRequests.PAGED_SPLASHES.value: paged_splashes,
			self.ValidRequests.SUBMIT_DISCORD_SPLASH.value: submit_discord_splash,
		}

		# For testing purposes
		# super().__init__("https://test.fractalthorns.com", "/api/v1/", requests_list)
		super().__init__("https://fractalthorns.com", "/api/v1/", requests_list)
		self.__BASE_IMAGE_URL = f"{self._base_url}/image/"
		self.__BASE_SKETCH_URL = f"{self._base_url}/sketch/"
		self.__BASE_RECORD_URL = f"{self._base_url}/episodic/"
		self.__BASE_DISCOVERY_URL = f"{self._base_url}/discover/"

		self.__cached_news_items: tuple[list[ftd.NewsEntry], dt.datetime] | None = None
		self.__cached_images: dict[str, tuple[ftd.Image, dt.datetime]] = {}
		self.__cached_image_contents: dict[
			str, tuple[tuple[Image.Image, Image.Image], dt.datetime]
		] = {}
		self.__cached_image_descriptions: dict[
			str, tuple[ftd.ImageDescription, dt.datetime]
		] = {}
		self.__cached_sketches: dict[str, tuple[ftd.Sketch, dt.datetime]] = {}
		self.__cached_sketch_contents: dict[
			str, tuple[tuple[Image.Image, Image.Image], dt.datetime]
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
			tuple[str, Literal["image", "sketch", "episodic-item", "episodic-line"]],
			tuple[list[ftd.SearchResult], dt.datetime],
		] = {}
		self.__cached_current_splash: tuple[ftd.Splash, dt.datetime] | None = None
		self.__cached_splash_pages: dict[int, tuple[ftd.SplashPage, dt.datetime]] = {}
		self.__cached_full_record_contents: (
			tuple[dict[str, ftd.RecordText], dt.datetime] | None
		) = None
		self.__cached_full_image_descriptions: (
			tuple[dict[str, ftd.ImageDescription], dt.datetime] | None
		) = None
		self.__last_all_images_cache: dt.datetime | None = None
		self.__last_all_sketches_cache: dt.datetime | None = None
		self.__last_full_episodic_cache: dt.datetime | None = None
		self.__last_cache_purge: dict[FractalthornsAPI.CacheTypes, dt.datetime] = {}

		try:
			loop = asyncio.get_running_loop()
			background_tasks = set()
			task = loop.create_task(self.load_all_caches())
			background_tasks.add(task)
			task.add_done_callback(background_tasks.discard)
		except RuntimeError:
			asyncio.run(self.load_all_caches())

		self.__cache_saved: dict[FractalthornsAPI.CacheTypes, bool] = dict.fromkeys(
			self.CacheTypes, True
		)

	__CACHE_DURATION: ClassVar[dict[CacheTypes, dt.timedelta]] = {
		CacheTypes.NEWS_ITEMS: dt.timedelta(hours=4),
		CacheTypes.IMAGES: dt.timedelta(hours=4),
		CacheTypes.IMAGE_CONTENTS: dt.timedelta(hours=24),
		CacheTypes.IMAGE_DESCRIPTIONS: dt.timedelta(hours=12),
		CacheTypes.SKETCHES: dt.timedelta(hours=4),
		CacheTypes.SKETCH_CONTENTS: dt.timedelta(hours=24),
		CacheTypes.CHAPTERS: dt.timedelta(hours=4),
		CacheTypes.RECORDS: dt.timedelta(hours=4),
		CacheTypes.RECORD_CONTENTS: dt.timedelta(hours=12),
		CacheTypes.SEARCH_RESULTS: dt.timedelta(hours=4),
		CacheTypes.CURRENT_SPLASH: dt.timedelta(minutes=5),
		CacheTypes.SPLASH_PAGES: dt.timedelta(minutes=5),
		CacheTypes.FULL_RECORD_CONTENTS: dt.timedelta(hours=24),
		CacheTypes.FULL_IMAGE_DESCRIPTIONS: dt.timedelta(hours=24),
	}
	__CACHE_PURGE_COOLDOWN: ClassVar[dict[CacheTypes, dt.timedelta]] = {
		CacheTypes.NEWS_ITEMS: dt.timedelta(minutes=20),
		CacheTypes.IMAGES: dt.timedelta(minutes=20),
		CacheTypes.IMAGE_CONTENTS: dt.timedelta(minutes=120),
		CacheTypes.IMAGE_DESCRIPTIONS: dt.timedelta(minutes=60),
		CacheTypes.SKETCHES: dt.timedelta(minutes=20),
		CacheTypes.SKETCH_CONTENTS: dt.timedelta(minutes=120),
		CacheTypes.CHAPTERS: dt.timedelta(minutes=20),
		CacheTypes.RECORDS: dt.timedelta(minutes=20),
		CacheTypes.RECORD_CONTENTS: dt.timedelta(minutes=60),
		CacheTypes.SEARCH_RESULTS: dt.timedelta(minutes=20),
		CacheTypes.CURRENT_SPLASH: dt.timedelta(minutes=5),
		CacheTypes.SPLASH_PAGES: dt.timedelta(minutes=5),
		CacheTypes.FULL_RECORD_CONTENTS: dt.timedelta(minutes=120),
		CacheTypes.FULL_IMAGE_DESCRIPTIONS: dt.timedelta(minutes=120),
	}

	__SPLASH_API_KEY_HEADER = "X-Fractalthorns-Api-Key"
	__SPLASH_API_KEY = getenv("SPLASH_API_KEY")

	__REQUEST_TIMEOUT: float = 10.0
	__DEFAULT_HEADERS: ClassVar[dict[str, str]] = {
		"User-Agent": FRACTALTHORNS_USER_AGENT
	}
	__CACHE_PATH: str = ".apicache/cache_"
	__CACHE_EXT: str = ".json"
	__CACHE_BAK: str = ".bak"
	__STALE_CACHE_MESSAGE = "cache is missing or stale."
	__RENEWED_CACHE_MESSAGE = "renewed cache."
	__ALREADY_CACHED_MESSAGE = "already cached."
	__NO_PARAMETER_CACHE_MESSAGE = "(%s) %s"
	__ONE_PARAMETER_CACHE_MESSAGE = "(%s - %s) %s"
	__TWO_PARAMETER_CACHE_MESSAGE = "(%s - %s, %s) %s"

	async def _make_request(
		self,
		session: aiohttp.ClientSession,
		endpoint: str,
		request_payload: dict[str, str] | None,
		*,
		strictly_match_request_arguments: bool = True,
		headers: dict[str, str] | None = None,
		use_default_headers: bool = True,
	) -> aiohttp.client._RequestContextManager:
		"""Make a request at one of the predefined endpoints.

		Arguments:
		---------
		endpoint -- Name of the endpoint
		request_payload -- Arguments that will be passed as JSON to ?body={}

		Keyword Arguments:
		-----------------
		strictly_match_request_arguments -- If True, raises a ParameterError if
		request_payload contains undefined arguments (default True)
		headers -- Headers to pass to aiohttp.ClientSession.get() (default {})

		Raises:
		------
		fractalthorns_exceptions.ParameterError (from Request._make_request) -- A required request argument is missing
		fractalthorns_exceptions.ParameterError (from Request.__check_arguments) -- Unexpected request argument
		aiohttp.client_exceptions.ClientError (from Request._make_request) -- A client error occurred
		"""
		request_headers = {}
		if use_default_headers:
			request_headers = self.__DEFAULT_HEADERS

		if headers is not None:
			request_headers.update(headers)

		return await super()._make_request(
			session,
			endpoint,
			request_payload,
			strictly_match_request_arguments=strictly_match_request_arguments,
			headers=request_headers,
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
		"""
		self.logger.info("Purge for %s requested.", cache.value)

		if (
			not force_purge
			and self.__last_cache_purge.get(cache) is not None
			and dt.datetime.now(dt.UTC)
			< self.__last_cache_purge[cache] + self.__CACHE_PURGE_COOLDOWN[cache]
		):
			self.logger.warning(
				"Purge failed: %s", self.InvalidPurgeReasons.CACHE_PURGE.value
			)

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
			case self.CacheTypes.SKETCHES:
				self.__cached_images = {}
				self.__last_all_sketches_cache = None
			case self.CacheTypes.SKETCH_CONTENTS:
				self.__cached_image_contents = {}
			case self.CacheTypes.CHAPTERS:
				self.__cached_chapters = None
				self.__last_full_episodic_cache = None
			case self.CacheTypes.RECORDS:
				self.__cached_records = {}
			case self.CacheTypes.RECORD_CONTENTS:
				self.__cached_record_contents = {}
			case self.CacheTypes.SEARCH_RESULTS:
				self.__cached_search_results = {}
			case self.CacheTypes.CURRENT_SPLASH:
				self.__cached_current_splash = None
			case self.CacheTypes.SPLASH_PAGES:
				self.__cached_splash_pages = {}
			case self.CacheTypes.FULL_RECORD_CONTENTS:
				self.__cached_full_record_contents = None
			case self.CacheTypes.FULL_IMAGE_DESCRIPTIONS:
				self.__cached_full_image_descriptions = None
			case _:
				self.logger.warning(
					"Purge failed: %s", self.InvalidPurgeReasons.INVALID_CACHE.value
				)

				msg = f"{self.InvalidPurgeReasons.INVALID_CACHE.value}: {cache.value}"
				raise fte.CachePurgeError(msg)

		self.__last_cache_purge.update({cache: dt.datetime.now(dt.UTC)})

		self.logger.info("Successfully purged %s.", cache.value)

	def get_cached_items(
		self, cache: CacheTypes, *, ignore_stale: bool = False
	) -> (
		tuple[list[ftd.NewsEntry], dt.datetime, dt.datetime]
		| dict[str, tuple[ftd.Image, dt.datetime, dt.datetime]]
		| dict[str, tuple[tuple[Image.Image, Image.Image], dt.datetime, dt.datetime]]
		| dict[str, tuple[ftd.ImageDescription, dt.datetime, dt.datetime]]
		| dict[str, tuple[ftd.Sketch, dt.datetime, dt.datetime]]
		| tuple[dict[str, ftd.Chapter], dt.datetime, dt.datetime]
		| dict[str, tuple[ftd.Record, dt.datetime, dt.datetime]]
		| dict[str, tuple[ftd.RecordText, dt.datetime, dt.datetime]]
		| dict[
			tuple[str, Literal["image", "sketch", "episodic-item", "episodic-line"]],
			tuple[list[ftd.SearchResult], dt.datetime, dt.datetime],
		]
		| tuple[ftd.Splash, dt.datetime, dt.datetime]
		| dict[int, tuple[ftd.SplashPage, dt.datetime, dt.datetime]]
		| tuple[dict[str, ftd.RecordText], dt.datetime, dt.datetime]
		| tuple[dict[str, ftd.ImageDescription], dt.datetime, dt.datetime]
		| dict[
			str,
			tuple[dt.datetime, dt.datetime]
			| dict[CacheTypes, tuple[dt.datetime, dt.datetime] | None],
		]
		| None
	):
		"""Get items currently stored in the cache without making requests.

		Arguments:
		---------
		cache -- Which cache to fetch

		Keyword Arguments:
		-----------------
		ignore_stale -- If True, stale cache entries are still returned.

		Returns:
		-------
		NEWS_ENTRY -- ([News Entries], Cache Time, Expiry Time) | None
		IMAGES -- {Name: (Image, Cache Time, Expiry Time)}
		IMAGE_CONTENTS -- {Name: ((Main Image, Thumbnail), Cache Time, Expiry Time)}
		IMAGE_DESCRIPTION -- {Name: (Description, Cache Time, Expiry Time)}
		SKETCHES -- {Name: (Sketch, Cache Time, Expiry Time)} | None
		SKETCH_CONTENTS -- {Name: ((Main Image, Thumbnail), Cache Time, Expiry Time)}
		CHAPTERS -- ({Name: Chapter}, Cache Time, Expiry Time) | None
		RECORDS -- {Name: (Record, Cache Time, Expiry Time)}
		RECORD_CONTENTS -- {Name: (Record Text, Cache Time, Expiry Time)}
		SEARCH_RESULTS -- {(Search Term, Search Type): (Record, Cache Time, Expiry Time)}
		CURRENT_SPLASH -- (Splash, Cache Time, Expiry Time) | None
		PAGED_SPLASHES -- {Page: (Splash Page, Cache Time, Expiry Time)}
		FULL_RECORD_CONTENTS -- ({Name: Record Texts}, Cache Time, Expiry Time) | None
		FULL_IMAGE_DESCRIPTIONS -- ({Name: Description}, Cache Time, Expiry Time) | None
		CACHE_METADATA -- {
			"last_all_images_cache": (Cache Time, Expiry Time) | None
			"last_full_episodic_cache": (Cache Time, Expiry Time) | None
			"last_cache_purge": {Type: (Purge Time, Cooldown Time)}
		}

		Types that return a tuple can return None if nothing is cached or the cache has expired.
		This includes the subtypes in CACHE_METADATA.

		Raises:
		------
		fractalthorns_exceptions.CacheFetchError -- Cannot fetch the cache.
		"""
		now = dt.datetime.now(dt.UTC)

		cached_items = None

		match cache:
			case self.CacheTypes.NEWS_ITEMS:
				cached_items = deepcopy(self.__cached_news_items)

			case self.CacheTypes.IMAGES:
				cached_items = deepcopy(self.__cached_images)

			case self.CacheTypes.IMAGE_CONTENTS:
				cached_items = deepcopy(self.__cached_image_contents)

			case self.CacheTypes.IMAGE_DESCRIPTIONS:
				cached_items = deepcopy(self.__cached_image_descriptions)

			case self.CacheTypes.SKETCHES:
				cached_items = deepcopy(self.__cached_sketches)

			case self.CacheTypes.SKETCH_CONTENTS:
				cached_items = deepcopy(self.__cached_sketch_contents)

			case self.CacheTypes.CHAPTERS:
				cached_items = deepcopy(self.__cached_chapters)

			case self.CacheTypes.RECORDS:
				cached_items = deepcopy(self.__cached_records)

			case self.CacheTypes.RECORD_CONTENTS:
				cached_items = deepcopy(self.__cached_record_contents)

			case self.CacheTypes.SEARCH_RESULTS:
				cached_items = deepcopy(self.__cached_search_results)

			case self.CacheTypes.CURRENT_SPLASH:
				cached_items = deepcopy(self.__cached_current_splash)

			case self.CacheTypes.SPLASH_PAGES:
				cached_items = deepcopy(self.__cached_splash_pages)

			case self.CacheTypes.FULL_RECORD_CONTENTS:
				cached_items = deepcopy(self.__cached_full_record_contents)

			case self.CacheTypes.FULL_IMAGE_DESCRIPTIONS:
				cached_items = deepcopy(self.__cached_full_image_descriptions)

			case self.CacheTypes.CACHE_METADATA:
				last_full_images_cache = deepcopy(self.__last_all_images_cache)
				last_full_sketches_cache = deepcopy(self.__last_all_sketches_cache)
				last_full_episodic_cache = deepcopy(self.__last_full_episodic_cache)
				last_cache_purge = deepcopy(self.__last_cache_purge)
				cached_items = {
					"last_all_images_cache": (
						last_full_images_cache,
						last_full_images_cache
						+ self.__CACHE_DURATION[self.CacheTypes.IMAGES],
					),
					"last_all_sketches_cache": (
						last_full_sketches_cache,
						last_full_sketches_cache
						+ self.__CACHE_DURATION[self.CacheTypes.SKETCHES],
					),
					"last_full_episodic_cache": (
						last_full_episodic_cache,
						last_full_episodic_cache
						+ self.__CACHE_DURATION[self.CacheTypes.CHAPTERS],
					),
					"last_cache_purge": {
						i: (j, j + self.__CACHE_PURGE_COOLDOWN[i])
						for i, j in last_cache_purge.items()
					},
				}

			case _:
				msg = f"Cannot fetch this cache: {cache}"
				raise fte.CacheFetchError(msg)

		if cached_items is None:
			return None

		if cache in {
			self.CacheTypes.NEWS_ITEMS,
			self.CacheTypes.CHAPTERS,
			self.CacheTypes.CURRENT_SPLASH,
			self.CacheTypes.FULL_RECORD_CONTENTS,
			self.CacheTypes.FULL_IMAGE_DESCRIPTIONS,
		}:
			if (
				not ignore_stale
				and now > cached_items[1] + self.__CACHE_DURATION[cache]
			):
				return None

			cached_items += (cached_items[1] + self.__CACHE_DURATION[cache],)

		elif cache in {
			self.CacheTypes.IMAGES,
			self.CacheTypes.IMAGE_CONTENTS,
			self.CacheTypes.IMAGE_DESCRIPTIONS,
			self.CacheTypes.SKETCHES,
			self.CacheTypes.SKETCH_CONTENTS,
			self.CacheTypes.RECORDS,
			self.CacheTypes.RECORD_CONTENTS,
			self.CacheTypes.SEARCH_RESULTS,
			self.CacheTypes.SPLASH_PAGES,
		}:
			for i, j in cached_items.items():
				if not ignore_stale and now > j[1] + self.__CACHE_DURATION[cache]:
					cached_items.pop(i)
				else:
					cached_items[i] = (*j, j[1] + self.__CACHE_DURATION[cache])

		return cached_items

	async def get_all_news(self, session: aiohttp.ClientSession) -> list[ftd.NewsEntry]:
		"""Get news items from fractalthorns.

		Arguments:
		---------
		session -- The session to use.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_all_news) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_all_news) -- A client error occurred
		"""
		return await self.__get_all_news(session)

	async def get_single_image(
		self, session: aiohttp.ClientSession, name: str | None
	) -> tuple[ftd.Image, tuple[Image.Image, Image.Image]]:
		"""Get an image from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		name -- Identifying name of the image.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_single_image and __get_image_contents) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_single_image and __get_image_contents) -- A client error occurred
		"""
		image_info = await self.__get_single_image(session, name)
		image_contents = await self.__get_image_contents(session, name)

		return (image_info, image_contents)

	async def get_image_description(
		self, session: aiohttp.ClientSession, name: str
	) -> ftd.ImageDescription:
		"""Get image description from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		name -- Identifying name of the image.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_image_description) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_image_description) -- A client error occurred
		"""
		return await self.__get_image_description(session, name)

	async def get_all_images(self, session: aiohttp.ClientSession) -> list[ftd.Image]:
		"""Get all images from fractalthorns.

		Arguments:
		---------
		session -- The session to use.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_all_images) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_all_images) -- A client error occurred
		"""
		return await self.__get_all_images(session)

	async def get_single_sketch(
		self, session: aiohttp.ClientSession, name: str | None = None
	) -> tuple[ftd.Sketch, tuple[Image.Image, Image.Image]]:
		"""Get all sketches from fractalthorns.

		Arguments:
		---------
		session -- The session to use.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_all_sketches and __get_sketch_contents) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_all_sketches and __get_sketch_contents) -- A client error occurred
		"""
		sketch = await self.__get_single_sketch(session, name)
		images = await self.__get_sketch_contents(session, name)

		return (sketch, images)

	async def get_all_sketches(
		self, session: aiohttp.ClientSession
	) -> list[ftd.Sketch]:
		"""Get all sketches from fractalthorns.

		Arguments:
		---------
		session -- The session to use.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_all_sketches) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_all_sketches) -- A client error occurred
		"""
		sketches = await self.__get_all_sketches(session)
		return list(sketches.values())

	async def get_full_episodic(
		self, session: aiohttp.ClientSession
	) -> list[ftd.Chapter]:
		"""Get the full episodic from fractalthorns.

		Arguments:
		---------
		session -- The session to use.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_full_episodic) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_full_episodic) -- A client error occurred
		"""
		return await self.__get_full_episodic(session)

	async def get_single_record(
		self, session: aiohttp.ClientSession, name: str | None
	) -> ftd.Record:
		"""Get a record from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		name -- Identifying name of the record.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_single_record) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_single_record) -- A client error occurred
		"""
		return await self.__get_single_record(session, name)

	async def get_record_text(
		self, session: aiohttp.ClientSession, name: str | None
	) -> ftd.RecordText:
		"""Get the contents of a record from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		name -- Identifying name of the record.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_record_text) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_record_text) -- A client error occurred
		"""
		return await self.__get_record_text(session, name)

	async def get_domain_search(
		self,
		session: aiohttp.ClientSession,
		term: str,
		type_: Literal["image", "sketch", "episodic-item", "episodic-line"],
	) -> list[ftd.SearchResult]:
		"""Get domain search results from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		term -- The term to search for.
		type_ -- Type of search (valid: "image", "sketch", "episodic-item", "episodic-line").

		Raises:
		------
		fractalthorns_exceptions.InvalidSearchType (from __get_domain_search) -- Not a valid search type
		aiohttp.client_exceptions.ClientError (from __get_domain_search) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_domain_search) -- A client error occurred
		"""
		return await self.__get_domain_search(session, term, type_)

	async def get_current_splash(
		self,
		session: aiohttp.ClientSession,
	) -> ftd.Splash:
		"""Get current splash from fractalthorns.

		Arguments:
		---------
		session -- The session to use.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_domain_search) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_domain_search) -- A client error occurred
		"""
		return await self.__get_current_splash(session)

	async def get_paged_splashes(
		self, session: aiohttp.ClientSession, page: int
	) -> ftd.SplashPage:
		"""Get current splash from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		page -- The page of splashes to get.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_domain_search) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_domain_search) -- A client error occurred
		"""
		return await self.__get_paged_splashes(session, page)

	async def post_submit_discord_splash(
		self,
		session: aiohttp.ClientSession,
		text: str,
		submitter_display_name: str,
		submitter_user_id: str,
	) -> list[ftd.SplashPage]:
		"""Get current splash from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		text -- The splash text.
		submitter_display_name -- The submitter's current discord display name.
		submitter_user_id -- The submitter's user id.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_domain_search) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_domain_search) -- A client error occurred
		"""
		return await self.__post_submit_discord_splash(
			session, text, submitter_display_name, submitter_user_id
		)

	async def get_full_record_contents(
		self,
		session: aiohttp.ClientSession,
		*,
		gather: bool | None = None,
	) -> dict[str, ftd.RecordText]:
		"""Get the full record contents from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		gather -- if True, gather the records. Raises an exception if the last usage was too recent. If False, raises an exception if the record contents are uncached.

		Raises:
		------
		fractalthorns_exceptions.ItemsUngatheredError (from __get_full_record_contents) -- Gather was not True and items are uncached
		fractalthorns_exceptions.CachePurgeError (from __get_full_record_contents) -- Too soon since the last gather
		aiohttp.client_exceptions.ClientError (from get_full_record_contents) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from get_full_record_contents) -- A client error occurred
		"""
		return await self.__get_full_record_contents(session, gather=gather)

	async def get_full_image_descriptions(
		self,
		session: aiohttp.ClientSession,
		*,
		gather: bool | None = None,
	) -> dict[str, ftd.RecordText]:
		"""Get the full record contents from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		gather -- if True, gather the records. Raises an exception if the last usage was too recent. If False, raises an exception if the record contents are uncached.

		Raises:
		------
		fractalthorns_exceptions.ItemsUngatheredError (from __get_full_image_descriptions) -- Gather was not True and items are uncached
		fractalthorns_exceptions.CachePurgeError (from __get_full_image_descriptions) -- Too soon since the last gather
		aiohttp.client_exceptions.ClientError (from __get_full_image_descriptions) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_full_image_descriptions) -- A client error occurred
		"""
		return await self.__get_full_image_descriptions(session, gather=gather)

	async def search_images(
		self,
		session: aiohttp.ClientSession,
		name: str | None = None,
		description: str | None = None,
		canon: str | None = None,
		character: str | None = None,
		*,
		has_description: bool | None = None,
	) -> list[ftd.Image]:
		"""Search for images from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		name -- Returns images whose title contain this.
		description -- Returns images whose description contain this.
		canon -- Returns images whose canon match this.
		character -- Returns images whose characters match this.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_full_image_descriptions and __get_all_images) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_full_image_descriptions and __get_all_images) -- A client error occurred
		fractalthorns_exceptions.ItemsUngatheredError (from __get_full_image_descriptions) -- Items are uncached
		re.error (from re.search) -- Invalid regular expression
		"""
		if description is not None:
			image_descriptions = await self.__get_full_image_descriptions(session)
		images = await self.__get_all_images(session)

		if canon is not None:
			canon = canon.lower().split(" ")
			for i in range(len(canon)):
				match canon[i]:
					case "vollux":
						canon[i] = "209151"
					case "moth":
						canon[i] = "209151"
					case "llokin":
						canon[i] = "265404"
					case "chevrin":
						canon[i] = "265404"
					case "osmite":
						canon[i] = "768220"
					case "nyxite":
						canon[i] = "768221"
					case "director":
						canon[i] = "0"

		if character is not None:
			character = character.lower().split(" ")

		matched_images = []

		for i in images:
			name_matches = name is None or re.search(name, i.name, re.IGNORECASE)
			description_matches = description is None or (
				image_descriptions[i.name].description is not None
				and re.search(
					description,
					image_descriptions[i.name].description,
					re.IGNORECASE,
				)
			)
			canon_matches = (
				canon is None
				or (i.canon is None and "none" in canon)
				or (i.canon is not None and i.canon.lower() in canon)
			)
			character_matches = (
				character is None
				or (len(i.characters) < 1 and "none" in character)
				or [j for j in i.characters if j.lower() in character]
			)
			has_description_matches = (
				has_description is None or i.has_description == has_description
			)

			if (
				name_matches
				and description_matches
				and canon_matches
				and character_matches
				and has_description_matches
			):
				matched_images.append(i)

		return matched_images

	async def search_records(
		self,
		session: aiohttp.ClientSession,
		name: str | None = None,
		chapter: str | None = None,
		iteration: str | None = None,
		language: str | None = None,
		character: str | None = None,
		*,
		requested: bool | None = None,
	) -> list[ftd.Record]:
		"""Search for records from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		name -- Returns records whose title contain this.
		chapter -- Returns records whose chapter match this.
		iteration -- Returns records whose iteration match this.
		language -- Returns records whose languages match this.
		character -- Returns records whose characters match this.
		requested -- Returns records that are or aren't requested.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_full_record_contents and __get_full_episodic) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_full_record_contents and __get_full_episodic) -- A client error occurred
		fractalthorns_exceptions.ItemsUngatheredError (from __get_full_record_contents) -- Items are uncached
		re.error (from re.search) -- Invalid regular expression
		"""
		if language is not None or character is not None or requested is not None:
			record_contents = await self.__get_full_record_contents(session)

		chapters = await self.__get_full_episodic(session)
		records: list[ftd.Record] = []
		for i in chapters:
			records.extend(i.records)

		if chapter is not None:
			chapter = chapter.lower().split(" ")

		if iteration is not None:
			iteration = iteration.lower().split(" ")
			for i in range(len(iteration)):
				match iteration[i]:
					case "vollux":
						iteration[i] = "209151"
					case "moth":
						iteration[i] = "209151"
					case "llokin":
						iteration[i] = "265404"
					case "chevrin":
						iteration[i] = "265404"
					case "osmite":
						iteration[i] = "768220"
					case "nyxite":
						iteration[i] = "768221"
					case "director":
						iteration[i] = "0"

		if language is not None:
			language = language.lower().split(" ")

		if character is not None:
			character = character.lower().split(" ")

		matching_records = []

		for i in records:
			name_matches = name is None or re.search(name, i.name, re.IGNORECASE)
			chapter_matches = chapter is None or i.chapter.lower() in chapter
			iteration_matches = iteration is None or i.iteration.lower() in iteration
			language_matches = language is None or [
				j for j in record_contents[i.name].languages if j.lower() in language
			]
			character_matches = character is None or [
				j for j in record_contents[i.name].characters if j.lower() in character
			]
			requested_matches = (
				requested is None
				or bool(
					[
						j
						for j in record_contents[i.name].header_lines
						if "unrequested" in j
					]
				)
				!= requested
			)

			if (
				name_matches
				and chapter_matches
				and iteration_matches
				and language_matches
				and character_matches
				and requested_matches
			):
				matching_records.append(i)

		return matching_records

	async def search_record_lines(
		self,
		session: aiohttp.ClientSession,
		text: str,
		language: str | None = None,
		character: str | None = None,
		emphasis: str | None = None,
		name: str | None = None,
		chapter: str | None = None,
		iteration: str | None = None,
		*,
		requested: bool | None = None,
	) -> list[ftd.MatchResult]:
		"""Search for record lines from fractalthorns.

		Arguments:
		---------
		session -- The session to use.
		text -- Returns lines whose text contain this.
		language -- Returns lines whose language match this.
		character -- Returns lines whose character match this.
		emphasis -- Returns lines whose emphasis contain this.
		name -- Returns lines whose records' title contain this.
		chapter -- Returns lines whose records' chapter match this.
		iteration -- Returns lines whose records' iteration match this.
		requested -- Returns lines whose records are or aren't requested.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_full_record_contents and __get_full_episodic) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from __get_full_record_contents and __get_full_episodic) -- A client error occurred
		fractalthorns_exceptions.ItemsUngatheredError (from __get_full_record_contents) -- Items are uncached
		re.error (from re.search) -- Invalid regular expression
		RuntimeError -- Loop ran for too long.
		"""
		record_contents = await self.__get_full_record_contents(session)

		chapters = await self.__get_full_episodic(session)
		records: list[ftd.Record] = []
		for i in chapters:
			records.extend(i.records)

		if language is not None:
			language = language.lower().split(" ")

		if character is not None:
			character = character.lower().split(" ")

		if chapter is not None:
			chapter = chapter.lower().split(" ")

		if iteration is not None:
			iteration = iteration.lower().split(" ")
			for i in range(len(iteration)):
				match iteration[i]:
					case "vollux":
						iteration[i] = "209151"
					case "moth":
						iteration[i] = "209151"
					case "llokin":
						iteration[i] = "265404"
					case "chevrin":
						iteration[i] = "265404"
					case "osmite":
						iteration[i] = "768220"
					case "nyxite":
						iteration[i] = "768221"
					case "director":
						iteration[i] = "0"

		matching_lines = []

		for i in records:
			name_matches = name is None or re.search(name, i.name, re.IGNORECASE)
			chapter_matches = chapter is None or i.chapter.lower() in chapter
			iteration_matches = iteration is None or i.iteration.lower() in iteration
			language_matches = language is None or [
				j for j in record_contents[i.name].languages if j.lower() in language
			]
			character_matches = character is None or [
				j for j in record_contents[i.name].characters if j.lower() in character
			]
			requested_matches = (
				requested is None
				or bool(
					[
						j
						for j in record_contents[i.name].header_lines
						if "unrequested" in j
					]
				)
				!= requested
			)

			if not (
				name_matches
				and chapter_matches
				and iteration_matches
				and language_matches
				and character_matches
				and requested_matches
			):
				continue

			for j in record_contents[i.name].lines:
				language_matches = language is None or (
					j.language is not None and j.language.lower() in language
				)
				character_matches = character is None or (
					j.character is not None and j.character.lower() in character
				)
				emphasis_matches = emphasis is None or (
					j.emphasis is not None
					and re.search(emphasis, j.emphasis, re.IGNORECASE) is not None
				)
				text_matches = re.search(text, j.text, re.IGNORECASE) is not None

				if not (
					language_matches
					and character_matches
					and emphasis_matches
					and text_matches
				):
					continue

				j.text = j.format_text()
				line_text = j.text

				max_loop = 100000
				for k in re.finditer(text, line_text, re.IGNORECASE):
					max_loop -= 1
					if max_loop < 0:  # infinite loop safeguard
						msg = "Loop running for too long."
						raise RuntimeError(msg)

					if k.end() - k.start() == 0:
						continue

					matching_lines.append(ftd.MatchResult(i, j, k))

		return matching_lines

	async def __get_all_news(
		self, session: aiohttp.ClientSession
	) -> list[ftd.NewsEntry]:
		"""Get a list all news items.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			self.__cached_news_items is None
			or dt.datetime.now(dt.UTC)
			> self.__cached_news_items[1]
			+ self.__CACHE_DURATION[self.CacheTypes.NEWS_ITEMS]
		):
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.NEWS_ITEMS.value,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.ALL_NEWS.value, None
			)
			async with r as resp:
				resp.raise_for_status()
				news_items = [
					ftd.NewsEntry.from_obj(i)
					for i in json.loads(await resp.text())["items"]
				]

			self.__cached_news_items = (
				news_items,
				dt.datetime.now(dt.UTC),
			)

			self.__cache_saved[self.CacheTypes.NEWS_ITEMS] = False

			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.NEWS_ITEMS.value,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.NEWS_ITEMS.value,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_news_items[0]

	async def __get_single_image(
		self, session: aiohttp.ClientSession, image: str | None
	) -> ftd.Image:
		"""Get a single image.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			image not in self.__cached_images
			or dt.datetime.now(dt.UTC)
			> self.__cached_images[image][1]
			+ self.__CACHE_DURATION[self.CacheTypes.IMAGES]
		):
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGES.value,
				image,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.SINGLE_IMAGE.value, {"name": image}
			)
			async with r as resp:
				resp.raise_for_status()
				image_metadata = json.loads(await resp.text())

			image_metadata["image_url"] = (
				f"{self._base_url}{image_metadata['image_url']}"
			)
			image_metadata["thumb_url"] = (
				f"{self._base_url}{image_metadata['thumb_url']}"
			)
			image_link = f"{self.__BASE_IMAGE_URL}{image_metadata['name']}"

			self.__cached_images.update(
				{
					image: (
						ftd.Image.from_obj(image_link, image_metadata),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			if image is None:
				self.__cached_images.update(
					{
						self.__cached_images[image][0].name: (
							ftd.Image.from_obj(image_link, image_metadata),
							dt.datetime.now(dt.UTC),
						)
					}
				)

			self.__cache_saved[self.CacheTypes.IMAGES] = False

			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGES.value,
				image,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGES.value,
				image,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_images[image][0]

	async def __get_image_contents(
		self, session: aiohttp.ClientSession, image: str
	) -> tuple[Image.Image, Image.Image]:
		"""Get the contents of an image.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			image not in self.__cached_image_contents
			or dt.datetime.now(dt.UTC)
			> self.__cached_image_contents[image][1]
			+ self.__CACHE_DURATION[self.CacheTypes.IMAGE_CONTENTS]
		):
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGE_CONTENTS.value,
				image,
				self.__STALE_CACHE_MESSAGE,
			)

			image_metadata = await self.__get_single_image(session, image)

			async with asyncio.TaskGroup() as tg:
				image_req = tg.create_task(
					session.get(
						f"{image_metadata.image_url}",
						timeout=self.__REQUEST_TIMEOUT,
						headers=self.__DEFAULT_HEADERS,
						raise_for_status=True,
					)
				)
				thumb_req = tg.create_task(
					session.get(
						f"{image_metadata.thumb_url}",
						timeout=self.__REQUEST_TIMEOUT,
						headers=self.__DEFAULT_HEADERS,
						raise_for_status=True,
					)
				)

			async with (
				image_req.result() as image_resp,
				thumb_req.result() as thumb_resp,
				asyncio.TaskGroup() as tg,
			):
				image_bytes = tg.create_task(image_resp.read())
				thumb_bytes = tg.create_task(thumb_resp.read())

			loop = asyncio.get_running_loop()
			image_contents, image_thumbnail = await asyncio.gather(
				loop.run_in_executor(None, Image.open, BytesIO(image_bytes.result())),
				loop.run_in_executor(None, Image.open, BytesIO(thumb_bytes.result())),
			)

			self.__cached_image_contents.update(
				{
					image: (
						(image_contents, image_thumbnail),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			if image is None:
				self.__cached_image_contents.update(
					{
						self.__cached_images[image][0].name: (
							(image_contents, image_thumbnail),
							dt.datetime.now(dt.UTC),
						)
					}
				)

			self.__cache_saved[self.CacheTypes.IMAGE_CONTENTS] = False

			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGE_CONTENTS.value,
				image,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGE_CONTENTS.value,
				image,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_image_contents[image][0]

	async def __get_image_description(
		self, session: aiohttp.ClientSession, image: str
	) -> ftd.ImageDescription:
		"""Get the description of an image.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			image not in self.__cached_image_descriptions
			or dt.datetime.now(dt.UTC)
			> self.__cached_image_descriptions[image][1]
			+ self.__CACHE_DURATION[self.CacheTypes.IMAGE_DESCRIPTIONS]
		):
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGE_DESCRIPTIONS.value,
				image,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.IMAGE_DESCRIPTION.value, {"name": image}
			)
			async with r as resp:
				resp.raise_for_status()
				image_description = json.loads(await resp.text())

			image_title = (await self.__get_single_image(session, image)).title
			image_link = f"{self.__BASE_IMAGE_URL}{image}"

			self.__cached_image_descriptions.update(
				{
					image: (
						ftd.ImageDescription.from_obj(
							image_title, image_link, image_description
						),
						dt.datetime.now(dt.UTC),
					)
				}
			)

			self.__cache_saved[self.CacheTypes.IMAGE_DESCRIPTIONS] = False

			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGE_DESCRIPTIONS.value,
				image,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGE_DESCRIPTIONS.value,
				image,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_image_descriptions[image][0]

	async def __get_all_images(self, session: aiohttp.ClientSession) -> list[ftd.Image]:
		"""Get all images.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			self.__last_all_images_cache is None
			or dt.datetime.now(dt.UTC)
			> self.__last_all_images_cache
			+ self.__CACHE_DURATION[self.CacheTypes.IMAGES]
		):
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGES.value,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.ALL_IMAGES.value, None
			)
			async with r as resp:
				resp.raise_for_status()
				images = json.loads(await resp.text())["images"]

			cache_time = dt.datetime.now(dt.UTC)

			self.purge_cache(self.CacheTypes.IMAGES, force_purge=True)

			for image in images:
				image["image_url"] = f"{self._base_url}{image['image_url']}"
				image["thumb_url"] = f"{self._base_url}{image['thumb_url']}"
				image_link = f"{self.__BASE_IMAGE_URL}{image['name']}"
				self.__cached_images.update(
					{image["name"]: (ftd.Image.from_obj(image_link, image), cache_time)}
				)

			self.__cached_images.update(
				{None: next(iter(self.__cached_images.values()))}
			)

			self.__last_all_images_cache = cache_time

			self.__cache_saved[self.CacheTypes.IMAGES] = False
			self.__cache_saved[self.CacheTypes.CACHE_METADATA] = False

			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGES.value,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.IMAGES.value,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return [j[0] for i, j in self.__cached_images.items() if i is not None]

	async def __get_single_sketch(
		self, session: aiohttp.ClientSession, sketch: str | None
	) -> ftd.Sketch:
		"""Get a single sketch.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			sketch not in self.__cached_sketches
			or dt.datetime.now(dt.UTC)
			> self.__cached_sketches[sketch][1]
			+ self.__CACHE_DURATION[self.CacheTypes.SKETCHES]
		):
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCHES.value,
				sketch,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.SINGLE_SKETCH.value, {"name": sketch}
			)
			async with r as resp:
				resp.raise_for_status()
				sketch_metadata = json.loads(await resp.text())

			sketch_metadata["image_url"] = (
				f"{self._base_url}{sketch_metadata['image_url']}"
			)
			sketch_metadata["thumb_url"] = (
				f"{self._base_url}{sketch_metadata['thumb_url']}"
			)
			sketch_link = f"{self.__BASE_SKETCH_URL}{sketch_metadata['name']}"

			self.__cached_sketches.update(
				{
					sketch: (
						ftd.Sketch.from_obj(sketch_link, sketch_metadata),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			if sketch is None:
				self.__cached_sketches.update(
					{
						self.__cached_sketches[sketch][0].name: (
							ftd.Sketch.from_obj(sketch_link, sketch_metadata),
							dt.datetime.now(dt.UTC),
						)
					}
				)

			self.__cache_saved[self.CacheTypes.SKETCHES] = False

			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCHES.value,
				sketch,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCHES.value,
				sketch,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_sketches[sketch][0]

	async def __get_all_sketches(
		self, session: aiohttp.ClientSession
	) -> dict[str, ftd.Sketch]:
		"""Get all sketches.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			self.__last_all_sketches_cache is None
			or dt.datetime.now(dt.UTC)
			> self.__last_all_sketches_cache
			+ self.__CACHE_DURATION[self.CacheTypes.SKETCHES]
		):
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCHES.value,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.ALL_SKETCHES.value, None
			)
			async with r as resp:
				resp.raise_for_status()
				sketches = json.loads(await resp.text())["sketches"]

			cache_time = dt.datetime.now(dt.UTC)

			self.purge_cache(self.CacheTypes.SKETCHES, force_purge=True)

			for sketch in sketches:
				sketch["image_url"] = f"{self._base_url}{sketch['image_url']}"
				sketch["thumb_url"] = f"{self._base_url}{sketch['thumb_url']}"
				sketch_link = f"{self.__BASE_SKETCH_URL}{sketch['name']}"
				self.__cached_sketches.update(
					{
						sketch["name"]: (
							ftd.Sketch.from_obj(sketch_link, sketch),
							cache_time,
						)
					}
				)

			self.__cached_sketches.update(
				{None: next(iter(self.__cached_sketches.values()))}
			)

			self.__last_all_sketches_cache = cache_time

			self.__cache_saved[self.CacheTypes.SKETCHES] = False

			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCHES.value,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCHES.value,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return {i: j[0] for i, j in self.__cached_sketches.items()}

	async def __get_sketch_contents(
		self, session: aiohttp.ClientSession, sketch: str
	) -> tuple[Image.Image, Image.Image]:
		"""Get the contents of an image.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		fractalthorns_exceptions.SketchNotFoundError -- Sketch not found
		"""
		if (
			sketch not in self.__cached_sketch_contents
			or dt.datetime.now(dt.UTC)
			> self.__cached_sketch_contents[sketch][1]
			+ self.__CACHE_DURATION[self.CacheTypes.SKETCH_CONTENTS]
		):
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCH_CONTENTS.value,
				sketch,
				self.__STALE_CACHE_MESSAGE,
			)

			sketch_metadata = await self.__get_single_sketch(session, sketch)

			async with asyncio.TaskGroup() as tg:
				image_req = tg.create_task(
					session.get(
						f"{sketch_metadata.image_url}",
						timeout=self.__REQUEST_TIMEOUT,
						headers=self.__DEFAULT_HEADERS,
						raise_for_status=True,
					)
				)
				thumb_req = tg.create_task(
					session.get(
						f"{sketch_metadata.thumb_url}",
						timeout=self.__REQUEST_TIMEOUT,
						headers=self.__DEFAULT_HEADERS,
						raise_for_status=True,
					)
				)

			async with (
				image_req.result() as image_resp,
				thumb_req.result() as thumb_resp,
				asyncio.TaskGroup() as tg,
			):
				image_bytes = tg.create_task(image_resp.read())
				thumb_bytes = tg.create_task(thumb_resp.read())

			loop = asyncio.get_running_loop()
			image_contents, image_thumbnail = await asyncio.gather(
				loop.run_in_executor(None, Image.open, BytesIO(image_bytes.result())),
				loop.run_in_executor(None, Image.open, BytesIO(thumb_bytes.result())),
			)

			self.__cached_sketch_contents.update(
				{
					sketch: (
						(image_contents, image_thumbnail),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			if sketch is None:
				self.__cached_sketch_contents.update(
					{
						self.__cached_sketches[sketch][0].name: (
							(image_contents, image_thumbnail),
							dt.datetime.now(dt.UTC),
						)
					}
				)

			self.__cache_saved[self.CacheTypes.SKETCH_CONTENTS] = False

			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCH_CONTENTS.value,
				sketch,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SKETCH_CONTENTS.value,
				sketch,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_sketch_contents[sketch][0]

	async def __get_full_episodic(
		self, session: aiohttp.ClientSession
	) -> list[ftd.Chapter]:
		"""Get the full episodic.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			self.__last_full_episodic_cache is None
			or dt.datetime.now(dt.UTC)
			> self.__last_full_episodic_cache
			+ self.__CACHE_DURATION[self.CacheTypes.CHAPTERS]
		):
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.CHAPTERS.value,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.FULL_EPISODIC.value, None
			)
			async with r as resp:
				resp.raise_for_status()
				chapters_list = json.loads(await resp.text())["chapters"]

			cache_time = dt.datetime.now(dt.UTC)

			self.purge_cache(self.CacheTypes.CHAPTERS, force_purge=True)
			self.purge_cache(self.CacheTypes.RECORDS, force_purge=True)

			chapters = {
				chapter["name"]: ftd.Chapter.from_obj(
					self.__BASE_RECORD_URL, self.__BASE_DISCOVERY_URL, chapter
				)
				for chapter in chapters_list
			}

			self.__cached_chapters = (chapters, cache_time)

			for chapter in chapters.values():
				for record in chapter.records:
					self.__cached_records.update({record.name: (record, cache_time)})

			self.__cached_records.update(
				{None: next(iter(self.__cached_records.values()))}
			)

			self.__last_full_episodic_cache = cache_time

			self.__cache_saved[self.CacheTypes.CHAPTERS] = False
			self.__cache_saved[self.CacheTypes.RECORDS] = False
			self.__cache_saved[self.CacheTypes.CACHE_METADATA] = False

			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.CHAPTERS.value,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.CHAPTERS.value,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return list(self.__cached_chapters[0].values())

	async def __get_single_record(
		self, session: aiohttp.ClientSession, name: str | None
	) -> ftd.Record:
		"""Get a single record.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			name not in self.__cached_records
			or dt.datetime.now(dt.UTC)
			> self.__cached_records[name][1]
			+ self.__CACHE_DURATION[self.CacheTypes.RECORDS]
		):
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.RECORDS.value,
				name,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.SINGLE_RECORD, {"name": name}
			)
			async with r as resp:
				resp.raise_for_status()
				record = json.loads(await resp.text())

			record_link = f"{self.__BASE_RECORD_URL}{record['name']}"
			puzzle_links = None
			if not record["solved"]:
				if record.get("linked_puzzles") is not None:
					puzzle_links = [
						f"{self.__BASE_DISCOVERY_URL}{i}"
						for i in record["linked_puzzles"]
					]
				else:
					puzzle_links = [self.__BASE_DISCOVERY_URL]

			self.__cached_records.update(
				{
					name: (
						ftd.Record.from_obj(record_link, puzzle_links, record),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			if name is None:
				self.__cached_records.update(
					{
						self.__cached_records[name][0].name: (
							ftd.Record.from_obj(record_link, puzzle_links, record),
							dt.datetime.now(dt.UTC),
						)
					}
				)

			self.__cache_saved[self.CacheTypes.RECORDS] = False

			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.RECORDS.value,
				name,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.RECORDS.value,
				name,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_records[name][0]

	async def __get_record_text(
		self, session: aiohttp.ClientSession, name: str | None
	) -> ftd.RecordText:
		"""Get a record's contents.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			name not in self.__cached_record_contents
			or dt.datetime.now(dt.UTC)
			> self.__cached_record_contents[name][1]
			+ self.__CACHE_DURATION[self.CacheTypes.RECORD_CONTENTS]
		):
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.RECORD_CONTENTS.value,
				name,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.RECORD_TEXT.value, {"name": name}
			)
			async with r as resp:
				resp.raise_for_status()
				record_contents = json.loads(await resp.text())

			record_title = (await self.__get_single_record(session, name)).title
			record_link = f"{self.__BASE_RECORD_URL}{name}"
			self.__cached_record_contents.update(
				{
					name: (
						ftd.RecordText.from_obj(
							record_title, record_link, record_contents
						),
						dt.datetime.now(dt.UTC),
					)
				}
			)
			if name is None:
				self.__cached_record_contents.update(
					{
						self.__cached_records[name][0].name: (
							ftd.RecordText.from_obj(
								record_title, record_link, record_contents
							),
							dt.datetime.now(dt.UTC),
						)
					}
				)

			self.__cache_saved[self.CacheTypes.RECORD_CONTENTS] = False

			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.RECORD_CONTENTS.value,
				name,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__ONE_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.RECORD_CONTENTS.value,
				name,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_record_contents[name][0]

	async def __get_domain_search(
		self,
		session: aiohttp.ClientSession,
		term: str,
		type_: Literal["image", "sketch", "episodic-item", "episodic-line"],
	) -> list[ftd.SearchResult]:
		"""Get a domain search.

		Raises
		------
		fractalthorns_exceptions.InvalidSearchType -- Not a valid search type
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if type_ not in {"image", "sketch", "episodic-item", "episodic-line"}:
			msg = "Invalid search type"
			raise fte.InvalidSearchTypeError(msg)

		if (term, type_) not in self.__cached_search_results or dt.datetime.now(
			dt.UTC
		) > self.__cached_search_results[term, type_][1] + self.__CACHE_DURATION[
			self.CacheTypes.SEARCH_RESULTS
		]:
			self.logger.info(
				self.__TWO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SEARCH_RESULTS.value,
				term,
				type_,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session,
				self.ValidRequests.DOMAIN_SEARCH.value,
				{"term": term, "type": type_},
			)
			async with r as resp:
				resp.raise_for_status()
				search_results = json.loads(await resp.text())["results"]

			if type_ == "image":
				for i in search_results:
					if i.get("image") is not None:
						i["image"]["image_url"] = (
							f"{self._base_url}{i['image']['image_url']}"
						)
						i["image"]["thumb_url"] = (
							f"{self._base_url}{i['image']['thumb_url']}"
						)
			elif type_ == "sketch":
				for i in search_results:
					if i.get("sketch") is not None:
						i["sketch"]["image_url"] = (
							f"{self._base_url}{i['sketch']['image_url']}"
						)
						i["sketch"]["thumb_url"] = (
							f"{self._base_url}{i['sketch']['thumb_url']}"
						)
			elif type_ == "episodic-line":
				record_text_tasks = []
				async with asyncio.TaskGroup() as tg:
					for i in search_results:
						if not i["record"]["solved"]:
							continue

						record_name = i["record"]["name"]
						task = tg.create_task(
							self.__get_record_text(session, record_name)
						)
						record_text_tasks.append((i, task))

				for i, j in record_text_tasks:
					line_index = i["record_line_index"]
					i.update({"record_line": (j.result()).lines[line_index]})

			self.__cached_search_results.update(
				{
					(term, type_): (
						[
							ftd.SearchResult.from_obj(
								self.__BASE_IMAGE_URL,
								self.__BASE_SKETCH_URL,
								self.__BASE_RECORD_URL,
								self.__BASE_DISCOVERY_URL,
								i,
							)
							for i in search_results
						],
						dt.datetime.now(dt.UTC),
					)
				}
			)

			self.__cache_saved[self.CacheTypes.SEARCH_RESULTS] = False
			self.__cache_saved[self.CacheTypes.RECORD_CONTENTS] = False

			self.logger.info(
				self.__TWO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SEARCH_RESULTS.value,
				term,
				type_,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__TWO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SEARCH_RESULTS.value,
				term,
				type_,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_search_results[term, type_][0]

	async def __get_current_splash(
		self,
		session: aiohttp.ClientSession,
	) -> ftd.Splash:
		"""Get the current splash, if there is one.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			self.__cached_current_splash is None
			or dt.datetime.now(dt.UTC)
			> self.__cached_current_splash[1]
			+ self.__CACHE_DURATION[self.CacheTypes.CURRENT_SPLASH]
		):
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.CURRENT_SPLASH.value,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.CURRENT_SPLASH.value, None
			)
			async with r as resp:
				resp.raise_for_status()
				current_splash = json.loads(await resp.text())

			current_splash = ftd.Splash.from_obj(current_splash)

			self.__cached_current_splash = (
				current_splash,
				dt.datetime.now(dt.UTC),
			)

			self.__cache_saved[self.CacheTypes.CURRENT_SPLASH] = False

			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.CURRENT_SPLASH.value,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.CURRENT_SPLASH.value,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_current_splash[0]

	async def __get_paged_splashes(
		self,
		session: aiohttp.ClientSession,
		page: int,
	) -> ftd.SplashPage:
		"""Get the specified page of splashes.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if (
			page not in self.__cached_splash_pages
			or dt.datetime.now(dt.UTC)
			> self.__cached_splash_pages[page][1]
			+ self.__CACHE_DURATION[self.CacheTypes.SPLASH_PAGES]
		):
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SPLASH_PAGES.value,
				self.__STALE_CACHE_MESSAGE,
			)

			r = await self._make_request(
				session, self.ValidRequests.PAGED_SPLASHES.value, {"page": page}
			)
			async with r as resp:
				resp.raise_for_status()
				splash_page = json.loads(await resp.text())

			splash_page = ftd.SplashPage.from_obj(splash_page)

			self.__cached_splash_pages = {page: (splash_page, dt.datetime.now(dt.UTC))}

			self.__cache_saved[self.CacheTypes.SPLASH_PAGES] = False

			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SPLASH_PAGES.value,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.SPLASH_PAGES.value,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_splash_pages[page][0]

	async def __post_submit_discord_splash(
		self,
		session: aiohttp.ClientSession,
		text: str,
		submitter_display_name: str,
		submitter_user_id: str,
	) -> None:
		"""Submit a discord splash.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		self.logger.info("User %s is trying to submit a splash", submitter_user_id)
		self.logger.debug('Submitted splash: "%s"', text)

		r = await self._make_request(
			session,
			self.ValidRequests.SUBMIT_DISCORD_SPLASH,
			{
				"text": text,
				"submitter_display_name": submitter_display_name,
				"submitter_user_id": submitter_user_id,
			},
			headers={self.__SPLASH_API_KEY_HEADER: self.__SPLASH_API_KEY},
		)

		async with r as resp:
			resp.raise_for_status()

		self.logger.info("Splash submission successful")

	async def __get_full_record_contents(
		self, session: aiohttp.ClientSession, *, gather: bool | None = None
	) -> dict[str, ftd.RecordText]:
		"""Get the full record contents.

		Raises
		------
		fractalthorns_exceptions.ItemsUngatheredError -- Gather was not True and items are uncached
		fractalthorns_exceptions.CachePurgeError -- Too soon since the last gather
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		cache_stale = (
			self.__cached_full_record_contents is None
			or dt.datetime.now(dt.UTC)
			> self.__cached_full_record_contents[1]
			+ self.__CACHE_DURATION[self.CacheTypes.FULL_RECORD_CONTENTS]
		)
		if gather is True or cache_stale:
			if cache_stale:
				self.logger.info(
					self.__NO_PARAMETER_CACHE_MESSAGE,
					self.CacheTypes.FULL_RECORD_CONTENTS.value,
					self.__STALE_CACHE_MESSAGE,
				)
			else:
				self.logger.info(
					"(%s) cache is not stale but gather was requested.",
					self.CacheTypes.FULL_RECORD_CONTENTS.value,
				)

			if gather is False:
				self.logger.warning(
					"(%s) no cache to retrieve and gather was set to False.",
					self.CacheTypes.FULL_RECORD_CONTENTS.value,
				)
				raise fte.ItemsUngatheredError

			try:
				self.purge_cache(self.CacheTypes.FULL_RECORD_CONTENTS)
			except fte.CachePurgeError:
				if self.__cached_full_record_contents is not None:
					raise

			self.purge_cache(self.CacheTypes.CHAPTERS, force_purge=True)
			self.purge_cache(self.CacheTypes.RECORDS, force_purge=True)
			self.purge_cache(self.CacheTypes.RECORD_CONTENTS, force_purge=True)

			chapters = await self.__get_full_episodic(session)
			records: list[ftd.Record] = []
			for i in chapters:
				records.extend([j for j in i.records if j.solved])

			tasks: list[asyncio.Task] = []
			async with asyncio.TaskGroup() as tg:
				tasks.extend(
					[
						tg.create_task(self.__get_record_text(session, i.name))
						for i in records
					]
				)

			record_contents = {
				records[i].name: tasks[i].result() for i in range(len(records))
			}
			self.__cached_full_record_contents = (
				record_contents,
				dt.datetime.now(dt.UTC),
			)

			self.__cache_saved[self.CacheTypes.FULL_RECORD_CONTENTS] = False

			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.FULL_RECORD_CONTENTS.value,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.FULL_RECORD_CONTENTS.value,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_full_record_contents[0]

	async def __get_full_image_descriptions(
		self, session: aiohttp.ClientSession, *, gather: bool | None = None
	) -> dict[str, ftd.ImageDescription]:
		"""Get the full record contents.

		Raises
		------
		fractalthorns_exceptions.ItemsUngatheredError -- Gather was not True and items are uncached
		fractalthorns_exceptions.CachePurgeError -- Too soon since the last gather
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		cache_stale = (
			self.__cached_full_image_descriptions is None
			or dt.datetime.now(dt.UTC)
			> self.__cached_full_image_descriptions[1]
			+ self.__CACHE_DURATION[self.CacheTypes.FULL_IMAGE_DESCRIPTIONS]
		)
		if gather is True or cache_stale:
			if cache_stale:
				self.logger.info(
					self.__NO_PARAMETER_CACHE_MESSAGE,
					self.CacheTypes.FULL_IMAGE_DESCRIPTIONS.value,
					self.__STALE_CACHE_MESSAGE,
				)
			else:
				self.logger.info(
					"(%s) cache is not stale but gather was requested.",
					self.CacheTypes.FULL_IMAGE_DESCRIPTIONS.value,
				)

			if gather is False:
				self.logger.warning(
					"(%s) no cache to retrieve and gather was set to False.",
					self.CacheTypes.FULL_IMAGE_DESCRIPTIONS.value,
				)
				raise fte.ItemsUngatheredError

			try:
				self.purge_cache(self.CacheTypes.FULL_IMAGE_DESCRIPTIONS)
			except fte.CachePurgeError:
				if self.__cached_full_image_descriptions is not None:
					raise

			self.purge_cache(self.CacheTypes.IMAGE_DESCRIPTIONS, force_purge=True)
			self.purge_cache(self.CacheTypes.IMAGES, force_purge=True)

			images = await self.__get_all_images(session)

			tasks: list[asyncio.Task] = []
			async with asyncio.TaskGroup() as tg:
				tasks.extend(
					[
						tg.create_task(self.__get_image_description(session, i.name))
						for i in images
					]
				)

			image_descriptions = {
				images[i].name: tasks[i].result() for i in range(len(images))
			}
			self.__cached_full_image_descriptions = (
				image_descriptions,
				dt.datetime.now(dt.UTC),
			)

			self.__cache_saved[self.CacheTypes.FULL_IMAGE_DESCRIPTIONS] = False

			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.FULL_IMAGE_DESCRIPTIONS.value,
				self.__RENEWED_CACHE_MESSAGE,
			)

		else:
			self.logger.info(
				self.__NO_PARAMETER_CACHE_MESSAGE,
				self.CacheTypes.FULL_IMAGE_DESCRIPTIONS.value,
				self.__ALREADY_CACHED_MESSAGE,
			)

		return self.__cached_full_image_descriptions[0]

	async def load_cache(self, cache: CacheTypes) -> None:
		"""Load the specified cache."""
		self.logger.info("Loading cache - %s", cache.value)

		try:
			if cache in {
				self.CacheTypes.IMAGE_CONTENTS,
				self.CacheTypes.SKETCH_CONTENTS,
			}:
				cache_path = "".join((self.__CACHE_PATH, cache.value.replace(" ", "_")))

				if not Path(cache_path).exists():
					return

				cache_meta = f"{cache_path}{self.__CACHE_EXT}"

				if not Path(cache_meta).exists():
					return

				async with aiofiles.open(cache_meta, encoding="utf-8") as f:
					saved_images = json.loads(await f.read())

				for i in saved_images:
					timestamp = dt.datetime.fromtimestamp(saved_images[i], tz=dt.UTC)

					image_path = f"{cache_path}/image_{i}.png"
					thumb_path = f"{cache_path}/thumb_{i}.png"

					if not (Path(image_path).exists() and Path(thumb_path).exists()):
						continue

					async with (
						aiofiles.open(image_path, "rb") as image_file,
						aiofiles.open(thumb_path, "rb") as thumb_file,
						asyncio.TaskGroup() as tg,
					):
						image_bytes = tg.create_task(image_file.read())
						thumb_bytes = tg.create_task(thumb_file.read())

					image = Image.open(BytesIO(image_bytes.result()))
					thumb = Image.open(BytesIO(thumb_bytes.result()))

					name = i
					if name == "__None__":
						name = None

					if cache == self.CacheTypes.IMAGE_CONTENTS:
						self.__cached_image_contents.update(
							{
								name: (
									(image, thumb),
									timestamp,
								)
							}
						)
					elif cache == self.CacheTypes.SKETCH_CONTENTS:
						self.__cached_sketch_contents.update(
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

				async with aiofiles.open(cache_path, encoding="utf-8") as f:
					cache_contents = json.loads(await f.read())

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
								ftd.Image.from_obj(j[0]["image_link"], j[0]),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_images = cache_contents
					case self.CacheTypes.IMAGE_DESCRIPTIONS:
						cache_contents = {
							i: (
								ftd.ImageDescription.from_obj(
									j[0]["title"], j[0]["image_link"], j[0]
								),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_image_descriptions = cache_contents
					case self.CacheTypes.SKETCHES:
						cache_contents = {
							(i if i != "__None__" else None): (
								ftd.Sketch.from_obj(j[0]["sketch_link"], j[0]),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_sketches = cache_contents
					case self.CacheTypes.CHAPTERS:
						cache_contents = (
							{
								i: ftd.Chapter.from_obj(
									self.__BASE_RECORD_URL, self.__BASE_DISCOVERY_URL, j
								)
								for i, j in cache_contents[0].items()
							},
							dt.datetime.fromtimestamp(cache_contents[1], tz=dt.UTC),
						)
						self.__cached_chapters = cache_contents
					case self.CacheTypes.RECORDS:
						cache_contents = {
							(i if i != "__None__" else None): (
								ftd.Record.from_obj(
									j[0]["record_link"], j[0]["puzzle_links"], j[0]
								),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_records = cache_contents
					case self.CacheTypes.RECORD_CONTENTS:
						cache_contents = {
							(i if i != "__None__" else None): (
								ftd.RecordText.from_obj(
									j[0]["title"], j[0]["record_link"], j[0]
								),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_record_contents = cache_contents
					case self.CacheTypes.SEARCH_RESULTS:
						cache_contents = {
							(i[: i.rindex("|")], i[i.rindex("|") + 1 :]): (
								[
									ftd.SearchResult.from_obj(
										self.__BASE_IMAGE_URL,
										self.__BASE_SKETCH_URL,
										self.__BASE_RECORD_URL,
										self.__BASE_DISCOVERY_URL,
										k,
									)
									for k in j[0]
								],
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_search_results = cache_contents
					case self.CacheTypes.CURRENT_SPLASH:
						cache_contents = (
							ftd.Splash.from_obj(cache_contents[0]),
							dt.datetime.fromtimestamp(cache_contents[1], tz=dt.UTC),
						)
						self.__cached_current_splash = cache_contents
					case self.CacheTypes.SPLASH_PAGES:
						cache_contents = {
							int(i): (
								ftd.SplashPage.from_obj(j[0]),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_splash_pages = cache_contents
					case self.CacheTypes.FULL_RECORD_CONTENTS:
						cache_contents = (
							{
								i: ftd.RecordText.from_obj(
									j["title"], j["record_link"], j
								)
								for i, j in cache_contents[0].items()
							},
							dt.datetime.fromtimestamp(cache_contents[1], tz=dt.UTC),
						)
						self.__cached_full_record_contents = cache_contents
					case self.CacheTypes.FULL_IMAGE_DESCRIPTIONS:
						cache_contents = (
							{
								i: ftd.ImageDescription.from_obj(
									j["title"], j["image_link"], j
								)
								for i, j in cache_contents[0].items()
							},
							dt.datetime.fromtimestamp(cache_contents[1], tz=dt.UTC),
						)
						self.__cached_full_image_descriptions = cache_contents
					case self.CacheTypes.CACHE_METADATA:
						self.__last_all_images_cache = cache_contents.get(
							"__last_all_images_cache"
						)
						self.__last_all_sketches_cache = cache_contents.get(
							"__last_all_sketches_cache"
						)
						self.__last_full_episodic_cache = cache_contents.get(
							"__last_full_episodic_cache"
						)
						self.__last_cache_purge = cache_contents.get(
							"__last_cache_purge"
						)

						if self.__last_all_images_cache is not None:
							self.__last_all_images_cache = dt.datetime.fromtimestamp(
								self.__last_all_images_cache, tz=dt.UTC
							)
						if self.__last_all_sketches_cache is not None:
							self.__last_all_sketches_cache = dt.datetime.fromtimestamp(
								self.__last_all_sketches_cache, tz=dt.UTC
							)
						if self.__last_full_episodic_cache is not None:
							self.__last_full_episodic_cache = dt.datetime.fromtimestamp(
								self.__last_full_episodic_cache, tz=dt.UTC
							)
						self.__last_cache_purge = {
							self.CacheTypes(i): dt.datetime.fromtimestamp(j, tz=dt.UTC)
							for i, j in self.__last_cache_purge.items()
						}

				self.logger.debug(
					"Loaded cache contents (%s):\n%s", cache.value, cache_contents
				)

		except Exception:
			self.logger.exception("Failed to load cache! (%s)", cache.value)

	async def load_all_caches(self) -> None:
		"""Load all caches."""
		tasks = set()
		async with asyncio.TaskGroup() as tg:
			for i in self.CacheTypes:
				task = tg.create_task(self.load_cache(i))
				tasks.add(task)
				task.add_done_callback(tasks.discard)

	async def save_cache(self, cache: CacheTypes) -> None:
		"""Save the specified cache."""
		if self.__cache_saved[cache]:
			self.logger.info("Cache already saved - %s", cache.value)
			return

		self.logger.info("Saving cache - %s", cache.value)

		try:
			if cache in {
				self.CacheTypes.IMAGE_CONTENTS,
				self.CacheTypes.SKETCH_CONTENTS,
			}:
				cache_path = "".join((self.__CACHE_PATH, cache.value.replace(" ", "_")))

				Path(cache_path).mkdir(parents=True, exist_ok=True)

				saved_images = {}

				if cache == self.CacheTypes.IMAGE_CONTENTS:
					cached_items = self.__cached_image_contents.items()
				elif cache == self.CacheTypes.SKETCH_CONTENTS:
					cached_items = self.__cached_sketch_contents.items()

				for i, j in cached_items:
					name = i
					if name is None:
						name = "__None__"
					image, image_path = (j[0][0], f"{cache_path}/image_{name}.png")
					thumb, thumb_path = (j[0][1], f"{cache_path}/thumb_{name}.png")

					if Path(image_path).exists():
						await aiofiles.os.replace(
							image_path, f"{image_path}{self.__CACHE_BAK}"
						)
					if Path(thumb_path).exists():
						await aiofiles.os.replace(
							thumb_path, f"{thumb_path}{self.__CACHE_BAK}"
						)

					loop = asyncio.get_running_loop()
					await asyncio.gather(
						loop.run_in_executor(None, image.save, image_path),
						loop.run_in_executor(None, thumb.save, thumb_path),
					)

					saved_images.update({name: j[1].timestamp()})

				cache_meta = f"{cache_path}{self.__CACHE_EXT}"

				if Path(cache_meta).exists():
					await aiofiles.os.replace(
						cache_meta, f"{cache_meta}{self.__CACHE_BAK}"
					)

				async with aiofiles.open(cache_meta, "w", encoding="utf-8") as f:
					await f.write(json.dumps(saved_images, indent=4))

			else:
				cache_path = "".join(
					(self.__CACHE_PATH, cache.value.replace(" ", "_"), self.__CACHE_EXT)
				)

				Path(cache_path).parent.mkdir(parents=True, exist_ok=True)

				if Path(cache_path).exists():
					await aiofiles.os.replace(
						cache_path, f"{cache_path}{self.__CACHE_BAK}"
					)

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
					case self.CacheTypes.SKETCHES:
						cache_contents = self.__cached_sketches
						cache_contents = {
							(i if i is not None else "__None__"): (
								asdict(j[0]),
								j[1].timestamp(),
							)
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
							(i if i is not None else "__None__"): (
								asdict(j[0]),
								j[1].timestamp(),
							)
							for i, j in cache_contents.items()
						}
					case self.CacheTypes.RECORD_CONTENTS:
						cache_contents = self.__cached_record_contents
						cache_contents = {
							(i if i is not None else "__None__"): (
								asdict(j[0]),
								j[1].timestamp(),
							)
							for i, j in cache_contents.items()
						}
					case self.CacheTypes.SEARCH_RESULTS:
						cache_contents = self.__cached_search_results
						cache_contents = {
							f"{i[0]}|{i[1]}": (
								[asdict(k) for k in j[0]],
								j[1].timestamp(),
							)
							for i, j in cache_contents.items()
						}
					case self.CacheTypes.CURRENT_SPLASH:
						cache_contents = self.__cached_current_splash
						cache_contents = (
							asdict(cache_contents[0]),
							cache_contents[1].timestamp(),
						)
					case self.CacheTypes.SPLASH_PAGES:
						cache_contents = self.__cached_splash_pages
						cache_contents = {
							i: (
								asdict(j[0]),
								j[1].timestamp(),
							)
							for i, j in cache_contents.items()
						}
					case self.CacheTypes.FULL_RECORD_CONTENTS:
						cache_contents = self.__cached_full_record_contents
						cache_contents = (
							{i: asdict(j) for i, j in cache_contents[0].items()},
							cache_contents[1].timestamp(),
						)
					case self.CacheTypes.FULL_IMAGE_DESCRIPTIONS:
						cache_contents = self.__cached_full_image_descriptions
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
						if self.__last_all_sketches_cache is not None:
							cache_contents.update(
								{
									"__last_all_sketches_cache": self.__last_all_sketches_cache.timestamp()
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
									i.value: j.timestamp()
									for i, j in self.__last_cache_purge.items()
								}
							}
						)

				async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
					await f.write(json.dumps(cache_contents, indent=4))

				self.logger.debug(
					"Saved cache contents (%s):\n%s", cache.value, cache_contents
				)

			self.__cache_saved[cache] = True

		except Exception:
			self.logger.exception("Failed to save cache! (%s)", cache.value)

	async def save_all_caches(self) -> None:
		"""Save all caches."""
		tasks = set()
		async with asyncio.TaskGroup() as tg:
			for i in self.CacheTypes:
				task = tg.create_task(self.save_cache(i))
				tasks.add(task)
				task.add_done_callback(tasks.discard)


fractalthorns_api: FractalthornsAPI = None

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
