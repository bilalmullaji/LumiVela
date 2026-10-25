from typing import Generator, Dict, Any, Optional
from src.graph import build_shopping_graph

class VelaAgent:
    _shared_graph = None

    def __init__(self, thread_id: str = "default_session"):
        if VelaAgent._shared_graph is None:
            VelaAgent._shared_graph = build_shopping_graph()
        self.graph = VelaAgent._shared_graph
        self.thread_id = thread_id
        self.config = {"configurable": {"thread_id": thread_id}}
        self.state_initialized = False

    def start_conversation(self, thread_id: Optional[str] = None) -> str:
        """Kicks off the opening concierge message."""
        if thread_id:
            self.thread_id = thread_id
            self.config = {"configurable": {"thread_id": thread_id}}
        
        initial_input = {
            "messages": [{"role": "system", "content": "Start session"}],
            "occasions": [],
            "fit_preference": None,
            "budget_tier": None,
            "max_budget_inr": None,
            "recommended_product_ids": [],
            "selected_product_ids": [],
            "suggested_accessory_id": None,
            "size": None,
            "current_step": "greeting",
            "last_response": "",
            "continue_shopping": None,
        }
        res = self.graph.invoke(initial_input, config=self.config)
        self.state_initialized = True
        return res["last_response"]

    def chat(self, user_message: str, thread_id: Optional[str] = None) -> str:
        """Sends user message into the LangGraph state machine and returns response."""
        cfg = {"configurable": {"thread_id": thread_id}} if thread_id else self.config
        user_input = {
            "messages": [{"role": "user", "content": user_message}]
        }
        res = self.graph.invoke(user_input, config=cfg)
        return res["last_response"]

    def get_current_state(self, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Inspects live LangGraph checkpoint state."""
        cfg = {"configurable": {"thread_id": thread_id}} if thread_id else self.config
        state = self.graph.get_state(cfg)
        return state.values if state else {}
