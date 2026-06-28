from ..api import Client, DownloadConfigHLS
import pytest

client = Client()

url_1 = "https://de.xvideos.com/video.ohplvhk02fd/meine_lesbische_freundin_hat_mich_beim_fremdgehen_mit_einem_zufalligen_typen_erwischt_aber_ich_kann_nicht_aufhoren_und_ficke_ihn_weiter_vor_ihren_augen_"
url_2 = "https://de.xvideos.com/video.ohplvhk02fd/meine_lesbische_freundin_hat_mich_beim_fremdgehen_mit_einem_zufalligen_typen_erwischt_aber_ich_kann_nicht_aufhoren_und_ficke_ihn_weiter_vor_ihren_augen_"

config_1 = DownloadConfigHLS(quality="worst", return_report=True)
config_2 = DownloadConfigHLS(quality="worst", return_report=True, remux=True)

@pytest.mark.asyncio
async def test_download_high():
    video_1 = await client.get_video(url_1)
    video_2 = await client.get_video(url_2)
    stuff_1 = await video_1.download(config_1)
    stuff_2 = await video_2.download(config_2)
    assert stuff_1["status"] == "completed"
    assert stuff_2["status"] == "completed"

