"""Closing a profile generator must finish its native scraper cleanup."""
import unittest
from unittest.mock import AsyncMock, patch

from xvideos_api import api


class ProfileCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_early_close_waits_for_inner_stream_cleanup(self):
        closed = []

        async def native_stream():
            try:
                yield "first"
                yield "second"
            finally:
                closed.append(True)

        profile = api.Channel(url="https://www.xvideos.com/channels/example", core=object())
        with patch.object(api, "scrape_stream", return_value=native_stream()), \
             patch.object(api.Channel, "get_field", AsyncMock(return_value=2)):
            stream = profile.videos(pages=2)
            self.assertEqual(await anext(stream), "first")
            await stream.aclose()
            self.assertEqual(closed, [True])
