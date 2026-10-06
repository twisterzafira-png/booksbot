# -*- coding: utf-8 -*-
import re
from urllib.parse import urlparse, urldefrag

import scrapy
from scrapy.linkextractors import LinkExtractor


class WebResearchSpider(scrapy.Spider):
    name = "webresearch"

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DEPTH_LIMIT": 4,
        "CLOSESPIDER_PAGECOUNT": 250,
        "USER_AGENT": "H334D-WebResearch/1.0 (+Scrapy Cloud)",
    }

    def __init__(self, url=None, max_pages=250, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not url:
            raise ValueError("Informe a URL com -a url=https://exemplo.com")

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        self.start_urls = [url]
        self.allowed_host = urlparse(url).netloc.lower().split(":")[0]
        self.max_pages = int(max_pages)
        self.pages_seen = 0
        self.link_extractor = LinkExtractor(unique=True)

    def parse(self, response):
        if self.pages_seen >= self.max_pages:
            return

        self.pages_seen += 1

        content_type = response.headers.get(
            "Content-Type", b""
        ).decode("latin1").lower()

        if "text/html" not in content_type:
            return

        title = response.css("title::text").get()
        description = response.css(
            'meta[name="description"]::attr(content)'
        ).get()

        h1 = response.css("h1 *::text, h1::text").getall()

        text_parts = response.css(
            "main ::text, article ::text, [role='main'] ::text, body ::text"
        ).getall()

        text = " ".join(" ".join(text_parts).split())

        if len(text) > 50000:
            text = text[:50000]

        price_pattern = re.compile(
            r"(?:R\$|US\$|\$|€|£)\s?\d[\d\.\,]*(?:\s?(?:mil|k))?",
            re.I,
        )

        prices = []

        for match in price_pattern.findall(text):
            if match not in prices:
                prices.append(match)

            if len(prices) >= 30:
                break

        yield {
            "url": response.url,
            "status": response.status,
            "title": title.strip() if title else None,
            "description": description.strip() if description else None,
            "h1": " ".join(" ".join(h1).split()) or None,
            "prices": prices,
            "text": text,
        }

        for link in self.link_extractor.extract_links(response):
            clean_url, _ = urldefrag(link.url)
            host = urlparse(clean_url).netloc.lower().split(":")[0]

            if host == self.allowed_host or host.endswith(
                "." + self.allowed_host
            ):
                yield response.follow(clean_url, callback=self.parse)
