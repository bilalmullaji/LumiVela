import json
import re
from typing import Dict, Any, List, Optional, TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.models import CustomerPreferences, Product
from src.catalog_service import CatalogService
from src.guardrails import check_guardrails, get_guardrail_response, check_catalogue_availability, get_out_of_catalogue_response

catalog = CatalogService()

class ConversationState(TypedDict):
    messages: Annotated[List[Dict[str, str]], operator.add]
    occasions: List[str]
    fit_preference: Optional[str]
    budget_tier: Optional[str]
    max_budget_inr: Optional[int]
    recommended_product_ids: List[str]
    selected_product_ids: List[str]
    suggested_accessory_id: Optional[str]
    size: Optional[str]
    current_step: str
    last_response: str
    continue_shopping: Optional[bool]

def parse_user_intent(state: ConversationState) -> Dict[str, Any]:
    """Analyzes the latest user message to update slots and state flags."""
    latest_msg = state["messages"][-1]["content"].lower() if state["messages"] else ""
    updates: Dict[str, Any] = {}

    # FAQ detection
    faq_ans = catalog.get_faq_answer(latest_msg)
    if faq_ans:
        updates["faq_answer"] = faq_ans

    # 1. Expanded Occasion Extraction
    occasions = list(state.get("occasions") or [])
    if any(w in latest_msg for w in ["gym", "workout", "lifting", "heavy", "weights", "pr", "bodybuilding", "powerlifting", "crossfit", "training"]):
        if "gym" not in occasions:
            occasions.append("gym")
    if any(w in latest_msg for w in ["street", "casual", "streetwear", "urban", "night out", "party", "club", "college", "campus", "daily", "coffee"]):
        if "streetwear" not in occasions:
            occasions.append("streetwear")
    if any(w in latest_msg for w in ["travel", "airport", "flight", "transit", "road trip", "journey"]):
        if "travel" not in occasions:
            occasions.append("travel")
    if any(w in latest_msg for w in ["lounge", "lounging", "cozy", "home", "chill", "relax", "rest day"]):
        if "loungewear" not in occasions:
            occasions.append("loungewear")
    if any(w in latest_msg for w in ["run", "running", "sprint", "cardio", "track", "marathon", "jogging"]):
        if "running" not in occasions:
            occasions.append("running")
    if any(w in latest_msg for w in ["outdoor", "trail", "hiking", "hike", "cold weather", "winter", "rain", "wind"]):
        if "outdoor" not in occasions:
            occasions.append("outdoor")
    if any(w in latest_msg for w in ["all", "crossover", "hybrid", "both", "everything", "all of the examples"]):
        occasions = ["gym", "streetwear", "travel", "loungewear", "running", "outdoor", "crossover"]
    updates["occasions"] = occasions

    # 2. Fit Extraction
    fit_pref = state.get("fit_preference")
    if any(w in latest_msg for w in ["oversized", "heavyweight", "boxy", "loose", "relaxed", "baggy"]):
        fit_pref = "oversized heavyweight"
    elif any(w in latest_msg for w in ["streamlined", "athletic", "slim", "compression", "fitted"]):
        fit_pref = "streamlined athletic"
    elif any(w in latest_msg for w in ["minimalist", "clean"]):
        fit_pref = "minimalist"
    updates["fit_preference"] = fit_pref

    # 3. Budget Extraction
    max_budget = state.get("max_budget_inr")
    budget_tier = state.get("budget_tier")
    if "tier 1" in latest_msg or "4,000" in latest_msg or "7,500" in latest_msg or "4000" in latest_msg or "7500" in latest_msg:
        budget_tier = "Tier 1 (₹4,000 – ₹7,500)"
        max_budget = 7500
    elif "tier 2" in latest_msg or "15,000" in latest_msg or "15000" in latest_msg:
        budget_tier = "Tier 2 (₹7,500 – ₹15,000)"
        max_budget = 15000
    elif any(w in latest_msg for w in ["tier 3", "apex", "demands", "whatever", "unlimited", "no limit", "flex", "open"]):
        budget_tier = "Tier 3 / Apex (Unrestricted)"
        max_budget = None
    updates["budget_tier"] = budget_tier
    updates["max_budget_inr"] = max_budget

    # 4. Item Selection Extraction
    selected = list(state.get("selected_product_ids") or [])
    rec_ids = list(state.get("recommended_product_ids") or [])

    # Direct Product ID matching
    for p in catalog.products:
        if p.id.lower() in latest_msg:
            if p.id not in selected:
                selected.append(p.id)

    # Fuzzy name matching against catalog titles
    for p in catalog.products:
        name_l = p.name.lower()
        tokens = [t for t in re.findall(r"[a-z0-9]+", name_l) if len(t) > 3]
        key_tokens = tokens[:3]
        if key_tokens and all(t in latest_msg for t in key_tokens[:2]):
            if p.id not in selected:
                selected.append(p.id)

    # Keyword shortcuts for common pieces
    keyword_map = [
        (("pump cover", "boxy tee", "heavyweight tee"), "VL-TEE-001"),
        (("cargo", "jogger", "utility"), "VL-JOG-002"),
        (("hoodie", "zip hoodie", "thermal"), "VL-HD-003"),
        (("sweatpants", "sweats", "french terry"), "VL-SWT-006"),
        (("crewneck", "crew"), "VL-CRW-007"),
        (("windbreaker", "shell", "jacket"), "VL-WND-008"),
        (("baselayer", "compression"), "VL-TEE-004"),
        (("stringer", "tank"), "VL-TNK-009"),
        (("running shorts", "split shorts", "shorts"), "VL-SHT-005"),
    ]
    for keys, pid in keyword_map:
        if any(k in latest_msg for k in keys):
            if pid not in selected:
                selected.append(pid)

    # Ordinal matching from recommended list
    if rec_ids:
        if any(w in latest_msg for w in ["first one", "first", "1st", "item 1", "number 1", "piece 1", "top one", "left one"]):
            if rec_ids[0] not in selected:
                selected.append(rec_ids[0])
        if len(rec_ids) > 1 and any(w in latest_msg for w in ["second one", "second", "2nd", "item 2", "number 2", "piece 2", "middle one"]):
            if rec_ids[1] not in selected:
                selected.append(rec_ids[1])
        if len(rec_ids) > 2 and any(w in latest_msg for w in ["third one", "third", "3rd", "item 3", "number 3", "piece 3", "last one"]):
            if rec_ids[2] not in selected:
                selected.append(rec_ids[2])

    # Bulk / Full fit selection
    if any(w in latest_msg for w in ["all of them", "full fit", "full setup", "both", "everything", "whole fit", "lock in full fit"]):
        if rec_ids and not selected:
            for rid in rec_ids:
                if rid not in selected:
                    selected.append(rid)

    # Accessory selection ("add accessory", "add sling", "add cap", "add socks", "add to fit")
    if any(w in latest_msg for w in ["add accessory", "add to fit", "add the sling", "add the cap", "add the socks", "modular sling", "tactical sling"]):
        acc_id = state.get("suggested_accessory_id") or "VL-ACC-001"
        if acc_id not in selected:
            selected.append(acc_id)

    updates["selected_product_ids"] = selected

    # 5. Size Extraction
    size = state.get("size")
    for s in ["small", "medium", "large", "xl"]:
        if re.search(rf"\b{s}\b", latest_msg):
            size = s[0].upper() if s != "xl" else "XL"
            break
    # Check standalone single letters
    for s_code in ["s", "m", "l", "xl"]:
        tokens = latest_msg.strip().split()
        if s_code in tokens or latest_msg.strip() == s_code or f"size {s_code}" in latest_msg:
            size = s_code.upper()
            break
    updates["size"] = size

    # 6. Continue Shopping vs Checkout Intent
    if any(w in latest_msg for w in ["continue shopping", "keep shopping", "browse more", "shop more", "more items", "more pieces", "add more", "another piece"]):
        updates["continue_shopping"] = True
    elif any(w in latest_msg for w in ["checkout", "head to checkout", "ready to checkout", "go to checkout", "done shopping", "that's all", "that is all", "done", "no more", "proceed to checkout"]):
        updates["continue_shopping"] = False

    return updates

