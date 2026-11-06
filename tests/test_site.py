import re

import pytest

from scripts import build_site
from scripts.build_site import DIST, build


@pytest.fixture(scope="module")
def site():
    build("https://api.example.com")
    return {name: (DIST / name).read_text(encoding="utf-8") for name in build_site.PAGES}


def test_every_page_builds(site):
    assert set(site) == {"index.html", "about.html", "handbook.html", "ask.html"}


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


def test_story_stays_in_universe_until_the_fine_print(site):
    about = site["about.html"]
    before = about[: about.index('id="fine-print"')].lower()
    for word in ["demo", "project", "llm", "chatbot", "not real", "isn't real"]:
        assert word not in before
    assert "moonbean isn't real" in about[about.index('id="fine-print"') :].lower()


def test_homepage_is_ask_and_old_link_still_works(site):
    assert site["index.html"] == site["ask.html"]
    assert 'id="composer"' in site["index.html"]
    assert "Answers are based on the Beanhand handbook" in site["index.html"]
    assert 'href="about.html"' in site["index.html"]
    assert 'type="password"' not in site["index.html"]


def test_page_links_and_anchors_resolve(site):
    for filename, page in site.items():
        for href in re.findall(r'href="([^" ]+)"', page):
            if ":" in href or href.startswith("static/"):
                continue
            target, _, anchor = href.partition("#")
            target = target or filename
            assert target in site, href
            if anchor:
                assert f'id="{anchor}"' in site[target], href
