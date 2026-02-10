from typing import List

from langgraph.graph import MessagesState

from src.agents.graph.nodes.model.plan_model import Plan


class State(MessagesState):
    observations:List[str]
    plan_iteration:int
    current_plan:Plan | str = None
    final_report:str = ""
    enable_background_investigation:bool = True
    background_investigation_results:str = None


