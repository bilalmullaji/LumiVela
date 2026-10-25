import re
from typing import Optional, Tuple, List

# Patterns for prompt injection / jailbreak attempts
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) (instructions|prompts|rules)",
    r"system prompt",
    r"you are now (dan|unrestricted|jailbroken)",
    r"developer mode",
    r"pretend to be",
    r"disregard (the )?rules",
    r"override your programming",
]

# Patterns for out-of-scope topics
OUT_OF_SCOPE_TOPICS = [
    # Programming & Coding
    (r"\b(python|javascript|java|c\+\+|rust|html|css|sql|react|fastapi|langgraph|langchain)\b(?!.*(wear|tee|hoodie|fit|brand))", "technical programming"),
    (r"\b(write a (script|program|code|function|algorithm)|debug|binary search|regex)\b", "software development"),

    # Math & Equations
    (r"\b(solve|calculate|equation|derivative|integral|algebra|quadratic)\b", "mathematics"),
    (r"^\s*\d+\s*[\+\-\*\/]\s*\d+\s*=?\s*$", "math calculations"),

    # Politics & Sensitive Topics
    (r"\b(politics|election|president|prime minister|democrat|republican|parliament|voting)\b", "politics"),

    # Weather & News
    (r"\b(weather in|temperature today|forecast|weather report)\b", "weather forecasts"),
    (r"\b(crypto|bitcoin|ethereum|stock market|shares|invest in)\b", "financial trading"),

    # Recipes & Cooking
    (r"\b(recipe for|how to cook|ingredients for|bake a cake|cook pasta)\b", "cooking recipes"),

    # Homework & General Trivia
    (r"\b(who was|capital of|tell me the history of|write an essay on|do my homework)\b", "general academic trivia"),

    # Competitor Redirects
    (r"\b(nike|adidas|gymshark|lululemon|under armour|zara|h&m|puma)\b", "competitor brands"),
]

