from scrapers.megamaxi import MegamaxiScraper
from scrapers.supermaxi import SupermaxiScraper
from scrapers.tia import TiaScraper
from scrapers.tuti import TutiScraper

SCRAPERS = {
    "tia": TiaScraper,
    "tuti": TutiScraper,
    "supermaxi": SupermaxiScraper,
    "megamaxi": MegamaxiScraper,
}
