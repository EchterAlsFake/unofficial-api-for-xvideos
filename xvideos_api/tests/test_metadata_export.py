import unittest

from xvideos_api.api import Video


class MetadataExportTests(unittest.TestCase):
    def test_cast_labels_and_no_comment_date(self):
        content = '''<h1>Example</h1><li class="model"><a href="/pornstars/example"><span class="name">Example Actor</span></a></li>
          <!-- dispo - Thursday, 01 October 2026 12:00:00 +0000 Loaded ! -->'''
        fields = Video._extract_html(content, "https://xvideos.com/video.abc/example")
        self.assertEqual(fields["performers"][0]["name"], "Example Actor")
        self.assertIsNone(fields["publish_date"])
        self.assertIsNone(fields["publish_date_source"])