# ----------------- HELPERS -----------------

CONFIRM_WORDS = (
    "confirm order", "place order", "confirm", "proceed", "yes", "buy", "pay",
    "secure", "finalize", "place it", "order it", "lock it in", "do it",
)
CHECKOUT_WORDS = (
    "checkout", "head to checkout", "ready to checkout", "go to checkout",
    "done shopping", "that's all", "that is all", "done", "no more",
    "proceed to checkout", "ready",
)
CONTINUE_SHOP_WORDS = (
    "continue shopping", "keep shopping", "browse more", "shop more",
    "more items", "more pieces", "add more", "another piece",
)


def _active_cart_ids(state: ConversationState) -> List[str]:
    selected = list(state.get("selected_product_ids") or [])
    if selected:
        return selected
    return list(state.get("recommended_product_ids") or [])


def _format_cart(state: ConversationState, include_size: bool = False) -> tuple:
    ids = _active_cart_ids(state)
    lines: List[str] = []
    total = 0
    for pid in ids:
        prod = catalog.get_product(pid)
        if not prod:
            continue
        if include_size and state.get("size"):
            sz = "One Size" if prod.category == "accessories" else f"Size {state['size']}"
            lines.append(f"* **{prod.name}** ({sz}) — ₹{prod.price_inr:,}")
        else:
            lines.append(f"* **{prod.name}** — ₹{prod.price_inr:,}")
        total += prod.price_inr
    return "\n".join(lines), total, ids