# ─────────────────────────────────────────────────────────────────
# OUT-OF-CATALOGUE clothing/occasion terms — items Vela
# does NOT stock. Organised by category for easy maintenance.
# ─────────────────────────────────────────────────────────────────
OUT_OF_CATALOGUE_ITEMS: List[Tuple[str, str, str]] = [
    # (regex_pattern, readable_item_name, suggested_alternative)

    # Formal / Occasion Wear
    (r"\bwedding (outfit|dress|suit|attire|wear)\b",
     "wedding outfits",
     "Our closest elevated-casual option would be the **Minimalist Boxy Heavyweight Crewneck** paired with **Hybrid Utility Cargo Joggers** for a premium relaxed-formal aesthetic."),

    (r"\b(tuxedo|blazer|suit( jacket)?|formal (wear|shirt|trousers|pants)|dress shirt|tie|bow tie|cufflinks)\b",
     "formal / business attire",
     "Vela specialises in **elevated streetwear and performance cuts**. For a sharp smart-casual look, explore our **Minimalist Boxy Heavyweight Crewneck** (400 GSM) or **Thermal Oversized Zip Hoodie**."),

    (r"\b(saree|kurta|salwar|sherwani|lehenga|dupatta|ethnic wear|traditional wear|festive wear)\b",
     "ethnic / traditional wear",
     "Vela is a **streetwear and athletic performance brand**. We don't carry ethnic wear, but our **Minimalist Boxy Crewneck** or **Boxy Heavyweight Pump Cover Tee** are excellent for a clean, premium everyday look."),

    # Women's / Gendered Categories
    (r"\b(bikini|swimwear|swim suit|lingerie|bra|women'?s dress|mini skirt|blouse|kurti)\b",
     "swimwear / women's fashion",
     "Vela focuses on **gender-neutral streetwear and athletic performance gear**. Check out our **Compression Seamless Baselayer** or **5\\\" Pace Split Running Shorts** for active fits."),

    # Kids & Baby
    (r"\b(kids( wear)?|children'?s (clothes|outfit)|baby (clothes|outfit|romper|onesie)|toddler)\b",
     "kids / children's clothing",
     "Vela carries **adult streetwear and athletic apparel only** (sizes S–XL). Our smallest size is **Small (S)**."),

    # Footwear
    (r"\b(shoes?|sneakers?|boots?|sandals?|heels?|loafers?|trainers?|football boots?|basketball shoes?|cleats?)\b",
     "footwear",
     "We don't carry footwear at this time. Our **Crew Performance Socks (3-Pack)** are the closest accessory — engineered for maximum cushioning and arch support."),

    # Underwear / Base Layers (beyond our range)
    (r"\b(underwear|boxers?|briefs?|trunks? \(underwear\)|undershirt)\b",
     "underwear",
     "We don't carry underwear. Our **Compression Seamless Baselayer** is the closest performance inner-layer we stock."),

    # Accessories (Specific Luxury / Out-Scope)
    (r"\b(watch(es)?|jewellery|jewelry|necklace|bracelet|ring|earring|sunglasses?|glasses?|belt)\b",
     "jewellery / watches / eyewear",
     "Vela carries **performance-functional accessories** only: tactical sling duffles, distressed caps, and crew socks. We don't stock jewellery, watches, or eyewear."),

    # Office / Uniform Wear
    (r"\b(uniform|office wear|corporate wear|work clothes|business casual outfit)\b",
     "office / uniform wear",
     "Vela isn't an office-wear brand. That said, our **Minimalist Boxy Heavyweight Crewneck** + **French Terry Relaxed Sweatpants** create a clean, smart-casual look that works for low-key office environments."),

    # Sports Equipment (not clothing)
    (r"\b(helmet|shin guard|knee pad|elbow pad|gloves?( for sports?)?|cricket bat|football|dumbbell|barbell)\b",
     "sports equipment",
     "Vela sells **performance apparel**, not sports equipment. Head to a sports retailer for gear — we'll handle what you wear while you train."),

    # Bags (beyond our tactical range)
    (r"\b(handbag|purse|clutch|laptop bag|backpack|briefcase|school bag)\b",
     "handbags / laptop bags",
     "We carry one specialised bag: the **Modular Sling / Gym Duffle** — built from waterproof Cordura ballistic nylon. It's designed specifically for gym-to-street use."),

    # Outerwear beyond range
    (r"\b(raincoat|trench coat|puffer jacket|parka|overcoat|peacoat)\b",
     "heavy outerwear (parka / trench coats)",
     "Our closest outerwear is the **Modular Tech Windbreaker Shell** (DWR-coated, 3-layer breathable ripstop nylon) and the **Thermal Oversized Zip Hoodie** (480 GSM). We don't carry full winter parkas or trench coats."),

    # Yoga / Pilates specific
    (r"\b(yoga( pants| leggings| outfit)?|pilates( outfit)?|leggings?)\b",
     "yoga / pilates leggings",
     "We don't stock yoga leggings. Our **Compression Seamless Baselayer** and **5\\\" Pace Split Running Shorts** are the closest high-stretch, performance-first options we carry."),
]

# Safe retail & fashion context words that should never trigger false positives
SAFE_FASHION_TERMS = {
    "gym", "workout", "lifting", "weights", "hoodie", "tee", "shirt", "cargos", "joggers",
    "sweatpants", "crewneck", "jacket", "windbreaker", "shorts", "bag", "sling", "cap",
    "socks", "oversized", "heavyweight", "fit", "size", "small", "medium", "large", "xl",
    "budget", "price", "rupees", "inr", "cart", "checkout", "shipping", "return", "exchange",
    "continue", "proceed", "secure", "buy", "order", "drop", "vela", "fabric", "gsm",
    "streetwear", "casual", "stringer", "baselayer", "compression", "athletic", "performance"
}


