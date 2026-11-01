from __future__ import annotations

from typing import Optional

from scrapers.woocommerce import WooCommerceSitemapScraper


class SupermaxiScraper(WooCommerceSitemapScraper):
    tienda = "supermaxi"

    def __init__(self, limit: Optional[int] = None, delay: Optional[float] = None):
        super().__init__("supermaxi", limit=limit, delay=delay)
