"""Build one self-contained HTML file of the dashboard that opens in any browser, also offline.

Inlines data.json, the world map, d3, topojson, the Excel library and the fonts, so nothing is
fetched when the file is opened. "Kør nu" and "Omskriv med Claude" need Claude and stay hidden;
the Excel export becomes a normal browser download.

    python tools/standalone.py            # -> dist/ETA-tavlen.html
"""
import base64
import io
import json
import re
import sys
import tarfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboard"
# The page's CDN script tags -> the same file taken from the npm registry tarball (reachable where the CDNs are not).
LIBS = {
    "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js": ("d3", "7.9.0", "dist/d3.min.js"),
    "https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js":
        ("topojson-client", "3.1.0", "dist/topojson-client.min.js"),
}
XLSX = ("xlsx-js-style", "1.2.0", "dist/xlsx.bundle.js")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15"}


def get(client: httpx.Client, url: str) -> httpx.Response:
    r = client.get(url, headers=UA, follow_redirects=True, timeout=60)
    r.raise_for_status()
    return r


def npm_file(client: httpx.Client, pkg: str, version: str, path: str) -> str:
    tgz = get(client, f"https://registry.npmjs.org/{pkg}/-/{pkg}-{version}.tgz").content
    with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz") as tar:
        return tar.extractfile(f"package/{path}").read().decode("utf-8")


def inline_fonts(client: httpx.Client, html: str) -> str:
    m = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/[^"]+)">', html)
    if not m:
        return html
    css = get(client, m.group(1).replace("&amp;", "&")).text
    css = re.sub(r"url\((https://[^)]+)\)", lambda u: "url(data:font/woff2;base64,%s)"
                 % base64.b64encode(get(client, u.group(1)).content).decode(), css)
    html = html.replace(m.group(0), f"<style>{css}</style>")
    return re.sub(r'<link rel="preconnect"[^>]*>\n?', "", html)


def safe_script(js: str) -> str:
    return js.replace("</script", "<\\/script")


def build(out: Path) -> None:
    html = (DASH / "index.html").read_text(encoding="utf-8")
    data = json.loads((DASH / "data.json").read_text(encoding="utf-8"))
    land = json.loads((DASH / "land-110m.json").read_text(encoding="utf-8"))
    with httpx.Client() as client:
        for url, lib in LIBS.items():
            tag = f'<script src="{url}"></script>'
            assert tag in html, url
            html = html.replace(tag, f"<script>{safe_script(npm_file(client, *lib))}</script>")
        xlsx = npm_file(client, *XLSX)
        html = inline_fonts(client, html)
    embed = json.dumps({"data": data, "land": land}, ensure_ascii=False, separators=(",", ":"))
    head = (f"<script>window.__EMBED = {safe_script(embed)};</script>\n"
            f"<script>{safe_script(xlsx)}</script>\n")
    html = html.replace("</head>", head + "</head>", 1) if "</head>" in html else head + html
    if not html.lstrip().lower().startswith("<!doctype"):
        html = ('<!doctype html>\n<html lang="da">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                f"<title>ETA-tavlen</title>\n</head>\n<body>\n{html}\n</body>\n</html>\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"{out} skrevet ({out.stat().st_size / 1e6:.1f} MB, data fra {data.get('run_date')})")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "ETA-tavlen.html")
