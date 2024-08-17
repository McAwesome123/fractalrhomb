# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module for accessing the API of a website."""

import json
from dataclasses import dataclass

import aiohttp

import src.fractalthorns_exceptions as fte


@dataclass(frozen=True)
class RequestArgument:
	"""Contains the name of the argument and whether it's optional."""

	name: str
	optional: bool


@dataclass(frozen=True)
class Request:
	"""Contains the endpoint URL and valid arguments. Used to make requests.

	__endpoint_url -- The API endpoint
	__request_arguments -- List of allowed arguments
	"""

	__endpoint_url: str
	__request_arguments: list[RequestArgument] | None

	async def make_request(
		self,
		session: aiohttp.ClientSession,
		url: str,
		request_payload: dict[str, str] | None,
		*,
		strictly_match_request_arguments: bool = True,
		headers: dict[str, str] | None = None,
	) -> aiohttp.client._RequestContextManager:
		"""Make a GET request to the predefined endpoint and return the response.

		Arguments:
		---------
		session -- An aiohttp client session to use
		url -- Full URL to the API where the endpoint is located
		request_payload -- Arguments that will be passed as JSON to ?body={}

		Keyword Arguments:
		-----------------
		strictly_match_request_arguments -- If True, raises a ParameterError if
		request_payload contains undefined arguments (default True)
		headers -- Headers to pass to aiohttp.ClientSession.get() (default {})

		Raises:
		------
		fractalthorns_exceptions.ParameterError -- A required request argument is missing
		fractalthorns_exceptions.ParameterError (from __check_arguments) -- Unexpected request argument
		aiohttp.client_exceptions.ClientError (from aiohttp.ClientSession.get) -- A client error occurred
		"""
		if headers is None:
			headers = {}

		if strictly_match_request_arguments:
			self.__check_arguments(request_payload)

		if self.__request_arguments is not None:
			for i in self.__request_arguments:
				if not i.optional and i.name not in request_payload:
					msg = f"Missing required request argument: {i.name}"
					raise fte.ParameterError(msg)

		final_url = f"{url}{self.__endpoint_url}"
		arguments = "{}"
		if self.__request_arguments is not None and request_payload is not None:
			arguments = json.dumps(request_payload)

		return session.get(
			final_url, params={"body": arguments}, timeout=30.0, headers=headers
		)

	def __check_arguments(self, request_payload: dict[str, str] | None) -> None:
		"""Raise a ParameterError if request_payload contains undefined arguments."""
		if self.__request_arguments is None and request_payload is not None:
			exc = (
				"Too many request arguments specified"
				f"(expected: 0, got {len(request_payload)})."
			)
			raise fte.ParameterError(exc)

		if request_payload is not None:
			for i in request_payload:
				arguments = [i.name for i in self.__request_arguments]
				if i not in arguments:
					exc = (
						"Too many request arguments specified"
						f"(expected: {len(arguments)}, got {len(request_payload)})."
					)
					raise fte.ParameterError(exc)


@dataclass(frozen=True)
class API:
	"""Contains the website URL and API URL, as well as a list of requests that are allowed by the website's API.

	_base_url -- The URL of the website
	_api_url -- The relative URL of the API
	_requests_list -- Dictionary of requests that can be made
	"""

	_base_url: str
	_api_url: str
	_requests_list: dict[str, Request]

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
		session -- An aiohttp client session to use
		endpoint -- Name of the endpoint
		request_payload -- Arguments that will be passed as JSON to ?body={}

		Keyword Arguments:
		-----------------
		strictly_match_request_arguments -- If True, raises a ParameterError if
		request_payload contains undefined arguments (default True)
		headers -- Headers to pass to aiohttp.ClientSession.get() (default {})

		Raises:
		------
		fractalthorns_exceptions.ParameterError (from Request.make_request) -- A required request argument is missing
		fractalthorns_exceptions.ParameterError (from Request.make_request) -- Unexpected request argument
		aiohttp.client_exceptions.ClientError (from aiohttp.ClientSession.get) -- A client error occurred
		"""
		if headers is None:
			headers = {}

		final_url = f"{self._base_url}{self._api_url}"
		return await self._requests_list.get(endpoint).make_request(
			session,
			final_url,
			request_payload,
			strictly_match_request_arguments=strictly_match_request_arguments,
			headers=headers,
		)
