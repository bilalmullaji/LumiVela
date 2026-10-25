"""
Tiny local GloVe-style embeddings for Vela catalog matching.

No TensorFlow / no API / no multi-GB download. Domain word vectors are
cluster-seeded (related fashion/gym terms sit near each other), unknown
tokens get a stable hash vector — same idea as GloVe averaging for short text.
"""
from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

DIM = 48

# Related terms share a cluster centroid → high cosine when phrases overlap in meaning.
_CLUSTERS: Dict[str, List[str]] = {
    "gym": [
        "gym", "workout", "workouts", "lifting", "lift", "weights", "pr", "bodybuilding",
        "powerlifting", "crossfit", "training", "pump", "hypertrophy", "compound", "squat",
        "bench", "deadlift", "sets", "reps",
    ],
    "street": [
        "street", "streetwear", "casual", "urban", "night", "party", "club", "college",
        "campus", "daily", "coffee", "drip", "fit", "fits", "rotation", "look",
    ],
    "travel": [
        "travel", "airport", "flight", "transit", "journey", "passport", "commute", "road",
    ],
    "lounge": [
        "lounge", "lounging", "cozy", "home", "chill", "relax", "rest", "soft", "comfort",
        "comfortable", "easy",
    ],
    "run": [
        "run", "running", "sprint", "cardio", "track", "marathon", "jogging", "jog", "pace",
    ],
    "outdoor": [
        "outdoor", "outdoors", "trail", "hiking", "hike", "cold", "winter", "rain", "wind",
        "weather", "thermal", "insulate", "insulated",
    ],
    "oversized": [
        "oversized", "oversize", "boxy", "loose", "relaxed", "baggy", "drape", "drop",
        "shoulder", "roomy", "wide",
    ],
    "heavyweight": [
        "heavyweight", "heavy", "dense", "gsm", "french", "terry", "fleece", "thick",
        "substantial", "310", "450", "480",
    ],
    "athletic": [
        "athletic", "streamlined", "slim", "compression", "fitted", "performance",
        "tapered", "taper", "muscle", "cut",
    ],
    "minimal": [
        "minimalist", "minimal", "clean", "tonal", "simple", "neutral", "matte",
    ],
    "tops": [
        "tee", "tshirt", "t-shirt", "shirt", "top", "tank", "stringer", "hoodie",
        "hood", "zip", "crew", "cover",
    ],
    "bottoms": [
        "pants", "joggers", "jogger", "sweatpants", "cargos", "cargo", "bottoms",
        "trouser", "trousers", "shorts",
    ],
    "outer": [
        "outerwear", "jacket", "shell", "layer", "layers", "hoodie",
    ],
    "accessory": [
        "accessory", "accessories", "cap", "hat", "socks", "sock", "bag", "duffle",
        "sling", "belt",
    ],
    "premium": [
        "premium", "apex", "signature", "architectural", "elevated", "luxe",
    ],
    "budget": [
        "budget", "cheap", "affordable", "under", "value", "essentials", "core",
    ],
}


def _seed_vec(seed: str, dim: int = DIM) -> List[float]:
    """Deterministic pseudo-random unit-ish vector from a string seed."""
    vec = [0.0] * dim
    h = 2166136261
    for ch in seed:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    for i in range(dim):
        h = (h * 1664525 + 1013904223) & 0xFFFFFFFF
        # map to [-1, 1]
        vec[i] = (h / 0xFFFFFFFF) * 2.0 - 1.0
    return _normalize(vec)


def _normalize(vec: Sequence[float]) -> List[float]:
    n = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / n for v in vec]


def _add(a: List[float], b: Sequence[float], scale: float = 1.0) -> None:
    for i, val in enumerate(b):
        a[i] += val * scale


def _build_vocab() -> Dict[str, List[float]]:
    vocab: Dict[str, List[float]] = {}
    for cluster, words in _CLUSTERS.items():
        base = _seed_vec(f"cluster:{cluster}")
        for i, word in enumerate(words):
            # Small orthogonal nudge so synonyms are close but not identical
            nudge = _seed_vec(f"{cluster}:{word}")
            mixed = [0.0] * DIM
            _add(mixed, base, 0.82)
            _add(mixed, nudge, 0.18)
            vocab[word] = _normalize(mixed)
    return vocab


_VOCAB = _build_vocab()
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _oov_vec(token: str) -> List[float]:
    return _seed_vec(f"oov:{token}")


def embed_tokens(tokens: Iterable[str]) -> List[float]:
    acc = [0.0] * DIM
    count = 0
    for tok in tokens:
        if len(tok) < 2:
            continue
        vec = _VOCAB.get(tok) or _oov_vec(tok)
        # In-vocab terms weigh more than hash OOV noise
        weight = 1.35 if tok in _VOCAB else 0.55
        _add(acc, vec, weight)
        count += 1
    if count == 0:
        return [0.0] * DIM
    return _normalize(acc)


def embed_text(text: str) -> List[float]:
    return embed_tokens(tokenize(text))


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    # Both are unit-normalized when produced by embed_*; still guard
    dot = sum(x * y for x, y in zip(a, b))
    return max(-1.0, min(1.0, float(dot)))


def product_document(product) -> str:
    parts = [
        getattr(product, "name", "") or "",
        getattr(product, "category", "") or "",
        getattr(product, "fit", "") or "",
        getattr(product, "aesthetic", "") or "",
        getattr(product, "fabric", "") or "",
        getattr(product, "description", "") or "",
        " ".join(getattr(product, "occasions", None) or []),
    ]
    if getattr(product, "gsm", None):
        parts.append(f"{product.gsm} gsm")
    return " ".join(parts)


def prefs_query_text(
    occasions: Optional[Sequence[str]] = None,
    fit_preference: Optional[str] = None,
    extra: Optional[str] = None,
) -> str:
    bits: List[str] = []
    if occasions:
        bits.extend(occasions)
    if fit_preference:
        bits.append(fit_preference)
    if extra:
        bits.append(extra)
    return " ".join(bits)


class LocalGloveIndex:
    """Precomputes product vectors; scores queries with cosine similarity."""

    def __init__(self, products: Sequence):
        self._vectors: Dict[str, List[float]] = {}
        for p in products:
            self._vectors[p.id] = embed_text(product_document(p))

    def similarity(self, product_id: str, query_vec: Sequence[float]) -> float:
        vec = self._vectors.get(product_id)
        if not vec:
            return 0.0
        return cosine(vec, query_vec)

    def score_products(
        self,
        query: str,
        product_ids: Optional[Iterable[str]] = None,
    ) -> Dict[str, float]:
        q = embed_text(query)
        ids = list(product_ids) if product_ids is not None else list(self._vectors.keys())
        return {pid: self.similarity(pid, q) for pid in ids}

    def top_k(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        scored = sorted(self.score_products(query).items(), key=lambda x: x[1], reverse=True)
        return scored[:k]
