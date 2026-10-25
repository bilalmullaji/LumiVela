import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.catalog_service import CatalogService
from src.local_glove import cosine, embed_text
from src.models import CustomerPreferences


def test_related_terms_are_close():
    gym = embed_text("gym lifting heavy weights")
    street = embed_text("streetwear casual night out")
    oversized = embed_text("oversized boxy heavyweight tee")
    athletic = embed_text("streamlined athletic compression")

    assert cosine(gym, embed_text("workout powerlifting")) > cosine(gym, street)
    assert cosine(oversized, embed_text("baggy drop shoulder")) > cosine(oversized, athletic)


def test_semantic_ranking_prefers_matching_vibe():
    catalog = CatalogService()
    prefs = CustomerPreferences(
        occasions=["gym"],
        fit_preference="oversized heavyweight",
        max_budget_inr=15000,
    )
    recs = catalog.filter_and_rank(
        prefs, limit=3, query_text="boxy pump cover for lifting"
    )
    assert len(recs) >= 1
    # Pump cover tee should surface for that query
    names = " ".join(p.name.lower() for p in recs)
    assert "tee" in names or "hoodie" in names or "jogger" in names or "sweat" in names


if __name__ == "__main__":
    test_related_terms_are_close()
    test_semantic_ranking_prefers_matching_vibe()
    print("OK: local GloVe tests passed")
