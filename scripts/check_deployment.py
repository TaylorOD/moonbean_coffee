"""Check the published site and API. --ask spends one chat request."""
import argparse
from html.parser import HTMLParser

import httpx

from scripts.evaluate import request_answer


class AskPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.api_url = None
        self.has_composer = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "ask":
            self.api_url = attrs.get("data-api-url")
        if tag == "form" and attrs.get("id") == "composer":
            self.has_composer = True


def check_site(html, api_url):
    page = AskPage()
    page.feed(html)
    if not page.has_composer:
        raise ValueError("The published home page is not Ask yet")
    if (page.api_url or "").rstrip("/") != api_url.rstrip("/"):
        raise ValueError("The published site has a missing or different API_URL")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="https://www.taylordorsett.com/moonbean_coffee/")
    parser.add_argument("--api-url", default="https://moonbean-api.onrender.com")
    parser.add_argument("--ask", action="store_true")
    args = parser.parse_args()
    try:
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            site = client.get(args.site)
            site.raise_for_status()
            check_site(site.text, args.api_url)
            print("Published Ask page points to the expected API")
            health = client.get(f"{args.api_url.rstrip('/')}/healthz")
            health.raise_for_status()
            if health.text.strip() != "ok":
                raise ValueError("The API health response was unexpected")
            print("API process is healthy (this does not test provider credentials)")
            if args.ask:
                answer, sources = request_answer(client, args.api_url, {"question": "What happens on Float Day?"})
                if "The River" not in sources or "noon" not in answer.lower():
                    raise ValueError("The live answer did not include the expected fact and source")
                print("Live answer includes the expected Float Day fact and handbook source")
    except (httpx.HTTPError, ValueError, RuntimeError) as error:
        # HTTP exception bodies can contain provider details. Keep the output narrow.
        print(f"Check failed: {error if isinstance(error, ValueError) else type(error).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
