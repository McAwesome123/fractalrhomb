"""Module for accessing the fractalthorns API"""

import json
import datetime as dt

from typing import Dict, List, Tuple, Optional
from enum import StrEnum
from api_access import RequestArgument, Request, API

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
		self.__cached_images = None
		self.__cached_image_contents = None
		self.__cached_image_descriptions = None
		self.__cached_records = None
		self.__cached_record_contents = None
		self.__cache_purge_allowed: Tuple[dt.datetime, str] = None

	__CACHE_DURATION: dt.timedelta = dt.timedelta(days = 1)

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
			self.__cached_images = None
			self.__cached_image_contents = None
			self.__cached_image_descriptions = None
			self.__cached_records = None
			self.__cached_record_contents = None
			new_time = dt.datetime.now(dt.UTC) + dt.timedelta(hours = 1)
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

	def get_single_image(self, name: Optional[str]):
		"""not implemented"""
		return self.make_request("single_image", {"name": name})

	def get_image_description(self, name: str):
		"""not implemented"""
		return self.make_request("image_description", {"name": name})

	def get_all_images(self):
		"""not implemented"""
		return self.make_request("all_images", None)

	def get_full_episodic(self):
		"""not implemented"""
		return self.make_request("full_episodic", None)

	def get_single_record(self, name: str):
		"""not implemented"""
		return self.make_request("single_record", {"name": name})

	def get_record_text(self, name: str):
		"""not implemented"""
		return self.make_request("record_text", {"name": name})

	def get_domain_search(self, term: str, type_: str):
		"""not implemented"""
		return self.make_request("domain_search", {"term": term, "type": type_})


	def __get_images_list(self) -> List[str]:
		if self.__valid_image_urls is None or dt.datetime.now(dt.UTC) > self.__valid_image_urls[1]:
			r = self.make_request(self.ValidRequests.ALL_IMAGES.value, None)
			r.raise_for_status()

			images = [i["name"] for i in json.loads(r.text)["images"]]
			self.__valid_image_urls = (images, dt.datetime.now(dt.UTC) + self.__CACHE_DURATION)

		return self.__valid_image_urls[0]

	def __get_records_list(self) -> List[str]:
		if self.__valid_record_urls is None or dt.datetime.now(dt.UTC) > self.__valid_record_urls[1]:
			r = self.make_request(self.ValidRequests.FULL_EPISODIC.value, None)
			r.raise_for_status()

			records = []
			for chapter in json.loads(r.text)["chapters"]:
				for record in chapter["records"]:
					if record["solved"]:
						records.append(record["name"])
			self.__valid_record_urls = (records, dt.datetime.now(dt.UTC) + self.__CACHE_DURATION)

		return self.__valid_record_urls[0]

	def __get_news_items(self) -> List[Dict[str, str]]:
		if self.__cached_news_items is None or dt.datetime.now(dt.UTC) > self.__cached_news_items[1]:
			r = self.make_request(self.ValidRequests.ALL_NEWS.value, None)
			r.raise_for_status()

			self.__cached_news_items = (json.loads(r.text)["items"],
										dt.datetime.now(dt.UTC) + self.__CACHE_DURATION)

		return self.__cached_news_items[0]

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

			if format_ == "changes" and formatting[format_]:
				changes_list = [" ".join(("> -", j)) for j in item["items"]]
				changes = "\n".join(changes_list)
				news_join_list.append(changes)

			if format_ == "version" and formatting[format_] and item.get("version") is not None:
				version = "".join(("> _", item["version"], "_"))
				news_join_list.append(version)

		return "\n".join(news_join_list)

api = FractalthornsAPI()
