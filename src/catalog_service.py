import json
import os
from typing import List, Optional, Dict
from src.models import Product, CustomerPreferences
from src.local_glove import LocalGloveIndex, prefs_query_text

class CatalogService:
    def __init__(self, catalog_path: Optional[str] = None):
        if catalog_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            catalog_path = os.path.join(base_dir, "data", "catalog.json")
        
        self.catalog_path = catalog_path
        self._load_catalog()

    def _load_catalog(self):
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.products: List[Product] = [Product(**p) for p in data["products"]]
        self.products_by_id: Dict[str, Product] = {p.id: p for p in self.products}
        self.faq: Dict[str, str] = data.get("faq", {})
        # Local GloVe-style semantic index (offline, tiny)
        self._glove = LocalGloveIndex(self.products)

    def get_product(self, product_id: str) -> Optional[Product]:
        return self.products_by_id.get(product_id)

    def get_complementary_accessory(self, product_id: str) -> Optional[Product]:
        product = self.get_product(product_id)
        if product and product.complementary_accessory_id:
            return self.products_by_id.get(product.complementary_accessory_id)
        # Fallback to general best accessory
        for p in self.products:
            if p.category == "accessories":
                return p
        return None

    def filter_and_rank(
        self,
        prefs: CustomerPreferences,
        limit: int = 3,
        query_text: Optional[str] = None,
    ) -> List[Product]:
        scored: List[tuple[Product, float]] = []

        semantic_query = prefs_query_text(
            occasions=prefs.occasions,
            fit_preference=prefs.fit_preference,
            extra=query_text,
        )
        semantic_scores = (
            self._glove.score_products(semantic_query) if semantic_query.strip() else {}
        )

        for p in self.products:
            if p.category == "accessories":
                continue  # reserve accessories for cross-sell

            score = 0.0

            # Occasion overlap (stronger signal)
            if prefs.occasions:
                matched_occ = sum(
                    1 for occ in prefs.occasions
                    if any(occ.lower() in o.lower() or o.lower() in occ.lower() for o in p.occasions)
                )
                score += matched_occ * 18
                if matched_occ == 0 and "crossover" not in prefs.occasions:
                    score -= 8

            # Fit match
            if prefs.fit_preference:
                pref_fit_lower = prefs.fit_preference.lower()
                product_fit = p.fit.lower()
                if "oversized" in pref_fit_lower and "oversized" in product_fit:
                    score += 22
                if "heavyweight" in pref_fit_lower and "heavyweight" in product_fit:
                    score += 18
                if "athletic" in pref_fit_lower and "athletic" in product_fit:
                    score += 22
                if "streamlined" in pref_fit_lower and "streamlined" in product_fit:
                    score += 18
                if "minimalist" in pref_fit_lower and (
                    "minimalist" in product_fit or "boxy" in product_fit or p.category == "tops"
                ):
                    score += 16

            # Local GloVe-style semantic boost (cosine → 0..~28)
            sim = semantic_scores.get(p.id, 0.0)
            if sim > 0.05:
                score += sim * 28.0

            # Budget fit — hard filter when a max budget is set
            if prefs.max_budget_inr is not None:
                if p.price_inr > prefs.max_budget_inr:
                    continue
                headroom = prefs.max_budget_inr - p.price_inr
                score += 14 + max(0, 8 - (headroom / 2000))

            # Quality signal
            if p.rating:
                score += float(p.rating)

            scored.append((p, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Diversify categories so the rail isn't three similar tops
        picked: List[Product] = []
        used_categories = set()
        for product, _score in scored:
            if product.category in used_categories:
                continue
            picked.append(product)
            used_categories.add(product.category)
            if len(picked) >= limit:
                break

        if len(picked) < limit:
            for product, _score in scored:
                if product in picked:
                    continue
                picked.append(product)
                if len(picked) >= limit:
                    break

        return picked

    def get_faq_answer(self, query: str) -> Optional[str]:
        import re
        q = query.lower()
        if any(w in q for w in ["shipping", "shipment", "delivery", "transit", "courier", "how long to ship"]):
            return self.faq.get("shipping")
        if any(w in q for w in ["return", "exchange", "refund", "policy"]):
            return self.faq.get("returns")
        if re.search(r"\b(size chart|sizing guide|how does sizing work|measurements?|dimensions?)\b", q):
            return self.faq.get("sizing")
        return None
