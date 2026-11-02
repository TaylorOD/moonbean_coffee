import re

import pytest

from scripts import build_site
from scripts.build_site import DIST, build


@pytest.fixture(scope="module")
def site():
    build("https://api.example.com")
    return {name: (DIST / name).read_text(encoding="utf-8") for name in build_site.PAGES}


def test_every_page_builds(site):
    assert set(site) == {"index.html", "handbook.html", "ask.html"}


def test_links_are_relative_so_previews_work(site):
    for page in site.values():
        assert not re.search(r'(href|src)="/', page)


def test_every_local_file_exists(site):
    for page in site.values():
        for path in re.findall(r'(?:href|src)="(static/[^"]+)"', page):
            assert (DIST / path).exists(), path


def test_csp_only_allows_the_api(site):
    for page in site.values():
        assert "connect-src https://api.example.com;" in page


def test_handbook_has_an_anchor_for_every_section(site):
    for slug in re.findall(r'<a href="#([^"]+)"', site["handbook.html"]):
        assert f'id="{slug}"' in site["handbook.html"]
