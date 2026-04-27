from typing import Optional, Dict, Any, List
from app.services.api_clients import GlobalProductClients
from app.utils.product_normalizer import normalize_product_data
import logging

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self):
        self.clients = GlobalProductClients()

    async def get_product_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Sequentially queries product sources until a product is found.
        1. OpenFoodFacts
        2. OpenBeautyFacts
        3. OpenFDA
        4. UPCitemDB
        5. BarcodeLookup
        6. Spoonacular
        """
        
        # 1. OpenFoodFacts (Food)
        logger.info(f"Querying OpenFoodFacts for: {barcode}")
        data = await self.clients.fetch_open_food_facts(barcode)
        if data and data.get("status") == 1:
            return normalize_product_data(data, "OpenFoodFacts", barcode)

        # 2. OpenBeautyFacts (Cosmetics)
        logger.info(f"Querying OpenBeautyFacts for: {barcode}")
        data = await self.clients.fetch_open_beauty_facts(barcode)
        if data and data.get("status") == 1:
            return normalize_product_data(data, "OpenBeautyFacts", barcode)

        # 3. OpenFDA (Medicine)
        logger.info(f"Querying OpenFDA for: {barcode}")
        data = await self.clients.fetch_open_fda(barcode)
        if data and data.get("results"):
            return normalize_product_data(data, "OpenFDA", barcode)

        # 4. UPCitemDB (General Retail)
        logger.info(f"Querying UPCitemDB for: {barcode}")
        data = await self.clients.fetch_upc_item_db(barcode)
        if data and data.get("items"):
            return normalize_product_data(data, "UPCitemDB", barcode)

        # 5. BarcodeLookup (General Retail)
        logger.info(f"Querying BarcodeLookup for: {barcode}")
        data = await self.clients.fetch_barcode_lookup(barcode)
        if data and data.get("products"):
            return normalize_product_data(data, "BarcodeLookup", barcode)

        # 6. Spoonacular (Food Fallback)
        logger.info(f"Querying Spoonacular for: {barcode}")
        data = await self.clients.fetch_spoonacular(barcode)
        if data and not data.get("status") == "failure":
            return normalize_product_data(data, "Spoonacular", barcode)

        logger.warning(f"Product not found in any global database: {barcode}")
        return None

product_service = ProductService()
