"""Uploader display metadata belongs to the video page, not a statistics feed."""
import unittest

from xvideos_api.api import Video


class VideoUploaderTests(unittest.TestCase):
    def test_uploader_name_excludes_subscription_count(self):
        data = Video._extract_html('''<li class="main-uploader">
          <a href="/channels/example"><span class="name"><span class="icon"></span> Studio 日本語</span>
          <span class="user-subscribe"><span class="count">197k</span></span></a></li>''')
        self.assertEqual(data["author_name"], "Studio 日本語")
        self.assertEqual(data["author_link"], "https://xvideos.com/channels/example")

    def test_absent_uploader_is_explicitly_unavailable(self):
        data = Video._extract_html("<h2>Example video</h2>")
        self.assertIsNone(data["author_name"])
        self.assertIsNone(data["author_link"])
