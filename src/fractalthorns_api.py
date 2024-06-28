"""Module for accessing the fractalthorns API"""

import json
import datetime as dt

from typing import Dict, List, Tuple, Optional
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
		self.__cached_images: Dict[str, Tuple[Dict[str, str], dt.datetime]] = {}
		self.__cached_image_contents = {}
		self.__cached_image_descriptions = {}
		self.__cached_records = {}
		self.__cached_record_contents = {}
		self.__cache_purge_allowed: Tuple[dt.datetime, str] = (dt.datetime.now(dt.UTC),)

	__CACHE_DURATION: dt.timedelta = dt.timedelta(days = 1)
	__CACHE_PURGE_COOLDOWN: dt.timedelta = dt.timedelta(hours = 2)
	__CACHE_PURGE_ALL_IMAGES_COOLDOWN: dt.timedelta = dt.timedelta(minutes = 30)
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
		"""Get image description from fractalthorns

		Arguments:
		name -- Identifying name of the image
		"""
		image_title = self.__get_single_image(name)["title"]
		image_description = self.__get_image_description(name)

		image_title = "".join((">>> ## ", image_title))
		image_description = image_description.rstrip() if image_description is not None \
				else "no description"

		return "\n".join((image_title, image_description))

	def get_all_images(self, *, start_index = 0, amount = 10) -> str:
		"""Get all images from fractalthorns

		Keyword Arguments:
		start_index -- Which image to start at (default 0)
		amount -- How many images to show (default 10)
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

	def __get_all_images(self) -> List[Dict[str, str]]:
		outdated = False
		for image in self.__get_images_list():
			if image not in self.__cached_images or dt.datetime.now(dt.UTC) > self.__cached_images[image][1]:
				outdated = True
				break

		if outdated:
			r = self.make_request(self.ValidRequests.ALL_IMAGES.value, None)
			r.raise_for_status()

			images = json.loads(r.text)["images"]
			cache_time = dt.datetime.now(dt.UTC) + self.__CACHE_DURATION

			for image in images:
				self.__cached_images.update({image["name"]: (image, cache_time)})

			cache_purge_time = dt.datetime.now(dt.UTC) + self.__CACHE_PURGE_ALL_IMAGES_COOLDOWN
			if self.__cache_purge_allowed[0] < cache_purge_time:
				self.__cache_purge_allowed = (cache_purge_time,
											  self.InvalidPurgeReasons.ALL_IMAGES_REQUEST.value)

		return [i[0] for i in self.__cached_images.values()]

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


api = FractalthornsAPI()
