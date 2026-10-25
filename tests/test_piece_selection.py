import sys
import os
import uuid

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import VelaAgent

def test_individual_piece_selection():
    print("Testing individual piece selection + clear checkout path...")
    thread = f"test_piece_{uuid.uuid4().hex[:8]}"
    agent = VelaAgent(thread_id=thread)

    agent.start_conversation()

    r2 = agent.chat("airport travel and loungewear")
    assert "budget" in r2.lower() or "tier" in r2.lower() or "fit" in r2.lower()
    print("[OK] Occasion parsed")

    r3 = agent.chat("oversized heavyweight cuts, whatever the customer demands")
    assert "₹" in r3 or "INR" in r3
    print("[OK] Recommendations")

    r4 = agent.chat("I choose piece VL-TEE-001")
    assert "Tee" in r4 or "Heavyweight" in r4 or "Added" in r4
    assert "checkout" in r4.lower()
    print("[OK] Single piece added")

    r5 = agent.chat("checkout")
    assert "size" in r5.lower()
    print("[OK] Size prompt")

    r6 = agent.chat("Size M")
    assert "review" in r6.lower() or "Total" in r6
    assert "M" in r6
    print("[OK] Order review with size")

    r7 = agent.chat("confirm order")
    assert "Order confirmed" in r7 or "VL-94281" in r7
    print("[OK] Order confirmed")

    print("\nSUCCESS: PIECE SELECTION PATH VERIFIED")

if __name__ == "__main__":
    test_individual_piece_selection()
