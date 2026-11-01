from __future__ import annotations

from typing import Optional

from scrapers.woocommerce import WooCommerceSitemapScraper


class MegamaxiScraper(WooCommerceSitemapScraper):
    tienda = "megamaxi"

    def __init__(self, limit: Optional[int] = None, delay: Optional[float] = None):
        super().__init__("megamaxi", limit=limit, delay=delay)
