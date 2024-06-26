"""Module for accessing the API of a website"""

from typing import List, Dict, Optional
from dataclasses import dataclass

import json
import requests

@dataclass(frozen = True)
class RequestArgument:
	"""Contains the name of the argument and whether it's optional"""
	name: str
	optional: bool

@dataclass(frozen = True)
class Request:
	"""Contains the endpoint URL and valid arguments. Used to make requests.

	__endpoint_url -- The API endpoint
	__request_arguments -- List of allowed arguments
	"""
	__endpoint_url: str
	__request_arguments: Optional[List[RequestArgument]]

	def make_request(self, url: str, request_payload: Optional[Dict[str, str]],
					 *, strictly_match_request_arguments = True) -> requests.Response:
		"""Makes a GET request to the predefined endpoint and returns the response

		Arguments:
		url -- Full URL to the API where the endpoint is located
		request_payload -- Arguments that will be passed as JSON to ?body={}

		Keyword Arguments:
		strictly_match_request_arguments -- If True, raises a ValueError if
		request_payload contains undefined arguments (default True)
		"""
		if strictly_match_request_arguments:
			self.__check_arguments(request_payload)

		if self.__request_arguments is not None:
			for i in self.__request_arguments:
				if not i.optional and i.name not in request_payload.keys():
					raise ValueError(f"Missing required request argument: {i.name}")

		final_url = ''.join((url, self.__endpoint_url))
		arguments = "{}"
		if self.__request_arguments is not None and request_payload is not None:
			arguments = json.dumps(request_payload)

		return requests.get(final_url, params = {"body": arguments}, timeout = 10)

	def __check_arguments(self, request_payload: Optional[Dict[str, str]]):
		"""Raises a ValueError if request_payload contains undefined arguments"""
		if self.__request_arguments is None and request_payload is not None:
			raise ValueError("Too many request arguments specified" \
				f"(expected: 0, got {len(request_payload)}).")

		if request_payload is not None:
			for i in request_payload.keys():
				arguments = [i.name for i in self.__request_arguments]
				if i not in arguments:
					raise ValueError("Too many request arguments specified" \
						f"(expected: {len(arguments)}, got {len(request_payload)}).")

@dataclass(frozen = True)
class API:
	"""Contains the website URL and API URL, as well as
	a list of requests that are allowed by the website's API.

	_base_url -- The URL of the website
	_api_url -- The relative URL of the API
	_requests_list --
	"""
	_base_url: str
	_api_url: str
	_requests_list: Dict[str, Request]

	def make_request(self, endpoint: str, request_payload: Optional[Dict[str, str]],
					 *, strictly_match_request_arguments = True) -> requests.Response:
		"""Makes a request at one of the predefined endpoints

		Arguments:
		endpoint -- Name of the endpoint
		request_payload -- Arguments that will be passed as JSON to ?body={}

		Keyword Arguments:
		strictly_match_request_arguments -- If True, raises a ValueError if
		request_payload contains undefined arguments (default True)
		"""

		final_url = ''.join((self._base_url, self._api_url))
		return self._requests_list.get(endpoint).make_request(
			final_url, request_payload,
			strictly_match_request_arguments = strictly_match_request_arguments
		)
