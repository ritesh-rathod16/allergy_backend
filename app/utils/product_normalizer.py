from typing import Dict, Any, List


def normalize_product_data(raw_data: Dict[str, Any], provider: str, barcode: str) -> Dict[str, Any]:
    # ---------------- SAFE VALUE HELPER ---------------- #
    def val(x, default=0):
        try:
            if x in [None, "", "null"]: return default
            return float(x)
        except (ValueError, TypeError):
            return default

    def str_val(x, default="--"):
        s = str(x).strip() if x not in [None, "", "null"] else ""
        return s if s else default

    def _risk_for_text(name: str) -> Dict[str, str]:
        lower_name = name.lower()
        if any(a in lower_name for a in ["milk", "dairy", "whey", "casein", "lactose"]):
            return {"risk": "DANGEROUS", "reason": "Contains dairy-related ingredient"}
        if any(a in lower_name for a in ["soy", "soya", "lecithin"]):
            return {"risk": "CAUTION", "reason": "May contain soy-related ingredient"}
        if any(a in lower_name for a in ["wheat", "gluten", "barley", "rye", "malt", "spelt"]):
            return {"risk": "DANGEROUS", "reason": "Contains gluten"}
        if any(a in lower_name for a in ["peanut", "arachis", "groundnut", "almond", "walnut", "cashew", "hazelnut", "pistachio", "pecan"]):
            return {"risk": "DANGEROUS", "reason": "Nut-based allergen"}
        if any(a in lower_name for a in ["egg", "albumin", "ovalbumin", "ovomucoid"]):
            return {"risk": "DANGEROUS", "reason": "Contains egg-related ingredient"}
        return {"risk": "SAFE", "reason": "No known allergen signal"}

    def _ingredients_from_text(text: str) -> List[Dict[str, str]]:
        t = (text or "").strip()
        if not t or t == "--":
            return []
        parts = [p.strip() for p in t.replace("\n", ",").split(",")]
        out = []
        for part in parts:
            if not part:
                continue
            pretty = part[:1].upper() + part[1:]
            risk = _risk_for_text(part)
            out.append({"name": pretty, "risk": risk["risk"], "reason": risk["reason"]})
        return out

    if provider == "UPCitemDB":
        item = (raw_data.get("items") or [{}])[0] if isinstance(raw_data.get("items"), list) else {}
        name = str_val(item.get("title"), "--")
        brand = str_val(item.get("brand"), "--")
        image_url = "--"
        images = item.get("images")
        if isinstance(images, list) and images:
            image_url = str_val(images[0], "--")
        ingredients_text = str_val(item.get("description"), "--")
        ingredients_list = _ingredients_from_text(ingredients_text)
        if not ingredients_list:
            ingredients_list = _ingredients_from_text(str_val(item.get("offers") or "", "--"))
        return {
            "barcode": barcode,
            "name": name,
            "brand": brand,
            "quantity": "--",
            "imageUrl": image_url,
            "ingredientsText": ingredients_text,
            "ingredientsList": ingredients_list,
            "nutritionFacts": {},
            "nutriScore": "--",
            "ecoScore": "--",
            "novaGroup": 0,
            "healthScore": 0,
            "additives": [],
            "analysisTags": [],
            "aiInsights": [],
            "packaging": "--",
            "manufacturingCountry": "--",
            "stores": "--",
            "countriesSold": "--",
            "carbonFootprint": "--",
        }

    if provider == "BarcodeLookup":
        prod = (raw_data.get("products") or [{}])[0] if isinstance(raw_data.get("products"), list) else {}
        ingredients_text = str_val(prod.get("ingredients"), "--")
        return {
            "barcode": barcode,
            "name": str_val(prod.get("product_name"), "--"),
            "brand": str_val(prod.get("brand"), "--"),
            "quantity": str_val(prod.get("size"), "--"),
            "imageUrl": str_val(prod.get("images", ["--"])[0] if isinstance(prod.get("images"), list) and prod.get("images") else prod.get("image"), "--"),
            "ingredientsText": ingredients_text,
            "ingredientsList": _ingredients_from_text(ingredients_text),
            "nutritionFacts": {},
            "nutriScore": "--",
            "ecoScore": "--",
            "novaGroup": 0,
            "healthScore": 0,
            "additives": [],
            "analysisTags": [],
            "aiInsights": [],
            "packaging": "--",
            "manufacturingCountry": "--",
            "stores": "--",
            "countriesSold": "--",
            "carbonFootprint": "--",
        }

    if provider == "Spoonacular":
        ingredients_text = str_val(raw_data.get("ingredientList") or raw_data.get("ingredients"), "--")
        return {
            "barcode": barcode,
            "name": str_val(raw_data.get("title"), "--"),
            "brand": "--",
            "quantity": "--",
            "imageUrl": str_val(raw_data.get("image"), "--"),
            "ingredientsText": ingredients_text,
            "ingredientsList": _ingredients_from_text(ingredients_text),
            "nutritionFacts": {},
            "nutriScore": "--",
            "ecoScore": "--",
            "novaGroup": 0,
            "healthScore": 0,
            "additives": [],
            "analysisTags": [],
            "aiInsights": [],
            "packaging": "--",
            "manufacturingCountry": "--",
            "stores": "--",
            "countriesSold": "--",
            "carbonFootprint": "--",
        }

    if provider == "OpenFDA":
        res = (raw_data.get("results") or [{}])[0] if isinstance(raw_data.get("results"), list) else {}
        openfda = res.get("openfda") or {}
        name = str_val((openfda.get("brand_name") or ["--"])[0] if isinstance(openfda.get("brand_name"), list) else openfda.get("brand_name"), "--")
        brand = str_val((openfda.get("manufacturer_name") or ["--"])[0] if isinstance(openfda.get("manufacturer_name"), list) else openfda.get("manufacturer_name"), "--")
        ingredients_text = str_val(res.get("inactive_ingredient") or res.get("active_ingredient"), "--")
        return {
            "barcode": barcode,
            "name": name,
            "brand": brand,
            "quantity": "--",
            "imageUrl": "--",
            "ingredientsText": ingredients_text,
            "ingredientsList": _ingredients_from_text(ingredients_text),
            "nutritionFacts": {},
            "nutriScore": "--",
            "ecoScore": "--",
            "novaGroup": 0,
            "healthScore": 0,
            "additives": [],
            "analysisTags": [],
            "aiInsights": [],
            "packaging": "--",
            "manufacturingCountry": "--",
            "stores": "--",
            "countriesSold": "--",
            "carbonFootprint": "--",
        }

    p = raw_data.get("product", {})
    nutriments = p.get("nutriments", {})

    # ---------------- INGREDIENT LIST ---------------- #
    # OpenFoodFacts provides a list of ingredients with analysis
    raw_ingredients = p.get("ingredients", [])
    ingredients_list = []
    
    for ing in raw_ingredients:
        name = str(ing.get("text") or "").strip()
        if not name: continue
        
        pretty_name = name[:1].upper() + name[1:]

        risk = "SAFE"
        reason = "No known allergen signal"
        
        r = _risk_for_text(name)
        risk = r["risk"]
        reason = r["reason"]
            
        ingredients_list.append({
            "name": pretty_name,
            "risk": risk,
            "reason": reason
        })

    ingredients_text = str_val(p.get("ingredients_text") or p.get("ingredients_text_en"), "--")

    # ---------------- NUTRITION ---------------- #
    nutrition = {
        "energy-kcal_100g": val(nutriments.get("energy-kcal_100g")),
        "fat_100g": val(nutriments.get("fat_100g")),
        "saturated-fat_100g": val(nutriments.get("saturated-fat_100g")),
        "carbohydrates_100g": val(nutriments.get("carbohydrates_100g")),
        "sugars_100g": val(nutriments.get("sugars_100g")),
        "proteins_100g": val(nutriments.get("proteins_100g")),
        "salt_100g": val(nutriments.get("salt_100g")),
        "fiber_100g": val(nutriments.get("fiber_100g")),
        "sodium_100g": val(nutriments.get("sodium_100g")),
    }

    # ---------------- HEALTH SCORE CALCULATION ---------------- #
    # Basic health score starting at 100
    health_score = 100
    
    # Penalize based on sugars
    sugars = nutrition["sugars_100g"]
    if sugars > 15: health_score -= 20
    elif sugars > 5: health_score -= 10
    
    # Penalize based on saturated fat
    sat_fat = nutrition["saturated-fat_100g"]
    if sat_fat > 5: health_score -= 15
    elif sat_fat > 1.5: health_score -= 5
    
    # Penalize based on salt
    salt = nutrition["salt_100g"]
    if salt > 1.5: health_score -= 15
    elif salt > 0.3: health_score -= 5
    
    # Penalize based on NOVA group (ultra-processed)
    nova = int(val(p.get("nova_group"), 0))
    if nova == 4: health_score -= 30
    elif nova == 3: health_score -= 15
    
    health_score = max(0, health_score)

    # ---------------- AI INSIGHTS ---------------- #
    ai_insights = []
    if sugars > 15:
        ai_insights.append({"type": "warning", "text": "High sugar content", "icon": "warning"})
    if salt > 1.5:
        ai_insights.append({"type": "warning", "text": "High salt content", "icon": "warning"})
    if nova == 4:
        ai_insights.append({"type": "warning", "text": "Ultra-processed food", "icon": "error"})
    if nutrition["fiber_100g"] < 2 and health_score < 70:
        ai_insights.append({"type": "info", "text": "Low in dietary fiber", "icon": "info"})
    if health_score > 80:
        ai_insights.append({"type": "success", "text": "Healthy choice", "icon": "check_circle"})

    return {
        "barcode": barcode,
        "name": str_val(p.get("product_name") or p.get("product_name_en"), "--"),
        "brand": str_val(p.get("brands"), "--"),
        "quantity": str_val(p.get("quantity"), "--"),
        "imageUrl": str_val(p.get("image_url") or p.get("image_front_url"), "--"),
        "ingredientsText": ingredients_text,
        "ingredientsList": ingredients_list,
        "nutritionFacts": nutrition,
        "nutriScore": str_val(p.get("nutriscore_grade"), "--").upper(),
        "ecoScore": str_val(p.get("ecoscore_grade"), "--").upper(),
        "novaGroup": nova,
        "healthScore": health_score,
        "additives": p.get("additives_tags", []),
        "analysisTags": p.get("ingredients_analysis_tags", []),
        "aiInsights": ai_insights,
        "packaging": str_val(p.get("packaging"), "--"),
        "manufacturingCountry": str_val(p.get("manufacturing_places"), "--"),
        "stores": str_val(p.get("stores"), "--"),
        "countriesSold": str_val(p.get("countries"), "--"),
        "carbonFootprint": str_val(nutriments.get("carbon-footprint-from-known-ingredients_100g"), "--"),
    }

    # ---------------- HEALTH SCORE ---------------- #
    # Dynamic health score based on sugar, fat, and NOVA group
    health_score = 100

    if nutrition["sugars_100g"] > 22.5: health_score -= 25
    elif nutrition["sugars_100g"] > 11.25: health_score -= 10

    if nutrition["fat_100g"] > 17.5: health_score -= 20
    elif nutrition["fat_100g"] > 3: health_score -= 5

    if nutrition["saturated-fat_100g"] > 5: health_score -= 15

    if p.get("nova_group", 0) == 4: health_score -= 30
    elif p.get("nova_group", 0) == 3: health_score -= 15

    health_score = max(health_score, 0)

    # ---------------- SCORES ---------------- #
    nutri_score = str_val(p.get("nutriscore_grade"), "--").upper()
    eco_score = str_val(p.get("ecoscore_grade"), "--").upper()
    nova_group = p.get("nova_group") or 0

    # ---------------- ADDITIVES ---------------- #
    additives = [
        _humanize_additive(a)
        for a in p.get("additives_tags", [])
    ]

    # ---------------- ANALYSIS TAGS ---------------- #
    analysis_tags_raw = p.get("ingredients_analysis_tags", [])
    analysis_tags = [
        t.split(":")[-1].replace("-", " ").title()
        for t in analysis_tags_raw
    ]

    # ---------------- AI INSIGHTS ---------------- #
    ai_insights = _generate_ai_insights(nutrition, nova_group, analysis_tags_raw)

    # ---------------- FINAL OUTPUT ---------------- #
    return {
        "barcode": barcode,
        "name": str_val(p.get("product_name") or p.get("product_name_en"), "--"),
        "brand": str_val(p.get("brands"), "--"),
        "quantity": str_val(p.get("quantity"), "--"),
        "imageUrl": str_val(p.get("image_url"), "--"),

        "ingredientsText": ingredients_text,
        "ingredientsList": ingredients_list, # Now structured list of objects

        "nutritionFacts": nutrition,
        "nutriScore": nutri_score,
        "ecoScore": eco_score,
        "novaGroup": nova_group,
        "healthScore": health_score,

        "additives": additives,
        "analysisTags": analysis_tags,
        "aiInsights": ai_insights,

        "packaging": str_val(p.get("packaging"), "--"),
        "manufacturingCountry": str_val(p.get("manufacturing_places"), "--"),
        "stores": str_val(p.get("stores"), "--"),
        "countriesSold": str_val(p.get("countries"), "--"),
        "carbonFootprint": str_val(p.get("carbon_footprint_from_known_ingredients_100g"), "--"),
    }


