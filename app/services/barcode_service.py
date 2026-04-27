import httpx
import os
from app.core.database import db
from typing import Optional, Dict, Any
import logging

class BarcodeService:
    @staticmethod
    async def get_product(barcode: str) -> Optional[Dict[str, Any]]:
        # 1. Check cache
        cached_product = await db.products_cache.find_one({"barcode": barcode})
        if cached_product:
            return cached_product
        
        # Order of APIs as per requirements:
        # 1. OpenFoodFacts
        # 2. OpenBeautyFacts
        # 3. OpenPetFoodFacts
        # 4. OpenFDA
        # 5. UPCitemDB
        # 6. BarcodeLookup (fallback)

        apis = [
            BarcodeService.fetch_open_food_facts,
            BarcodeService.fetch_open_beauty_facts,
            BarcodeService.fetch_open_pet_food_facts,
            BarcodeService.fetch_open_fda,
            BarcodeService.fetch_upc_item_db,
            BarcodeService.fetch_barcode_lookup
        ]

        for api_func in apis:
            try:
                product_data = await api_func(barcode)
                if product_data:
                    await BarcodeService.cache_product(product_data)
                    return product_data
            except Exception as e:
                logging.error(f"Error calling {api_func.__name__}: {e}")
        
        return None

    @staticmethod
    async def fetch_open_food_facts(barcode: str) -> Optional[Dict[str, Any]]:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 1:
                    p = data["product"]
                    return BarcodeService._unify(barcode, p, "OpenFoodFacts")
        return None

    @staticmethod
    async def fetch_open_beauty_facts(barcode: str) -> Optional[Dict[str, Any]]:
        url = f"https://world.openbeautyfacts.org/api/v0/product/{barcode}.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 1:
                    p = data["product"]
                    return BarcodeService._unify(barcode, p, "OpenBeautyFacts")
        return None

    @staticmethod
    async def fetch_open_pet_food_facts(barcode: str) -> Optional[Dict[str, Any]]:
        url = f"https://world.openpetfoodfacts.org/api/v0/product/{barcode}.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 1:
                    p = data["product"]
                    return BarcodeService._unify(barcode, p, "OpenPetFoodFacts")
        return None

    @staticmethod
    async def fetch_open_fda(barcode: str) -> Optional[Dict[str, Any]]:
        # OpenFDA API for NDC or UPC lookup
        url = f"https://api.fda.gov/drug/label.json?search=upc:\"{barcode}\""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if "results" in data and len(data["results"]) > 0:
                    p = data["results"][0]
                    return {
                        "barcode": barcode,
                        "name": p.get("openfda", {}).get("brand_name", [p.get("generic_name", ["Unknown"])[0]])[0],
                        "brand": p.get("openfda", {}).get("manufacturer_name", ["Unknown"])[0],
                        "category": "Healthcare/Drug",
                        "ingredients": p.get("active_ingredient", [""])[0] + " " + p.get("inactive_ingredient", [""])[0],
                        "nutrition": {},
                        "allergens": "",
                        "image": "",
                        "description": p.get("purpose", [""])[0],
                        "source": "OpenFDA"
                    }
        return None

    @staticmethod
    async def fetch_upc_item_db(barcode: str) -> Optional[Dict[str, Any]]:
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("items"):
                    p = data["items"][0]
                    return {
                        "barcode": barcode,
                        "name": p.get("title", "Unknown"),
                        "brand": p.get("brand", "Unknown"),
                        "category": p.get("category", "Unknown"),
                        "ingredients": p.get("description", ""), # Often contains ingredients in description
                        "nutrition": {},
                        "allergens": "",
                        "image": p.get("images", [""])[0],
                        "description": p.get("description", ""),
                        "source": "UPCitemDB"
                    }
        return None

    @staticmethod
    async def fetch_barcode_lookup(barcode: str) -> Optional[Dict[str, Any]]:
        # This usually requires an API key. Using a placeholder for production logic.
        api_key = os.getenv("BARCODE_LOOKUP_KEY")
        if not api_key: return None
        url = f"https://api.barcodelookup.com/v3/products?barcode={barcode}&key={api_key}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("products"):
                    p = data["products"][0]
                    return {
                        "barcode": barcode,
                        "name": p.get("title", "Unknown"),
                        "brand": p.get("brand", "Unknown"),
                        "category": p.get("category", "Unknown"),
                        "ingredients": p.get("ingredients", ""),
                        "nutrition": {},
                        "allergens": "",
                        "image": p.get("images", [""])[0],
                        "description": p.get("description", ""),
                        "source": "BarcodeLookup"
                    }
        return None

    @staticmethod
    def _unify(barcode: str, p: Dict[str, Any], source: str) -> Dict[str, Any]:
        return {
            "barcode": barcode,
            "name": p.get("product_name", p.get("title", "Unknown")),
            "brand": p.get("brands", p.get("brand", "Unknown")),
            "category": p.get("categories", p.get("category", "Unknown")),
            "ingredients": p.get("ingredients_text", p.get("ingredients", "")),
            "nutrition": p.get("nutriments", {}),
            "allergens": p.get("allergens", ""),
            "image": p.get("image_url", p.get("image_front_url", "")),
            "description": p.get("generic_name", p.get("description", "")),
            "source": source
        }

    @staticmethod
    async def cache_product(product_data: Dict[str, Any]):
        await db.products_cache.update_one(
            {"barcode": product_data["barcode"]},
            {"$set": product_data},
            upsert=True
        )
