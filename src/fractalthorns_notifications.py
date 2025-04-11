# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Code responsible for listening to and relaying SSE notifications."""

import asyncio
import json
import logging
from datetime import timedelta

import aiohttp
from aiohttp_sse_client2 import client as sse_client

import src.fractalthorns_dataclasses as ftd
from src.fractalrhomb_globals import bot, bot_data

notifs_logger = logging.getLogger("notifs")

BASE_RETRY_INTERVAL = timedelta(seconds=30)
MAX_RETRY_INTERVAL = timedelta(hours=1)

resume_event = asyncio.Event()


async def start_and_watch_notification_listener() -> None:
	"""Start the notification listener and watch for exceptions."""
	while True:
		listener_task = asyncio.create_task(listen_for_notifications())
		await asyncio.wait([listener_task], return_when=asyncio.FIRST_EXCEPTION)

		if listener_task.cancelled():
			notifs_logger.warning("SSE listener was cancelled.")
		elif (listener_exception := listener_task.exception()) is not None:
			notifs_logger.warning(
				'SSE listener failed with %s "%s", the client will need to be manually restarted.',
				type(listener_exception),
				listener_exception,
			)

		notifs_logger.info("SSE listener stopped. Waiting to be manually resumed.")
		await resume_event.wait()

		notifs_logger.info("SSE listener is resuming.")
		resume_event.clear()


async def listen_for_notifications() -> None:
	"""Listen for notifications and send them to the handler."""
	retry_interval = BASE_RETRY_INTERVAL

	while True:
		notifs_logger.info("Trying to connect to sse endpoint.")
		try:
			# change this path to /notifications-test to get test messages
			async with sse_client.EventSource(
				"https://fractalthorns.com/notifications", timeout=None
			) as event_source:
				# Yes, you are reading that correctly. I just passed timeout=None to a SSE client.
				# Guess what happens if you don't? The request times out after 5 minutes, as is the aiohttp default.
				#
				# https://github.com/rtfol/aiohttp-sse-client/issues/161
				# WHAT
				#      THE
				#           FUCK
				#
				# How does something like this even happen??? HOW IS IT STILL NOT FIXED???
				# Oh no, it's cool, my other car is a graphics library that can only draw one triangle at a time.
				retry_interval = BASE_RETRY_INTERVAL
				async for event in event_source:
					await handle_notification(event)

		except (aiohttp.ClientPayloadError, ConnectionError) as ex:
			# This SSE client does have its own retry logic, but it will only retry on certain very specific failures.
			# These two exception types cover the most common reasons the connection might fail, those being:
			# 1) the server is entirely down, or
			# 2) the backend is down and spitting 400s or 500s
			# Neither of these are automatically retried by the client and have to be picked up by us.
			notifs_logger.warning(
				'Lost connection to SSE server because of %s "%s", trying again in %s seconds.',
				type(ex),
				ex,
				retry_interval.total_seconds(),
			)

			await asyncio.sleep(retry_interval.total_seconds())

			retry_interval *= 2
			retry_interval = min(retry_interval, MAX_RETRY_INTERVAL)

		except TimeoutError:
			# Even though I asked it for no timeout, aiohttp may still be unhappy with
			# leaving a single GET request open for a week. So just in case...
			notifs_logger.warning("SSE client timed out, reconnecting...")


async def handle_notification(notification: sse_client.MessageEvent) -> None:
	"""Determine type of notification and send to relevant handler."""
	notifs_logger.info("Caught an SSE notification: %s.", notification)
	body = notification.data

	if "/" not in body:
		notifs_logger.info("SSE notification is missing a type delimiter! Ignoring.")
		return

	notification_type, payload = body.split("/", maxsplit=1)
	notifs_logger.info("Type: %s.", notification_type)

	match notification_type:
		case "news_update":
			news_item = ftd.NewsEntry.from_obj(json.loads(payload))
			await post_news_update(news_item)
		case _:
			notifs_logger.info(
				"SSE notification had an unknown type: %s.", notification_type
			)


async def post_news_update(news_item: ftd.NewsEntry) -> None:
	"""Post a news update in predefined news channels."""
	news_channels = bot_data.news_post_channels

	if len(news_channels) == 0:
		notifs_logger.warning(
			"Wanted to post a notification, but no update channels are configured!"
		)

	for channel in news_channels:
		notifs_logger.info("Posting a news update.")

		discord_channel = bot.get_channel(int(channel))
		await discord_channel.send(news_item.format())
