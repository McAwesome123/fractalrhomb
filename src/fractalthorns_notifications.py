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
import re
from os import getenv
from datetime import timedelta

from aiohttp_sse_client2 import client as sse_client

from src.fractalrhomb_globals import bot

notifs_logger = logging.getLogger("discord")

BASE_RETRY_INTERVAL = timedelta(seconds=30)
MAX_RETRY_INTERVAL = timedelta(hours=1)

async def listen_for_notifications() -> None:
    retry_interval = BASE_RETRY_INTERVAL

    while True:
        notifs_logger.info(f'trying to connect to sse endpoint')
        try:
            async with sse_client.EventSource('http://localhost:4321/notifications-test') as event_source:
                async for event in event_source:
                    await handle_notification(event)
                    retry_interval = BASE_RETRY_INTERVAL

        except (ClientPayloadError, ConnectionError) as ex:
            # This SSE client does have its own retry logic, but it will only 
            # retry on certain very specific failures.
            # These two exception types cover the most common reasons the connection
            # might fail - those being 1) the server is entirely down or
            # 2) it is broken and spitting 400s or 500s - which are NOT
            # automatically retried by the client and have to be picked up
            # by us.
            notifs_logger.warning(f'couldn\'t connect to the sse server because of {type(ex)=} "{ex=}", trying again in {retry_interval.total_seconds()} seconds')

            await asyncio.sleep(retry_interval.total_seconds())

            retry_interval *= 2
            retry_interval = MAX_RETRY_INTERVAL if retry_interval > MAX_RETRY_INTERVAL else retry_interval

        except Exception as ex: 
            notifs_logger.warning(f'unknown exception when connecting to see server {type(ex)=} "{ex=}", the client will need to be manually restarted')
            raise

        
async def handle_notification(notification):
    notifs_logger.info(f'caught a sse notification: {notification}')
    body = notification.data

    if '/' not in body:
        notifs_logger.info(f'sse notification is missing a type delimiter! ignoring')
        return

    notification_type, payload = body.split('/', maxsplit=1)
    notifs_logger.info(f'type: {notification_type}')

    match notification_type:
        case 'news_update':
            await post_news_update(json.loads(payload))
        case _:
            notifs_logger.info(f'sse notification had an unknown type: {notification_type}')

async def post_news_update(news_item):
    news_channels = json.loads(getenv("NEWS_UPDATE_POST_CHANNELS", "[]"))

    if len(news_channels) == 0:
        notifs_logger.warning(f'wanted to post a notification, but no update channels are configured!')

    for channel in news_channels:
        notifs_logger.info(f'posting a news update')

        discord_channel = bot.get_channel(int(channel))
        await discord_channel.send(make_news_update_string(news_item))

def make_news_update_string(news_item):
    # This is 100% going to cause a problem later, but YOLO
    strip_html_tags = lambda s: re.sub('<[^<]+?>', '', s)

    string = (
        f'**fractalthorns update for** {news_item['date']}\n'
        f'## {news_item['title']}\n'
        f'{"* " + "\n* ".join(map(strip_html_tags, news_item['items']))}'
    )

    return string
