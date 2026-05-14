from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "readurl" / "scripts"))

import pagecopy_read  # noqa: E402


def test_localize_pagecopy_images_preserves_base_and_uses_file_urls(tmp_path):
    html_path = tmp_path / "snapshot.html"
    image_url = "https://mmbiz.qpic.cn/mmbiz_png/example/640?wx_fmt=png&from=appmsg"
    html_path.write_text(
        f"""
        <html>
          <head><base href="https://mp.weixin.qq.com/s/example"></head>
          <body>
            <img class="wx_img_placeholder" data-src="{image_url}" src="placeholder.gif">
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    def fake_download(url: str) -> tuple[bytes, str]:
        assert url == image_url
        return b"image-bytes", "image/png"

    result = pagecopy_read.localize_pagecopy_images(html_path, download=fake_download)

    fixed = Path(result["local_html_path"]).read_text(encoding="utf-8")
    assert '<base href="https://mp.weixin.qq.com/s/example">' in fixed
    assert 'src="file://' in fixed
    assert 'data-src="file://' in fixed
    assert "placeholder.gif" not in fixed
    assert Path(result["assets_dir"]).exists()
    assert result["downloaded_images"] == 1
    assert result["failed_images"] == 0
