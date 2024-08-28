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

		NEWS_ITEMS = "news"
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
		self.logger = logging.getLogger("fractalthorns_api")

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
		self.__BASE_IMAGE_URL = f"{self._base_url}/image/"
		self.__BASE_RECORD_URL = f"{self._base_url}/episodic/"

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
			tuple[str, Literal["image", "episodic-item", "episodic-line"]],
			tuple[list[ftd.SearchResult], dt.datetime],
		] = {}
		self.__cached_full_record_contents: (
			tuple[dict[str, ftd.RecordText], dt.datetime] | None
		) = None
		self.__last_all_images_cache: dt.datetime | None = None
		self.__last_full_episodic_cache: dt.datetime | None = None
		self.__last_cache_purge: dict[self.CacheTypes, dt.datetime] = {}

		asyncio.run(self.load_all_caches())

		self.__cache_saved: dict[self.CacheTypes, bool] = dict.fromkeys(
			self.CacheTypes, True
		)

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
	__CACHE_PATH: str = ".apicache/cache_"
	__CACHE_EXT: str = ".json"
	__CACHE_BAK: str = ".bak"
	__STALE_CACHE_MESSAGE = "cache is missing or stale."
	__RENEWED_CACHE_MESSAGE = "renewed cache."
	__ALREADY_CACHED_MESSAGE = "already cached."

	async def _make_request(
		self,
		session: aiohttp.ClientSession,
		endpoint: str,
		request_payload: dict[str, str] | None,
		*,
		strictly_match_request_arguments: bool = True,
		headers: dict[str, str] | None = None,
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
		if headers is None:
			headers = self.__DEFAULT_HEADERS

		return await super()._make_request(
			session,
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
		"""
		msg = f"Purge for {cache.value} requested."
		self.logger.info(msg)

		if (
			not force_purge
			and self.__last_cache_purge.get(cache) is not None
			and dt.datetime.now(dt.UTC)
			< self.__last_cache_purge[cache] + self.__CACHE_PURGE_COOLDOWN[cache]
		):
			msg = f"Purge failed: {self.InvalidPurgeReasons.CACHE_PURGE.value}"
			self.logger.info(msg)

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
				msg = f"Purge failed: {self.InvalidPurgeReasons.INVALID_CACHE.value}"
				self.logger.warning(msg)

				msg = f"{self.InvalidPurgeReasons.INVALID_CACHE.value}: {cache}"
				raise fte.CachePurgeError(msg)

		self.__last_cache_purge.update({cache: dt.datetime.now(dt.UTC)})

		msg = f"Successfully purged {cache.value}."
		self.logger.info(msg)

	def get_cached_items(
		self, cache: CacheTypes, *, ignore_stale: bool = False
	) -> (
		tuple[list[ftd.NewsEntry], dt.datetime, dt.datetime]
		| dict[str, tuple[ftd.Image, dt.datetime, dt.datetime]]
		| dict[str, tuple[tuple[Image.Image, Image.Image], dt.datetime, dt.datetime]]
		| dict[str, tuple[ftd.ImageDescription, dt.datetime, dt.datetime]]
		| tuple[dict[str, ftd.Chapter], dt.datetime, dt.datetime]
		| dict[str, tuple[ftd.Record, dt.datetime, dt.datetime]]
		| dict[str, tuple[ftd.RecordText, dt.datetime, dt.datetime]]
		| dict[
			tuple[str, Literal["image", "episodic-item", "episodic-line"]],
			tuple[list[ftd.SearchResult], dt.datetime, dt.datetime],
		]
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
		CHAPTERS -- ({Name: Chapter}, Cache Time, Expiry Time) | None
		RECORDS -- {Name: (Record, Cache Time, Expiry Time)}
		RECORD_CONTENTS -- {Name: (RecordText, Cache Time, Expiry Time)}
		SEARCH_RESULTS -- {(Search Term, Search Type): (Record, Cache Time, Expiry Time)}
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

			case self.CacheTypes.CHAPTERS:
				cached_items = deepcopy(self.__cached_chapters)

			case self.CacheTypes.RECORDS:
				cached_items = deepcopy(self.__cached_records)

			case self.CacheTypes.RECORD_CONTENTS:
				cached_items = deepcopy(self.__cached_record_contents)

			case self.CacheTypes.SEARCH_RESULTS:
				cached_items = deepcopy(self.__cached_search_results)

			case self.CacheTypes.CACHE_METADATA:
				last_full_images_cache = deepcopy(self.__last_all_images_cache)
				last_full_episodic_cache = deepcopy(self.__last_full_episodic_cache)
				last_cache_purge = deepcopy(self.__last_cache_purge)
				cached_items = {
					"last_all_images_cache": (
						last_full_images_cache,
						last_full_images_cache
						+ self.__CACHE_DURATION[self.CacheTypes.IMAGES],
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

		if cache in {self.CacheTypes.NEWS_ITEMS, self.CacheTypes.CHAPTERS}:
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
			self.CacheTypes.RECORDS,
			self.CacheTypes.RECORD_CONTENTS,
			self.CacheTypes.SEARCH_RESULTS,
		}:
			for i, j in cached_items.items():
				if not ignore_stale and now > j[1] + self.__CACHE_DURATION[cache]:
					cached_items.pop(i)
				else:
					cached_items[i] = (*j, j[1] + self.__CACHE_DURATION[cache])

		return cached_items

	async def get_all_news(self, session: aiohttp.ClientSession) -> list[ftd.NewsEntry]:
		"""Get news items from fractalthorns.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from __get_all_news) -- A client error occurred
		"""
		return await self.__get_all_news(session)

	async def get_single_image(
		self, session: aiohttp.ClientSession, name: str | None
	) -> tuple[ftd.Image, tuple[Image.Image, Image.Image]]:
		"""Get an image from fractalthorns.

		Arguments:
		---------
		name -- Identifying name of the image.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_single_image and __get_image_contents) -- A client error occurred
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
		name -- Identifying name of the image.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_image_description) -- A client error occurred
		"""
		return await self.__get_image_description(session, name)

	async def get_all_images(self, session: aiohttp.ClientSession) -> list[ftd.Image]:
		"""Get all images from fractalthorns.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from __get_all_images) -- A client error occurred
		"""
		return await self.__get_all_images(session)

	async def get_full_episodic(
		self, session: aiohttp.ClientSession
	) -> list[ftd.Chapter]:
		"""Get the full episodic from fractalthorns.

		Raises
		------
		aiohttp.client_exceptions.ClientError (from __get_full_episodic) -- A client error occurred
		"""
		return await self.__get_full_episodic(session)

	async def get_single_record(
		self, session: aiohttp.ClientSession, name: str
	) -> ftd.Record:
		"""Get a record from fractalthorns.

		Arguments:
		---------
		name -- Identifying name of the record.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_single_record) -- A client error occurred
		"""
		return await self.__get_single_record(session, name)

	async def get_record_text(
		self, session: aiohttp.ClientSession, name: str
	) -> ftd.RecordText:
		"""Get the contents of a record from fractalthorns.

		Arguments:
		---------
		name -- Identifying name of the record.

		Raises:
		------
		aiohttp.client_exceptions.ClientError (from __get_record_text) -- A client error occurred
		"""
		return await self.__get_record_text(session, name)

	async def get_domain_search(
		self,
		session: aiohttp.ClientSession,
		term: str,
		type_: Literal["image", "episodic-item", "episodic-line"],
	) -> list[ftd.SearchResult]:
		"""Get domain search results from fractalthorns.

		Arguments:
		---------
		term -- The term to search for.
		type_ -- Type of search (valid: "image", "episodic-item", "episodic-line").

		Raises:
		------
		fractalthorns_exceptions.InvalidSearchType (from __get_domain_search) -- Not a valid search type
		aiohttp.client_exceptions.ClientError (from __get_domain_search) -- A client error occurred
		"""
		return await self.__get_domain_search(session, term, type_)

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
			msg = f"({self.CacheTypes.NEWS_ITEMS.value}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

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

			msg = f"({self.CacheTypes.NEWS_ITEMS.value}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = (
				f"({self.CacheTypes.NEWS_ITEMS.value}) {self.__ALREADY_CACHED_MESSAGE}"
			)
			self.logger.info(msg)

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
			msg = f"({self.CacheTypes.IMAGES.value} - {image}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

			r = await self._make_request(
				session, self.ValidRequests.SINGLE_IMAGE.value, {"name": image}
			)
			async with r as resp:
				resp.raise_for_status()
				image_metadata = json.loads(await resp.text())

			image_metadata["image_url"] = (
				f"{self._base_url}{image_metadata["image_url"]}"
			)
			image_metadata["thumb_url"] = (
				f"{self._base_url}{image_metadata["thumb_url"]}"
			)
			image_link = f"{self.__BASE_IMAGE_URL}{image_metadata["name"]}"

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

			msg = f"({self.CacheTypes.IMAGES.value} - {image}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = f"({self.CacheTypes.IMAGES.value}) {self.__ALREADY_CACHED_MESSAGE}"
			self.logger.info(msg)

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
			msg = f"({self.CacheTypes.IMAGE_CONTENTS.value} - {image}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

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

			self.__cache_saved[self.CacheTypes.IMAGE_CONTENTS] = False

			msg = f"({self.CacheTypes.IMAGE_CONTENTS.value} - {image}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = f"({self.CacheTypes.IMAGE_CONTENTS.value} - {image}) {self.__ALREADY_CACHED_MESSAGE}"
			self.logger.info(msg)

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
			msg = f"({self.CacheTypes.IMAGE_DESCRIPTIONS.value} - {image}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

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

			msg = f"({self.CacheTypes.IMAGE_DESCRIPTIONS.value} - {image}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = f"({self.CacheTypes.IMAGE_DESCRIPTIONS.value} - {image}) {self.__ALREADY_CACHED_MESSAGE}"
			self.logger.info(msg)

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
			msg = f"({self.CacheTypes.IMAGES.value}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

			r = await self._make_request(
				session, self.ValidRequests.ALL_IMAGES.value, None
			)
			async with r as resp:
				resp.raise_for_status()
				images = json.loads(await resp.text())["images"]

			cache_time = dt.datetime.now(dt.UTC)

			self.purge_cache(self.CacheTypes.IMAGES, force_purge=True)

			for image in images:
				image["image_url"] = f"{self._base_url}{image["image_url"]}"
				image["thumb_url"] = f"{self._base_url}{image["thumb_url"]}"
				image_link = f"{self.__BASE_IMAGE_URL}{image["name"]}"
				self.__cached_images.update(
					{image["name"]: (ftd.Image.from_obj(image_link, image), cache_time)}
				)

			self.__cached_images.update(
				{None: next(iter(self.__cached_images.values()))}
			)

			self.__last_all_images_cache = cache_time

			self.__cache_saved[self.CacheTypes.IMAGES] = False
			self.__cache_saved[self.CacheTypes.CACHE_METADATA] = False

			msg = f"({self.CacheTypes.IMAGES.value}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = f"({self.CacheTypes.IMAGES.value}) {self.__ALREADY_CACHED_MESSAGE}"
			self.logger.info(msg)

		return [j[0] for i, j in self.__cached_images.items() if i is not None]

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
			msg = f"({self.CacheTypes.CHAPTERS.value}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

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
				chapter["name"]: ftd.Chapter.from_obj(self.__BASE_RECORD_URL, chapter)
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

			self.__cache_saved[self.CacheTypes.CHAPTERS] = False
			self.__cache_saved[self.CacheTypes.RECORDS] = False
			self.__cache_saved[self.CacheTypes.CACHE_METADATA] = False

			msg = f"({self.CacheTypes.CHAPTERS.value}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = f"({self.CacheTypes.CHAPTERS.value}) {self.__ALREADY_CACHED_MESSAGE}"
			self.logger.info(msg)

		return list(self.__cached_chapters[0].values())

	async def __get_single_record(
		self, session: aiohttp.ClientSession, name: str
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
			msg = f"({self.CacheTypes.RECORDS.value} - {name}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

			r = await self._make_request(
				session, self.ValidRequests.SINGLE_RECORD, {"name": name}
			)
			async with r as resp:
				resp.raise_for_status()
				record = json.loads(await resp.text())

			record_link = None
			if record["solved"]:
				record_link = f"{self.__BASE_RECORD_URL}{record["name"]}"

			self.__cached_records.update(
				{
					name: (
						ftd.Record.from_obj(record_link, record),
						dt.datetime.now(dt.UTC),
					)
				}
			)

			self.__cache_saved[self.CacheTypes.RECORDS] = False

			msg = f"({self.CacheTypes.RECORDS.value} - {name}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = f"({self.CacheTypes.RECORDS.value} - {name}) {self.__ALREADY_CACHED_MESSAGE}"
			self.logger.info(msg)

		return self.__cached_records[name][0]

	async def __get_record_text(
		self, session: aiohttp.ClientSession, name: str
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
			msg = f"({self.CacheTypes.RECORD_CONTENTS.value} - {name}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

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

			self.__cache_saved[self.CacheTypes.RECORD_CONTENTS] = False

			msg = f"({self.CacheTypes.RECORD_CONTENTS.value} - {name}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = f"({self.CacheTypes.RECORD_CONTENTS.value} - {name}) {self.__ALREADY_CACHED_MESSAGE}"
			self.logger.info(msg)

		return self.__cached_record_contents[name][0]

	async def __get_domain_search(
		self,
		session: aiohttp.ClientSession,
		term: str,
		type_: Literal["image", "episodic-item", "episodic-line"],
	) -> list[ftd.SearchResult]:
		"""Get a domain search.

		Raises
		------
		fractalthorns_exceptions.InvalidSearchType -- Not a valid search type
		aiohttp.client_exceptions.ClientError (from _make_request) -- A client error occurred
		aiohttp.client_exceptions.ClientResponseError (from aiohttp.ClientResponse.raise_for_status) -- A client error occurred
		"""
		if type_ not in {"image", "episodic-item", "episodic-line"}:
			msg = "Invalid search type"
			raise fte.InvalidSearchTypeError(msg)

		if (term, type_) not in self.__cached_search_results or dt.datetime.now(
			dt.UTC
		) > self.__cached_search_results[term, type_][1] + self.__CACHE_DURATION[
			self.CacheTypes.SEARCH_RESULTS
		]:
			msg = f"({self.CacheTypes.SEARCH_RESULTS.value} - {term}, {type_}) {self.__STALE_CACHE_MESSAGE}"
			self.logger.info(msg)

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
							f"{self._base_url}{i["image"]["image_url"]}"
						)
						i["image"]["thumb_url"] = (
							f"{self._base_url}{i["image"]["thumb_url"]}"
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
								self.__BASE_RECORD_URL, self.__BASE_IMAGE_URL, i
							)
							for i in search_results
						],
						dt.datetime.now(dt.UTC),
					)
				}
			)

			self.__cache_saved[self.CacheTypes.SEARCH_RESULTS] = False
			self.__cache_saved[self.CacheTypes.RECORD_CONTENTS] = False

			msg = f"({self.CacheTypes.SEARCH_RESULTS.value} - {term}, {type_}) {self.__RENEWED_CACHE_MESSAGE}"
			self.logger.info(msg)

		else:
			msg = f"({self.CacheTypes.SEARCH_RESULTS.value} - {term}, {type_}) {self.__ALREADY_CACHED_MESSAGE}"
			self.logger.info(msg)

		return self.__cached_search_results[term, type_][0]

	async def load_cache(self, cache: CacheTypes) -> None:
		"""Load the specified cache."""
		msg = f"({cache.value} loading cache."
		self.logger.info(msg)

		try:
			if cache == self.CacheTypes.IMAGE_CONTENTS:
				cache_path = "".join((self.__CACHE_PATH, cache.value.replace(" ", "_")))

				if not Path(cache_path).exists():
					return

				cache_meta = f"{cache_path}{self.__CACHE_EXT}"

				if not Path(cache_meta).exists():
					return

				async with aiofiles.open(cache_meta, "r", encoding="utf-8") as f:
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

				async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
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
					case self.CacheTypes.CHAPTERS:
						cache_contents = (
							{
								i: ftd.Chapter.from_obj(self.__BASE_RECORD_URL, j)
								for i, j in cache_contents[0].items()
							},
							dt.datetime.fromtimestamp(cache_contents[1], tz=dt.UTC),
						)
						self.__cached_chapters = cache_contents
					case self.CacheTypes.RECORDS:
						cache_contents = {
							i: (
								ftd.Record.from_obj(j[0]["record_link"], j[0]),
								dt.datetime.fromtimestamp(j[1], tz=dt.UTC),
							)
							for i, j in cache_contents.items()
						}
						self.__cached_records = cache_contents
					case self.CacheTypes.RECORD_CONTENTS:
						cache_contents = {
							i: (
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
										self.__BASE_RECORD_URL, self.__BASE_IMAGE_URL, k
									)
									for k in j[0]
								],
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
						self.__last_cache_purge = cache_contents.get(
							"__last_cache_purge"
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
							self.CacheTypes(i): dt.datetime.fromtimestamp(j, tz=dt.UTC)
							for i, j in self.__last_cache_purge.items()
						}

		except Exception:
			msg = f"Failed to load cache! ({cache.value})"
			self.logger.exception(msg)

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
			msg = f"({cache.value}) cache already saved."
			self.logger.info(msg)
			return

		msg = f"({cache.value}) saving cache."
		self.logger.info(msg)

		try:
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
							f"{i[0]}|{i[1]}": (
								[asdict(k) for k in j[0]],
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
									i.value: j.timestamp()
									for i, j in self.__last_cache_purge.items()
								}
							}
						)

				async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
					await f.write(json.dumps(cache_contents, indent=4))

			self.__cache_saved[cache] = True

		except Exception:
			msg = f"Failed to save cache! ({cache.value})"
			self.logger.exception(msg)

	async def save_all_caches(self) -> None:
		"""Save all caches."""
		tasks = set()
		async with asyncio.TaskGroup() as tg:
			for i in self.CacheTypes:
				task = tg.create_task(self.save_cache(i))
				tasks.add(task)
				task.add_done_callback(tasks.discard)


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
