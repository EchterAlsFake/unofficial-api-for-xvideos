import pytest
from ..api import Client


cookies_placeholder = {
    "session_token": "",
    "session_token_auth": ""
}

@pytest.mark.asyncio
async def test_account_methods():
    client = Client()
    account = client.get_account(cookies=cookies_placeholder)

    # Test recommended videos
    idx = 0
    async for result in account.get_recommended_videos(pages=1, videos_concurrency=1, pages_concurrency=1):
        assert isinstance(result.video.title, str)
        idx += 1
        if idx >= 3:
            break
# Test liked videos
    idx = 0
    async for result in account.get_liked_videos(pages=1, videos_concurrency=1, pages_concurrency=1):
        assert isinstance(result.video.title, str)
        idx += 1
        if idx >= 3:
            break

    # Test watch later videos
    idx = 0
    async for result in account.get_watch_later_videos(pages=1, videos_concurrency=1, pages_concurrency=1):
        assert isinstance(result.video.title, str)
        idx += 1
        if idx >= 3:
            break
