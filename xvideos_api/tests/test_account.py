import pytest
from ..api import Client
from base_api.modules.config import IteratorConfig


cookies_placeholder = {
    "session_token": "",
    "session_token_auth": ""
}

@pytest.mark.asyncio
async def test_account_methods():
    client = Client()
    account = client.get_account(cookies=cookies_placeholder)
    iterator_config = IteratorConfig(
        max_item_concurrency=1,
        max_page_concurrency=1,
        load_specific_sources=("html",),
        _page_request_method="POST",
    )

    # Test recommended videos
    idx = 0
    async for result in account.get_recommended_videos(pages=1, iterator_config=iterator_config):
        assert isinstance(result.unwrap().title, str)
        idx += 1
        if idx >= 3:
            break
# Test liked videos
    idx = 0
    async for result in account.get_liked_videos(pages=1, iterator_config=iterator_config):
        assert isinstance(result.unwrap().title, str)
        idx += 1
        if idx >= 3:
            break

    # Test watch later videos
    idx = 0
    async for result in account.get_watch_later_videos(pages=1, iterator_config=iterator_config):
        assert isinstance(result.unwrap().title, str)
        idx += 1
        if idx >= 3:
            break
