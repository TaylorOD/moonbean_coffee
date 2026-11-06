import pytest

from scripts.check_deployment import check_site


def test_old_homepage_is_not_a_successful_deployment():
    with pytest.raises(ValueError, match="not Ask"):
        check_site('<h1>Moonbean</h1>', 'https://api.example.com')


def test_missing_or_wrong_api_address_is_detected():
    for value in ['', 'https://wrong.example.com']:
        with pytest.raises(ValueError, match="API_URL"):
            check_site(f'<main id="ask" data-api-url="{value}"><form id="composer"></form></main>',
                       'https://api.example.com')


def test_connected_homepage_passes():
    check_site('<main id="ask" data-api-url="https://api.example.com/"><form id="composer"></form></main>',
               'https://api.example.com')
