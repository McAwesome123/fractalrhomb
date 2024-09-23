# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Code responsible for listening to and relaying SSE notifications."""

import json
import logging
import re
from os import getenv

from aiohttp_sse_client2 import client as sse_client

from src.fractalrhomb_globals import bot

notifs_logger = logging.getLogger("notifs")

async def listen_for_notifications() -> None:
    async with sse_client.EventSource('https://fractalthorns.com/notifications') as event_source:
        try:
            async for event in event_source:
                await handle_notification(event)
        except ConnectionError:
            pass

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
            pass

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
