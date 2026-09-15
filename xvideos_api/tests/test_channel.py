import pytest
from ..api import Client


@pytest.mark.asyncio
async def test_channel():
    client = Client()
    channel = await client.get_channel("https://de.xvideos.com/teddy_tarantino")

    assert isinstance(channel.name, str)
    assert isinstance(channel.thumbnail_url, str)
    assert isinstance(channel.total_pages, int)
    assert isinstance(channel.per_page, int)
    assert isinstance(channel.total_videos, int)
    assert isinstance(channel.profile_hits, str)
    assert isinstance(channel.subscribers, str)
    assert isinstance(channel.signed_up, str)
    assert isinstance(channel.last_activity, (str, type(None)))
    assert isinstance(channel.total_videos_views, str)
    assert isinstance(channel.worked_for_with_links, list)

    for thing in await channel.worked_for_with():
        assert isinstance(thing.name, str)

    idx = 0
    async for result in channel.videos():
        idx += 1
        assert isinstance(result.unwrap().title, str)

        if idx >= 3:
            break


def test_channel_extract_html():
    from ..api import Channel

    html_content = """<div id="page">
<div id="main">
<div class="profile-infos">
<div>
<div class="profile-pic">
<picture class="no-box">
<img src="https://profile-gcore.xvideos-cdn.com/3dc29000-17e9-45f8-8a23-ea98ced67f5f/0/pp_big.jpg?secure=wdz_A09J4ahEy6pwLQ7PTA==,1789466777">
</picture>
</div>
<h2 class="with-aka">
<strong class="text-danger">SCOUT69official</strong>
<span class="mobile-show-inline">
<small class="mobile-only-hide"><span class="mobile-hide">8.883.103.159</span> Video-Views</small>
</span>
<div class="user-actions">
<span class="user-subscribe sub-strip"><span class="count">1,1M</span></span>
</div>
</h2>
</div>
</div>
<div id="profile-tabs">
<ul class="xv-slim-tabs">
<li><a id="tab-videos"><span> Videos</span><span class="count">14.990</span></a></li>
</ul>
</div>
<div id="tabAboutMe">
<p id="pinfo-profile-hits"><span>25.000.000</span></p>
<p id="pinfo-signedup"><span>1. Januar 2020</span></p>
<p id="pinfo-workedfor"><span><a href="/profiles/scout69_official">Scout</a></span></p>
</div>
</div>
</div>"""
    base_json = '{"nb_videos": 14990, "nb_per_page": 24}'
    data = Channel._extract_data(html_content, base_json)
    assert data["name"] == "SCOUT69official"
    assert "pp_big.jpg" in data["thumbnail_url"]
    assert data["total_videos"] == 14990
    assert data["subscribers"] == "1,1M"
    assert data["total_videos_views"] == "8.883.103.159"
    assert "/profiles/scout69_official" in data["worked_for_with_links"]


def test_channel_extract_lifeselector():
    from ..api import Channel

    html_content = """<div id="page">
<div id="main">
<div class="profile-infos">
<div>
<div class="profile-pic">
<picture class="no-box">
<source srcset="https://profile-cdn77.xvideos-cdn.com/6ca88e30-c752-4f9e-a26b-2b50afb298f9/3/pp_big.avif" type="image/avif">
<img src="https://profile-cdn77.xvideos-cdn.com/6ca88e30-c752-4f9e-a26b-2b50afb298f9/3/pp_big.jpg" onerror="this.src='default.jpg';">
</picture>
</div>
<h2>
<span class="flag flag-ch mobile-hide" title="Schweiz"></span>
<strong class="text-danger">Life Selector</strong>
<span class="flag flag-ch mobile-show-inline-block" title="Schweiz"></span>
<br class="mobile-hide">
<small class="mobile-hide">Kanal</small>
<span class="mobile-show-inline">
<br>
<small class="mobile-only-hide"><span class="mobile-hide">1.386.436.547</span><span class="mobile-show-inline">1,4B</span> Video-Views</small>
</span>
<span class="mobile-show-inline-block mobile-user-actions">
<span class="user-subscribe sub-strip"><span class="count">511,4k</span></span>
</span>
</h2>
</div>
</div>
<div id="profile-tabs">
<ul class="xv-slim-tabs">
<li class=""><a class="xv-slim-tab-btn tab-button" id="tab-videos" title="Videos"><span> Videos</span><span class="count">1.547</span></a></li>
</ul>
</div>
</div>
</div>"""
    data = Channel._extract_data(html_content, "")
    assert data["name"] == "Life Selector"
    assert "pp_big.jpg" in data["thumbnail_url"]
    assert data["total_videos"] == 1547
    assert data["subscribers"] == "511,4k"
    assert data["total_videos_views"] == "1.386.436.547"
