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


HTML_SNIPPET = """<div id="page" class="video-page">
<div id="main">
<!-- dispo - Tue, 15 Sep 26 06:53:32 +0000 Loaded ! Video exists and loaded. Video exists and OK. -->
<div id="ad-header-mobile-contener"></div>
<h2 class="page-title"><span class="icon-f icf-refresh" id="title-auto-tr-switch" title="Dieser Titel wurde automatisch übersetzt. Klicken Sie, um auf den ursprünglichen Titel zu wechseln."></span><span id="title-auto-tr">Atemberaubende Latina-Schönheit spritzt im Uber und der Fahrer wird klatschnass!</span> <span class="duration">10  Min</span><span class="video-hd-mark">1440p</span></h2>
<div class="video-metadata video-tags-list ordered-label-list cropped"><ul><li class="main-uploader"><a href="/maximo_pov" class="btn btn-default label main uploader-tag hover-name"><span class="name"><span class="icon-f icf-device-tv-v2"></span> Maximo POV</span><span class="user-subscribe sub-checked" data-user-id="502490093" data-user-profile="maximo_pov" title="Anmelden" style="display: inline-block;"><span class="count">135k</span></span></a></li><li class="model"><a href="/pornstars/maximo_garcia1" class="btn btn-default label profile hover-name is-pornstar" data-id="789643015"><span class="model-star-sub icon-f icf-star-o" data-user-id="789643015" data-user-profile="maximo_garcia1"></span><span class="name">Maximo Garcia</span><span class="user-subscribe sub-checked" data-user-id="789643015" data-user-profile="maximo_garcia1" title="Anmelden" style="display: inline-block;"><span class="count">560k</span></span></a></li><li class="model"><a href="/models/baby-nicols" class="btn btn-default label profile hover-name is-pornstar" data-id="234560981"><span class="model-star-sub icon-f icf-star-o" data-user-id="234560981" data-user-profile="baby-nicols"></span><span class="name">Baby Nicols</span><span class="user-subscribe sub-checked" data-user-id="234560981" data-user-profile="baby-nicols" title="Anmelden" style="display: inline-block;"><span class="count">161k</span></span></a></li>
<li><a href="/tags/blonde" class="is-keyword btn btn-default">blonde</a></li><li><a href="/tags/sexy" class="is-keyword btn btn-default">sexy</a></li><li><a href="/tags/babe" class="is-keyword btn btn-default">babe</a></li><li><a href="/tags/pornstar" class="is-keyword btn btn-default">pornstar</a></li><li><a href="/tags/blowjob" class="is-keyword btn btn-default">blowjob</a></li><li><a href="/tags/homemade" class="is-keyword btn btn-default">homemade</a></li><li><a href="/tags/beauty" class="is-keyword btn btn-default">beauty</a></li><li><a href="/tags/stud" class="is-keyword btn btn-default">stud</a></li><li><a href="/tags/sloppy" class="is-keyword btn btn-default">sloppy</a></li><li><a href="/tags/1-on-1" class="is-keyword btn btn-default">1-on-1</a></li><li><a href="/tags/natural-tits" class="is-keyword btn btn-default">natural-tits</a></li><li style="display: inline-block; visibility: visible;"><a href="#" class="suggestion" id="metadata_suggestion_popup_opener" title="Tags bearbeiten"><span class="icon-f icf-pencil"></span><span class="hidden-sm hidden-xs">Tags bearbeiten</span></a></li><li class="view-more-li" style="display: inline-block; visibility: visible;"><a href="#" class="view-more btn btn-default" title="weitere Tags">+</a></li><li><a href="/tags/real-orgasm" class="is-keyword btn btn-default">real-orgasm</a></li><li><a href="/tags/bwc" class="is-keyword btn btn-default">bwc</a></li><li><a href="/tags/beautiful-face" class="is-keyword btn btn-default">beautiful-face</a></li><li><a href="/tags/long-cock" class="is-keyword btn btn-default">long-cock</a></li><li><a href="/tags/perfect-tits" class="is-keyword btn btn-default">perfect-tits</a></li><li><a href="/tags/pretty-face" class="is-keyword btn btn-default">pretty-face</a></li><li><a href="/tags/wet-blowjob" class="is-keyword btn btn-default">wet-blowjob</a></li><li><a href="/tags/muscular-body" class="is-keyword btn btn-default">muscular-body</a></li><li><a href="/tags/muscular-guy" class="is-keyword btn btn-default">muscular-guy</a></li>
</ul></div>						
<div id="content">
<div id="video-right" class="mobile-hide"></div>
<div id="video-player-bg" class="ignore-popunder">
<script>
	    html5player.setVideoTitle('Atemberaubende Latina-Sch&ouml;nheit spritzt im Uber und der Fahrer wird klatschnass!');
	    html5player.setEncodedIdVideo('omvalmpbc78');
	    html5player.setThumbUrl('https://thumb-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/xv_15_t.jpg');
	    html5player.setVideoUrlLow('https://mp4-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/mp4_sd.mp4?secure=TKYSucHH9LlbuYz31I_lXA==,1789467477');
	    html5player.setVideoUrlHigh('https://mp4-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/mp4_sd.mp4?secure=TKYSucHH9LlbuYz31I_lXA==,1789467477');
	    html5player.setVideoHLS('https://hls-cdn77.xvideos-cdn.com/5cW89fA4I11OGR1_MShHzg==,1789467477/18559893-5132-44e5-8df9-ea51e568a9a3/6/hls.m3u8');
	    html5player.setThumbUrl169('https://thumb-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/xv_6_p.avif');
	    html5player.setThumbSlide('https://thumb-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/mozaique_listing.jpg');
	    html5player.setThumbSlideBig('https://thumb-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/mozaique_full.jpg');
	    html5player.setThumbSlideMinute('https://thumb-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/mozaiquemin_NUM.avif');
	    html5player.setUploaderName('maximo_pov');
	    html5player.setVideoURL('/video.omvalmpbc78/atemberaubende_latina-schonheit_spritzt_im_uber_und_der_fahrer_wird_klatschnass_');
</script>
</div>
</div>
<div id="v-views"><span class="icon-f icf-eye"></span><strong class="mobile-hide">25.827</strong><strong class="mobile-show-inline">26k</strong></div>
<div class="rate-infos"><span class="rating-total-txt">38 Stimmen</span><div class="nbr"><span><span class="rating-good-nbr">28</span><span class="icon-f icf-thumb-up"></span></span><span><span class="rating-bad-nbr">10</span><span class="icon-f icf-thumb-down"></span></span></div></div>
<div class="tabs"><button class="comments tab-button"><span><span class="badge">1</span><span class="icon-f icf-comment-o"></span></span><span>Kommentare</span></button></div>
<div class="copy-link force-one-line"><input id="copy-video-embed" type="text" readonly="" value="&lt;iframe src=&quot;https://de.xvideos.com/embedframe/omvalmpbc78&quot; frameborder=0 width=510 height=400 scrolling=no allowfullscreen=allowfullscreen&gt;&lt;/iframe&gt;" class="form-control"></div>
</div>"""


