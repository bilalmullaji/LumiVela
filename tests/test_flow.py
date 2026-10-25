import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import VelaAgent

import uuid

def test_full_shopping_journey():
    print("Testing Vela linear order flow...")
    agent = VelaAgent(thread_id=f"test_flow_{uuid.uuid4().hex[:8]}")

    r1 = agent.start_conversation()
    assert "Vela" in r1 or "Lumi" in r1
    print("[OK] Turn 1 (Greeting)")

    r2 = agent.chat("all of the examples")
    assert "budget" in r2.lower() or "tier" in r2.lower() or "fit" in r2.lower()
    print("[OK] Turn 2 (Occasion)")

    r3 = agent.chat("oversized heavyweight cuts, whatever the customer demands")
    assert "₹" in r3 or "INR" in r3
    print("[OK] Turn 3 (Recommendations)")

    r4 = agent.chat("Continue")
    assert "Added" in r4 or "Bag" in r4 or "cart" in r4.lower()
    assert "checkout" in r4.lower()
    print("[OK] Turn 4 (Added to bag)")

    r5 = agent.chat("checkout")
    assert "size" in r5.lower() or "S" in r5
    print("[OK] Turn 5 (Ask size)")

    r6 = agent.chat("Small")
    assert "review" in r6.lower() or "Total" in r6 or "confirm" in r6.lower()
    print("[OK] Turn 6 (Order review)")

    r7 = agent.chat("confirm order")
    assert "Order confirmed" in r7 or "VL-94281" in r7
    print("[OK] Turn 7 (Order confirmed)")

    print("\nSUCCESS: LINEAR ORDER FLOW VALIDATED")

if __name__ == "__main__":
    test_full_shopping_journey()
