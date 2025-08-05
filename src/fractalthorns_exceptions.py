# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Module containing exceptions used the fractalthorns API handler."""

import datetime as dt


class APIError(Exception):
	"""General purpose Fractalthorns API handler exception."""


class ParameterError(APIError):
	"""Missing or unexpected request argument."""


class CachePurgeError(APIError):
	"""Cannot purge the cache."""

	def __init__(
		self, reason: str | None = None, allowed_time: dt.datetime | None = None, /
	) -> "CachePurgeError":
		"""Create a cache purge error."""
		self.reason = reason
		self.allowed_time = allowed_time


class CacheFetchError(APIError):
	"""Invalid cache to fetch."""


class InvalidSearchTypeError(APIError):
	"""Not a valid search type."""


class ItemsUngatheredError(APIError):
	"""The full items are not cached."""


class SketchNotFoundError(APIError):
	"""The requested sketch was not found."""


class UnknownRequestTypeError(APIError):
	"""The set request type is unknown."""
