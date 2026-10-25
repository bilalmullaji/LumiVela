import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import health, init_session, chat_endpoint, get_catalog, root, InitRequest, ChatRequest

def run_tests():
    print("Testing Vela FastAPI Endpoints...")

    # 1. Health
    h = health()
    assert h["status"] == "online"
    print("[OK] Health endpoint: ONLINE")

    # 2. Root (Static index.html check)
    r = root()
    assert r.path.endswith("index.html")
    print(f"[OK] Root endpoint serves {os.path.basename(r.path)}")

    # 3. Init session
    init_res = init_session(InitRequest(thread_id="test_sync_web"))
    assert "Vela" in init_res["greeting"]
    print("[OK] Init session endpoint: GREETING DELIVERED")

    # 4. Chat: Occasion
    c1 = chat_endpoint(ChatRequest(message="all of the examples", thread_id="test_sync_web"))
    assert "budget" in c1["response"].lower() or "tier" in c1["response"].lower()
    print("[OK] Chat endpoint Turn 1 (Occasion: All) Passed")

    # 5. Chat: Fit & Budget -> Product cards
    c2 = chat_endpoint(ChatRequest(
        message="oversized heavyweight cuts, whatever the customer demands",
        thread_id="test_sync_web"
    ))
    assert len(c2["recommended_products"]) == 3
    print(f"[OK] Chat endpoint Turn 2 returned {len(c2['recommended_products'])} rich product cards!")

    # 6. Catalog
    cat = get_catalog()
    assert len(cat["products"]) >= 8
    print(f"[OK] Catalog endpoint loaded {len(cat['products'])} catalog items!")

    print("\nSUCCESS: ALL FASTAPI BACKEND & FRONTEND ENDPOINTS VERIFIED!")

if __name__ == "__main__":
    run_tests()