def check_catalogue_availability(query: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Checks if the user is asking for something not stocked by Vela.

    Returns:
        (is_out_of_catalogue: bool, item_name: Optional[str], suggested_alternative: Optional[str])
    """
    clean_q = query.strip().lower()
    for pattern, item_name, suggestion in OUT_OF_CATALOGUE_ITEMS:
        if re.search(pattern, clean_q):
            return True, item_name, suggestion
    return False, None, None


def check_guardrails(query: str) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether the user's query violates retail concierge guardrails
    or is off-topic.

    Returns:
        (is_violation: bool, reason: Optional[str])
    """
    clean_q = query.strip().lower()
    if not clean_q:
        return False, None

    # 1. Prompt Injection Checks
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, clean_q):
            return True, "system security & prompt injection protection"

    # Check if query contains obvious retail/fashion context
    tokens = set(re.findall(r"\b\w+\b", clean_q))
    has_retail_context = bool(tokens.intersection(SAFE_FASHION_TERMS))

    # 2. Out-of-Scope Checks (if no legitimate retail context is present)
    for pattern, topic_name in OUT_OF_SCOPE_TOPICS:
        if re.search(pattern, clean_q):
            # Competitor brand always redirects
            if topic_name == "competitor brands":
                return True, topic_name
            if not has_retail_context:
                return True, topic_name

    return False, None


def get_out_of_catalogue_response(item_name: str, suggestion: str, state: dict) -> str:
    """
    Returns an on-brand, empathetic response when the user requests an
    item Vela does not carry, with a contextual pivot back to what we do stock.
    """
    cart_ids = state.get("selected_product_ids") or []
    cart_note = ""
    if cart_ids:
        cart_note = f"\n\n_(You currently have **{len(cart_ids)} item(s)** safely held in your cart.)_"

    return (
        f"⚡ **Not in the Vela Catalogue — Here's the Intel:**\n\n"
        f"We currently don't carry **{item_name}**. Vela is built strictly around "
        f"**premium heavyweight streetwear**, **technical athletic performance gear**, and **functional accessories**.\n\n"
        f"**However, here's the closest match we carry:**\n\n"
        f"{suggestion}\n\n"
        f"---\n"
        f"Would you like to explore what we do stock? Just tell me your vibe or occasion and I'll curate your perfect drops instantly!"
        f"{cart_note}"
    )


def get_guardrail_response(reason: str, state: dict) -> str:
    """
    Generates an on-brand, high-energy deflection that immediately pivots
    the customer back to their active shopping rotation.
    """
    if reason == "competitor brands":
        intro = (
            "⚡ **Vela Exclusive:** We don't speak for other brands—we operate on a completely different frequency. "
            "Our focus is strictly on architectural cuts, custom 310–480 GSM milled fabrics, and high-impact streetwear aesthetics."
        )
    elif reason == "system security & prompt injection protection":
        intro = (
            "⚡ **System Protocol Locked:** Nice try, but Vela AI stays strictly within its operational parameters—"
            "delivering elite streetwear and performance gear."
        )
    else:
        intro = (
            f"⚡ **Vela Style Guardrail:** I'm dialled in strictly as your **Vela Shopping Concierge**. "
            f"I specialise in cutting-edge streetwear, gym performance apparel, and silhouette curation—not {reason}."
        )

    # Contextual pivot back to shopping
    cart_ids = state.get("selected_product_ids") or []
    current_step = state.get("current_step") or "greeting"

    if cart_ids:
        pivot = f"\n\nYou currently have **{len(cart_ids)} item(s)** in your cart. Would you like to **continue shopping** for more pieces, or head to **checkout**?"
    elif current_step in ["recommending", "cross_selling", "product_added_ask_continue"]:
        pivot = "\n\nLet's get back to elevating your rotation! Which of the drops above catches your eye?"
    elif not state.get("occasions"):
        pivot = "\n\nLet's dial in your fit: What's the primary occasion or vibe you're shopping for today?"
    elif not state.get("fit_preference") or not state.get("budget_tier"):
        pivot = "\n\nWhat silhouette cut do you prefer (oversized heavyweight vs streamlined athletic), and what budget tier are we targeting?"
    elif not state.get("size"):
        pivot = "\n\nWhat size (S, M, L, XL) do you typically rock in tops and bottoms?"
    else:
        pivot = "\n\nReady to secure this drop before inventory clears?"

    return intro + pivot
