import httpx
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class GlobalProductClients:
    def __init__(self):
        self.timeout = httpx.Timeout(5.0, connect=2.0)
        self.headers = {"User-Agent": "AllergyDetectorApp - Android - Version 1.0"}

    async def fetch_open_food_facts(self, barcode: str) -> Optional[Dict]:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        return await self._get(url, "OpenFoodFacts")

    async def fetch_open_beauty_facts(self, barcode: str) -> Optional[Dict]:
        url = f"https://world.openbeautyfacts.org/api/v2/product/{barcode}.json"
        return await self._get(url, "OpenBeautyFacts")

    async def fetch_open_fda(self, barcode: str) -> Optional[Dict]:
        # OpenFDA uses UPC or NDC
        url = f"https://api.fda.gov/drug/label.json?search=openfda.upc:{barcode}"
        return await self._get(url, "OpenFDA")

    async def fetch_upc_item_db(self, barcode: str) -> Optional[Dict]:
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
        return await self._get(url, "UPCitemDB")

    async def fetch_barcode_lookup(self, barcode: str) -> Optional[Dict]:
        key = os.getenv("BARCODELOOKUP_KEY")
        if not key: return None
        url = f"https://api.barcodelookup.com/v3/products?barcode={barcode}&key={key}"
        return await self._get(url, "BarcodeLookup")

    async def fetch_spoonacular(self, barcode: str) -> Optional[Dict]:
        key = os.getenv("SPOONACULAR_KEY")
        if not key: return None
        url = f"https://api.spoonacular.com/food/products/upc/{barcode}?apiKey={key}"
        return await self._get(url, "Spoonacular")

    async def _get(self, url: str, provider: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"Product found in {provider}")
                    return response.json()
        except Exception as e:
            logger.error(f"Error connecting to {provider}: {str(e)}")
        return None
