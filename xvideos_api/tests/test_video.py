import pytest
from base_api import DownloadConfigHLS

from ..api import Client, Channel

url = "https://de.xvideos.com/video.ohplvhk02fd/meine_lesbische_freundin_hat_mich_beim_fremdgehen_mit_einem_zufalligen_typen_erwischt_aber_ich_kann_nicht_aufhoren_und_ficke_ihn_weiter_vor_ihren_augen_"
# This URL will be used for all tests



@pytest.mark.asyncio
async def test_get_video():
    try:
        import av

    except:
        raise "Can not run without AV!"

    client = Client()
    video = await client.get_video(url)
    assert isinstance(video.title, str) and len(video.title) > 0
    assert isinstance(video.length, str) and len(video.length) > 0
    assert isinstance(video.views, str) and len(video.views) > 0
    assert isinstance(video.comment_count, str) and len(video.comment_count) > 0
    assert isinstance(video.likes, str) and len(video.likes) > 0
    assert isinstance(video.dislikes, str) and len(video.dislikes) > 0
    assert isinstance(video.rating_votes, str) and len(video.rating_votes) > 0
    assert isinstance(video.description, str) and len(video.description) > 0
    assert isinstance(video.tags, list) and len(video.tags) > 0
    assert isinstance(video.thumbnail_url, str) and len(video.thumbnail_url) > 0
    assert isinstance(video.preview_video_url, str) and len(video.preview_video_url) > 0
    assert isinstance(video.publish_date, str) and len(video.publish_date) > 0
    assert isinstance(video.content_url, str) and len(video.content_url) > 0
    assert isinstance(video.author_link, str) and len(video.author_link) > 0
    assert isinstance(video.pornstars_urls, list)
    assert isinstance(video.embed_url, str) and len(video.embed_url) > 0
    assert isinstance(video.m3u8_base_url, str) and len(video.m3u8_base_url) > 0

    author = await video.get_author
    assert isinstance(author.name, str)


    config_1 = DownloadConfigHLS(quality="worst", return_report=True, remux=True)
    config_2 = DownloadConfigHLS(quality="worst", return_report=True)

    result_1 = await video.download(config_1)
    result_2 = await video.download(config_2)

    assert result_1["status"] == "completed"
    assert result_2["status"] == "completed"