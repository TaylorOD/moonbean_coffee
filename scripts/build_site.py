"""Builds the static site into dist/ for GitHub Pages.

Run from the repo root: python -m scripts.build_site
Set API_URL to point the Ask page at the chat API.
"""
import os
import shutil
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.handbook import read_handbook, slugify, to_records

ROOT = Path(__file__).parent.parent
SITE = ROOT / "site"
DIST = ROOT / "dist"
PAGES = {"index.html": "about", "handbook.html": "handbook", "ask.html": "ask"}


def render_handbook(text):
    html = markdown.markdown(
        text, extensions=["toc"], extension_configs={"toc": {"slugify": slugify}}
    )
    toc = [{"title": r["section"], "slug": r["id"]} for r in to_records(text)]
    return html, toc


def build(api_url=""):
    env = Environment(
        loader=FileSystemLoader(SITE / "templates"), autoescape=select_autoescape(["html"])
    )
    html, toc = render_handbook(read_handbook())

    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(SITE / "static", DIST / "static")
    (DIST / ".nojekyll").touch()
    for filename, page in PAGES.items():
        template = env.get_template(filename)
        output = template.render(page=page, api_url=api_url, html=html, toc=toc)
        (DIST / filename).write_text(output, encoding="utf-8")


if __name__ == "__main__":
    build(os.getenv("API_URL", ""))
    print(f"Built {len(PAGES)} pages into dist/")
