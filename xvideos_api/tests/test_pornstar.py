import pytest
from ..api import Client
from base_api.modules.config import IteratorConfig



@pytest.mark.asyncio
async def test_pornstar():
    client = Client()
    pornstar = await client.get_pornstar("https://de.xvideos.com/pornstars/sweetie-fox1")

    assert isinstance(pornstar.total_videos, int)
    assert isinstance(pornstar.total_pages, int)
    assert isinstance(pornstar.name, str) and len(pornstar.name) >= 3
    assert isinstance(pornstar.thumbnail_url, str) and len(pornstar.thumbnail_url) >= 3
    assert isinstance(pornstar.per_page, int)
    assert isinstance(pornstar.gender, str)
    assert isinstance(pornstar.profile_hits, str)
    assert isinstance(pornstar.total_videos_views, str)
    assert isinstance(pornstar.signed_up, str)
    assert isinstance(pornstar.last_activity, (str, type(None)))
    assert isinstance(pornstar.video_tags, str)
    assert isinstance(pornstar.subscribers, str)
    assert isinstance(pornstar.worked_for_with_links, list)

    for channel in await pornstar.worked_for_with():
        assert isinstance(channel.name, str)

    idx = 0
    iterator_config = IteratorConfig(
        max_item_concurrency=1,
        max_page_concurrency=1,
        load_specific_sources=("html",),
    )
    async for result in pornstar.videos(iterator_config=iterator_config):
        video = result.unwrap()
        assert isinstance(video.title, str) and len(video.title) >= 3
        idx += 1
        if idx == 3:
            break


def test_pornstar_extract_html():
    from ..api import Pornstar

    html_content = """<div id="main">
<div id="profile-title" class="banner-sliders">
<div class="profile-infos">
<div>
<div class="profile-pic">
<picture class="no-box">
<source srcset="https://profile-gcore.xvideos-cdn.com/fdcb4d6a-c747-4708-9fed-ca7eae1c6aa1/0/pp_big.avif" type="image/avif">
<img src="https://profile-gcore.xvideos-cdn.com/fdcb4d6a-c747-4708-9fed-ca7eae1c6aa1/0/pp_big.jpg?secure=test" onerror="this.src='default.jpg';">
</picture>
</div>
<h2>
<span class="flag flag-ru mobile-hide"></span>
<strong class="text-danger">Sweetie Fox</strong>
<small class="mobile-hide">Weiblich, Porno-Darstellerin</small>
<span class="mobile-show-inline">
<small class="mobile-only-hide"><span class="mobile-hide">1.342.873.617</span> Video-Views</small>
</span>
</h2>
</div>
</div>
</div>
<div id="tabAboutMe" class="tab">
<p id="pinfo-sex"><strong>Geschlecht:</strong><span>Weiblich</span></p>
<p id="pinfo-profile-hits"><strong>Profilaufrufe:</strong><span>14.899.776</span></p>
<p id="pinfo-subscribers"><strong>Subscribers:</strong><span>1.313.953</span></p>
<p id="pinfo-videos-views"><strong>Total Videoaufrufe:</strong><span>1.342.873.617</span></p>
<p id="pinfo-signedup"><strong>Angemeldet:</strong><span>24. August 2023 (vor 1.117 Tagen)</span></p>
<p id="pinfo-lastactivity"><strong>Zuletzt ausgeführte Aktivität:</strong><span><a id="goto-activity">vor 9 Tagen</a></span></p>
<p id="pinfo-workedfor"><strong>Funktioniert bei / mit:</strong><span><a href="/profiles/sweetie_fox_official" class="text-danger">Sweetie Fox</a>, <a href="/profiles/mofos-network" class="text-danger">Mofos</a></span></p>
<p id="pinfo-video-tags"><strong>Sweetie Fox wurde am meisten markiert:</strong><span><small>amateur (633), blowjob (596)</small></span></p>
</div>
</div>"""
    base_json = '{"nb_videos": 588, "nb_per_page": 24}'
    data = Pornstar._extract_data(html_content, base_json)
    assert data["name"] == "Sweetie Fox"
    assert "pp_big.jpg" in data["thumbnail_url"]
    assert data["total_videos"] == 588
    assert data["per_page"] == 24
    assert data["total_pages"] == 25
    assert data["profile_hits"] == "14.899.776"
    assert data["subscribers"] == "1.313.953"
    assert data["total_videos_views"] == "1.342.873.617"
    assert data["signed_up"] == "24. August 2023 (vor 1.117 Tagen)"
    assert data["last_activity"] == "vor 9 Tagen"
    assert "/profiles/sweetie_fox_official" in data["worked_for_with_links"]
    assert data["gender"] == "Weiblich"
    assert data["age"] is None
    assert "amateur (633)" in data["video_tags"]


def test_pornstar_extract_age():
    from ..api import Pornstar

    html_header_age = """<h2><strong class="text-danger">Lia Lin</strong><small class="mobile-hide">Weiblich, Porno-Darstellerin, 25y</small></h2>"""
    data = Pornstar._extract_data(html_header_age, "")
    assert data["name"] == "Lia Lin"
    assert data["age"] == "25"

    html_pinfo_age = """<h2><strong class="text-danger">Lia Lin</strong></h2><p id="pinfo-age"><span>26</span></p>"""
    data2 = Pornstar._extract_data(html_pinfo_age, "")
    assert data2["age"] == "26"
