import os
import uuid
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent import VelaAgent
from src.catalog_service import CatalogService

app = FastAPI(
    title="Vela AI Concierge",
    description="Cutting-Edge Streetwear & Athletic Apparel Digital Retail Assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = VelaAgent()
catalog = CatalogService()

base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class InitRequest(BaseModel):
    thread_id: Optional[str] = None

@app.get("/")
def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Vela AI API is running. static/index.html not found."}

@app.post("/api/init")
def init_session(req: Optional[InitRequest] = None):
    thread_id = (req.thread_id if req and req.thread_id else f"session_{uuid.uuid4().hex[:8]}")
    greeting = agent.start_conversation(thread_id=thread_id)
    state = agent.get_current_state(thread_id=thread_id)
    return {
        "thread_id": thread_id,
        "greeting": greeting,
        "state": state
    }

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    thread_id = req.thread_id or "default_session"
    reply = agent.chat(req.message, thread_id=thread_id)
    state = agent.get_current_state(thread_id=thread_id)

    # Attach any product cards currently relevant
    matched_products = []
    if state.get("recommended_product_ids"):
        for pid in state["recommended_product_ids"]:
            prod = catalog.get_product(pid)
            if prod:
                matched_products.append(prod.model_dump())

    accessory_card = None
    if state.get("suggested_accessory_id"):
        acc = catalog.get_product(state["suggested_accessory_id"])
        if acc:
            accessory_card = acc.model_dump()

    return {
        "response": reply,
        "state": state,
        "thread_id": thread_id,
        "recommended_products": matched_products,
        "suggested_accessory": accessory_card
    }

@app.get("/api/catalog")
def get_catalog():
    return {
        "brand": "Vela",
        "currency": "INR",
        "products": [p.model_dump() for p in catalog.products],
        "faq": catalog.faq
    }

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "service": "Vela AI Retail Concierge",
        "framework": "LangGraph StateGraph",
        "memory": "LangGraph MemorySaver"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