def test_video_extract_html():
    from ..api import Video

    data = Video._extract_html(HTML_SNIPPET)
    assert data["title"] == "Atemberaubende Latina-Schönheit spritzt im Uber und der Fahrer wird klatschnass!"
    assert data["length"] == "10  Min"
    assert data["views"] == "25.827"
    assert data["likes"] == "28"
    assert data["dislikes"] == "10"
    assert data["rating_votes"] == "38 Stimmen"
    assert data["comment_count"] == "1"
    assert data["author_link"] == "https://xvideos.com/maximo_pov"
    assert data["pornstars_urls"] == [
        "https://xvideos.com/pornstars/maximo_garcia1",
        "https://xvideos.com/models/baby-nicols",
    ]
    assert data["thumbnail_url"] == "https://thumb-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/xv_15_t.jpg"
    assert data["preview_video_url"] == "https://thumb-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/preview.mp4"
    assert data["publish_date"] == "Tue, 15 Sep 26 06:53:32 +0000"
    assert data["content_url"] == "https://mp4-cdn77.xvideos-cdn.com/18559893-5132-44e5-8df9-ea51e568a9a3/6/mp4_sd.mp4?secure=TKYSucHH9LlbuYz31I_lXA==,1789467477"
    assert data["m3u8_base_url"] == "https://hls-cdn77.xvideos-cdn.com/5cW89fA4I11OGR1_MShHzg==,1789467477/18559893-5132-44e5-8df9-ea51e568a9a3/6/hls.m3u8"
    assert "https://de.xvideos.com/embedframe/omvalmpbc78" in data["embed_url"]
    assert "blonde" in data["tags"]
    assert len(data["tags"]) == 20