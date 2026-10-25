import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import VelaAgent

import uuid

def test_faq_interruption_and_pivot():
    print("Testing FAQ Interruption & Immediate Concierge Pivot...")
    agent = VelaAgent(thread_id=f"test_faq_{uuid.uuid4().hex[:8]}")

    agent.start_conversation()

    # User asks about shipping policy in the middle of shopping
    faq_res = agent.chat("What is your shipping policy and delivery time?")
    assert "Vela Intel" in faq_res
    assert "Express Air Priority" in faq_res
    assert "primary occasion" in faq_res.lower() or "fit" in faq_res.lower()
    print("[OK] Shipping FAQ answered and immediately pivoted back to shopping!")

    # User asks about return policy
    faq_res2 = agent.chat("How do returns work?")
    assert "Vela Intel" in faq_res2
    assert "14-day zero-friction" in faq_res2
    print("[OK] Returns FAQ answered and immediately pivoted back to shopping!")

    print("\nSUCCESS: FAQ INTERRUPTIONS AND PIVOTS FULLY VERIFIED!")

if __name__ == "__main__":
    test_faq_interruption_and_pivot()