def _wants_checkout(msg: str, state: ConversationState) -> bool:
    if state.get("continue_shopping") is False:
        return True
    return any(w in msg for w in CHECKOUT_WORDS)


def _wants_continue_shop(msg: str, state: ConversationState) -> bool:
    if state.get("continue_shopping") is True:
        return True
    if any(w in msg for w in CONTINUE_SHOP_WORDS):
        return True
    step = state.get("current_step")
    if step == "product_added_ask_continue" and any(
        w in msg for w in ["browse", "more", "hoodie", "bottom", "cargo", "sweat", "jacket", "tops", "bottoms"]
    ):
        return True
    return False


def _wants_confirm(msg: str) -> bool:
    return any(w in msg for w in CONFIRM_WORDS)


def _review_order_response(state: ConversationState) -> Dict[str, Any]:
    lines, total, _ids = _format_cart(state, include_size=True)
    size = state.get("size") or "M"
    response = (
        f"**Order review** — size **{size}** locked.\n\n"
        "### Your bag\n"
        f"{lines}\n\n"
        f"**Total: ₹{total:,}**\n\n"
        "Ships Express in 24h · arrives in 2–3 days · 14-day easy exchanges.\n\n"
        "Say **confirm order** to place it, or **continue shopping** to add more."
    )
    return {"last_response": response, "current_step": "review_order"}


def _order_complete_response(state: ConversationState) -> Dict[str, Any]:
    lines, total, _ids = _format_cart(state, include_size=True)
    size = state.get("size") or "M"
    response = (
        "**Order confirmed.** You're all set.\n\n"
        "* **Order #** `VL-94281`\n"
        f"* **Size** {size}\n"
        f"* **Total** ₹{total:,}\n\n"
        f"{lines}\n\n"
        "Dispatch tomorrow via Express Air. Thanks for shopping **Vela**."
    )
    return {"last_response": response, "current_step": "completed"}


def _ask_size_response() -> Dict[str, Any]:
    return {
        "last_response": (
            "**Checkout next.** What size do you wear?\n\n"
            "Pick **S**, **M**, **L**, or **XL** — we'll use it for every piece in this order."
        ),
        "current_step": "asking_size",
    }


# ----------------- NODES -----------------

def routing_node(state: ConversationState) -> Dict[str, Any]:
    parsed = parse_user_intent(state)
    return parsed