# ---------------- ADDITIVE HUMANIZER ---------------- #
def _humanize_additive(tag: str) -> str:
    code = tag.split(':')[-1].upper()

    common = {
        "E330": "Citric Acid",
        "E621": "MSG",
        "E951": "Aspartame",
        "E202": "Potassium Sorbate",
        "E102": "Tartrazine",
        "E110": "Sunset Yellow",
        "E129": "Allura Red",
    }

    return f"{code} – {common.get(code, 'Food Additive')}"


# ---------------- AI INSIGHTS ---------------- #
def _generate_ai_insights(n: Dict, nova: int, analysis: List) -> List[Dict]:
    insights = []

    if n["sugars_100g"] > 22.5:
        insights.append({"type": "danger", "text": "High sugar content", "icon": "warning"})
    elif n["sugars_100g"] > 11.25:
        insights.append({"type": "warning", "text": "Moderate sugar content", "icon": "info"})

    if n["fat_100g"] > 17.5:
        insights.append({"type": "danger", "text": "High fat content", "icon": "warning"})

    if nova == 4:
        insights.append({"type": "danger", "text": "Ultra-processed food", "icon": "biotech"})
    elif nova == 3:
        insights.append({"type": "warning", "text": "Processed food", "icon": "factory"})

    tags_str = "".join(analysis).lower()

    if "vegan" in tags_str:
        insights.append({"type": "success", "text": "Vegan product", "icon": "eco"})
    elif "vegetarian" in tags_str:
        insights.append({"type": "success", "text": "Vegetarian product", "icon": "leaf"})

    if "palm-oil-free" in tags_str:
        insights.append({"type": "success", "text": "Palm oil free", "icon": "forest"})
    elif "palm-oil" in tags_str:
        insights.append({"type": "warning", "text": "Contains palm oil", "icon": "opacity"})

    return insights
