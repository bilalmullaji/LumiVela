from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Product(BaseModel):
    id: str
    name: str
    category: str
    price_inr: int
    price_usd: int
    fit: str
    gsm: Optional[int] = None
    fabric: str
    occasions: List[str]
    aesthetic: str
    description: str
    sizes: List[str]
    complementary_accessory_id: Optional[str] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None

class CustomerPreferences(BaseModel):
    occasions: List[str] = Field(default_factory=list, description="Primary occasions (e.g. gym, streetwear, running, crossover)")
    fit_preference: Optional[str] = Field(default=None, description="e.g. oversized heavyweight, streamlined athletic, minimalist")
    budget_tier: Optional[str] = Field(default=None, description="Tier 1, Tier 2, Tier 3, or custom")
    max_budget_inr: Optional[int] = Field(default=None, description="Maximum budget in INR")
    preferred_size: Optional[str] = Field(default=None, description="S, M, L, XL")

class AgentState(BaseModel):
    messages: List[Dict[str, str]] = Field(default_factory=list)
    preferences: CustomerPreferences = Field(default_factory=CustomerPreferences)
    recommended_product_ids: List[str] = Field(default_factory=list)
    selected_product_ids: List[str] = Field(default_factory=list)
    suggested_accessory_id: Optional[str] = None
    current_step: str = "greeting"  # greeting -> asking_questions -> recommending -> cross_selling -> checkout -> done
    last_faq_type: Optional[str] = None