def concierge_node(state: ConversationState) -> Dict[str, Any]:
    """
    Linear shopping path:
      prefs → recommend → cart → (optional browse) → size → review → confirmed
    """
    latest_msg = state["messages"][-1]["content"].lower() if state["messages"] else ""
    step = state.get("current_step") or "greeting"

    if step == "completed":
        return {
            "last_response": (
                "Your order is already confirmed (`#VL-94281`). "
                "Say **start over** if you want a fresh session, or ask about shipping/returns."
            ),
            "current_step": "completed",
        }

    is_ooc, ooc_item_name, ooc_suggestion = check_catalogue_availability(latest_msg)
    if is_ooc:
        response = get_out_of_catalogue_response(ooc_item_name, ooc_suggestion, state)
        return {"last_response": response, "current_step": "ooc_informed"}

    is_violation, reason = check_guardrails(latest_msg)
    if is_violation:
        response = get_guardrail_response(reason, state)
        return {"last_response": response}

    faq_ans = catalog.get_faq_answer(latest_msg)
    if faq_ans:
        if not state.get("occasions"):
            nudge = "What's the occasion you're shopping for?"
        elif not state.get("fit_preference") or not state.get("budget_tier"):
            nudge = "What fit and budget tier should we use?"
        elif not state.get("recommended_product_ids"):
            nudge = "Ready for your curated picks?"
        elif not state.get("selected_product_ids"):
            nudge = "Which piece should we add to your bag?"
        elif step == "asking_size" or not state.get("size"):
            nudge = "What size (S / M / L / XL)?"
        elif step == "review_order":
            nudge = "Say **confirm order** when you're ready."
        else:
            nudge = "Continue shopping or head to checkout?"
        return {
            "last_response": f"**Lumi · Vela:** {faq_ans}\n\n{nudge}",
            "current_step": "faq_answered",
        }

    if not state.get("occasions"):
        return {
            "last_response": (
                "Hey — I'm **Lumi**. I help you shop **Vela**.\n\n"
                "What's the vibe — gym, street, travel, lounge, outdoor, running, or a full crossover?"
            ),
            "current_step": "asking_occasion",
        }

    if not state.get("fit_preference") or not state.get("budget_tier"):
        if not state.get("fit_preference"):
            return {
                "last_response": (
                    "Nice. Two quick prefs:\n\n"
                    "1. **Fit** — oversized heavyweight, streamlined athletic, or clean minimalist?\n"
                    "2. **Budget** — Tier 1 (₹4k–₹7.5k), Tier 2 (₹7.5k–₹15k), or open?"
                ),
                "current_step": "asking_fit_and_budget",
            }
        return {
            "last_response": (
                "Got the fit. Which budget?\n\n"
                "* **Tier 1** — ₹4,000 – ₹7,500\n"
                "* **Tier 2** — ₹7,500 – ₹15,000\n"
                "* **Open** — no hard cap"
            ),
            "current_step": "asking_budget",
        }

    if not state.get("recommended_product_ids"):
        prefs = CustomerPreferences(
            occasions=state["occasions"],
            fit_preference=state["fit_preference"],
            budget_tier=state["budget_tier"],
            max_budget_inr=state.get("max_budget_inr"),
        )
        recent_bits = [
            m.get("content", "")
            for m in (state.get("messages") or [])[-6:]
            if m.get("role") == "user"
        ]
        recommended = catalog.filter_and_rank(
            prefs, limit=3, query_text=" ".join(recent_bits)
        )
        rec_ids = [p.id for p in recommended]
        items_text = "\n".join(
            f"* **{p.name}** — ₹{p.price_inr:,}"
            + (f" · ★ {p.rating:.1f}" if getattr(p, "rating", None) else "")
            for p in recommended
        )
        return {
            "last_response": (
                "Here are your best matches:\n\n"
                f"{items_text}\n\n"
                "Add a piece, or say **lock in full fit** for the whole set."
            ),
            "recommended_product_ids": rec_ids,
            "current_step": "recommending",
        }

    if step == "review_order" and (
        _wants_confirm(latest_msg)
        or any(w in latest_msg for w in ["secure this drop", "lock in drop", "priority hold"])
    ):
        return _order_complete_response(state)

    if _wants_continue_shop(latest_msg, state) and step in (
        "product_added_ask_continue", "review_order", "continue_shopping_browse", "faq_answered"
    ):
        cat_match = None
        if any(w in latest_msg for w in ["bottom", "cargo", "jogger", "sweatpant", "pant", "shorts"]):
            cat_match = "bottoms"
        elif any(w in latest_msg for w in ["hoodie", "jacket", "windbreaker", "outerwear"]):
            cat_match = "outerwear"
        elif any(w in latest_msg for w in ["tee", "shirt", "top", "stringer", "baselayer"]):
            cat_match = "tops"
        elif any(w in latest_msg for w in ["accessory", "accessories", "bag", "cap", "socks", "sling"]):
            cat_match = "accessories"

        if cat_match:
            cat_prods = [
                p for p in catalog.products
                if p.category == cat_match and p.id not in (state.get("selected_product_ids") or [])
            ][:2]
            prods_text = "\n".join(
                f"* **{p.name}** — ₹{p.price_inr:,}" for p in cat_prods
            ) or "_No more pieces in that category right now._"
            response = (
                f"Browsing **{cat_match}** — your bag is saved.\n\n"
                f"{prods_text}\n\n"
                "Pick one to add, or say **checkout** when you're ready."
            )
        else:
            response = (
                "Bag saved. What next?\n\n"
                "* Bottoms · Outerwear · Tops · Accessories\n\n"
                "Name a category or piece, or say **checkout**."
            )
        return {
            "last_response": response,
            "current_step": "continue_shopping_browse",
            "continue_shopping": None,
        }

    if _wants_checkout(latest_msg, state) and step in (
        "product_added_ask_continue", "continue_shopping_browse", "recommending",
        "asking_size", "faq_answered", "review_order",
    ):
        selected_ids = list(state.get("selected_product_ids") or [])
        updates: Dict[str, Any] = {}
        if not selected_ids and state.get("recommended_product_ids"):
            selected_ids = list(state["recommended_product_ids"])
            updates["selected_product_ids"] = selected_ids

        if not state.get("size"):
            return {**_ask_size_response(), **updates}
        return {**_review_order_response({**state, **updates}), **updates}

    if state.get("size") and step in (
        "asking_size", "recommending", "product_added_ask_continue", "continue_shopping_browse"
    ):
        selected_ids = list(state.get("selected_product_ids") or [])
        updates = {}
        if not selected_ids and state.get("recommended_product_ids"):
            selected_ids = list(state["recommended_product_ids"])
            updates["selected_product_ids"] = selected_ids
        if any(w in latest_msg for w in ["add accessory", "add the sling", "add the cap", "add the socks"]):
            acc_id = state.get("suggested_accessory_id") or "VL-ACC-001"
            if acc_id not in selected_ids:
                selected_ids = selected_ids + [acc_id]
                updates["selected_product_ids"] = selected_ids
        merged = {**state, **updates}
        return {**_review_order_response(merged), **updates}

    selected_ids = list(state.get("selected_product_ids") or [])
    selection_intent = selected_ids or any(
        w in latest_msg
        for w in ["lock in", "full fit", "select", "choose", "piece", "want the", "add the", "i'll take"]
    )
    if (
        not selected_ids
        and step == "recommending"
        and latest_msg.strip() in ("continue", "proceed", "yes", "ok", "okay")
    ):
        selection_intent = True

    if selection_intent and step in (
        "recommending", "continue_shopping_browse", "product_added_ask_continue",
        "faq_answered", "ooc_informed", "follow_up",
    ):
        if not selected_ids and state.get("recommended_product_ids"):
            selected_ids = list(state["recommended_product_ids"])

        lead_id = selected_ids[-1] if selected_ids else (state.get("recommended_product_ids") or [None])[0]
        lead_product = catalog.get_product(lead_id) if lead_id else None
        acc = catalog.get_complementary_accessory(lead_id) if lead_id else None
        acc_id = acc.id if acc else None

        cart_lines, total, _ = _format_cart(
            {**state, "selected_product_ids": selected_ids}, include_size=False
        )
        chosen = lead_product.name if lead_product else "Your picks"
        acc_blurb = ""
        if acc:
            acc_blurb = (
                f"\nOptional add-on: **{acc.name}** (₹{acc.price_inr:,}) — say **add accessory** if you want it.\n"
            )

        response = (
            f"**Added:** {chosen}\n\n"
            f"### Bag ({len(selected_ids)})\n"
            f"{cart_lines}\n\n"
            f"**Total: ₹{total:,}**"
            f"{acc_blurb}\n"
            "Next: **continue shopping** or **checkout**."
        )
        out: Dict[str, Any] = {
            "last_response": response,
            "selected_product_ids": selected_ids,
            "current_step": "product_added_ask_continue",
        }
        if acc_id:
            out["suggested_accessory_id"] = acc_id
        return out

    if step == "asking_size" and not state.get("size"):
        return _ask_size_response()

    if step == "review_order":
        return _review_order_response(state)

    if step == "recommending":
        return {
            "last_response": (
                "Pick a card, say a product name, or **lock in full fit** for everything shown."
            ),
            "current_step": "recommending",
        }

    return {
        "last_response": (
            "You can **add a piece**, **continue shopping**, or **checkout** whenever you're ready."
        ),
        "current_step": "follow_up",
    }


# ----------------- GRAPH BUILDER -----------------

def build_shopping_graph():
    workflow = StateGraph(ConversationState)

    workflow.add_node("router", routing_node)
    workflow.add_node("concierge", concierge_node)

    workflow.set_entry_point("router")
    workflow.add_edge("router", "concierge")
    workflow.add_edge("concierge", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
