from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver # For HITL
from typing import Literal
from ..agent_state.state import AgentState
from ..project_nodes.scout_node import scout_node
from ..project_nodes.agent_node import agent_node
from ..project_nodes.inspector_node import inspector_node
from ..project_nodes.interviewer_nodes import interviewer_node
from ..project_nodes.review_nodes import review_node
from ..project_nodes.submitter_node import submitter_node

# --- Routing Logic ---
def routing_function_inspector(state: AgentState) -> Literal["incomplete", "complete"]:
    if state.get("missing_fields"):
        return "incomplete"
    return "complete"

def routing_function_review(state: AgentState) -> Literal["approve", "re-edit"]:
    """
    Routing after the Review_Gate.
    """
    if state.get("is_approved") is True:
        return "approve"
    return "re-edit"

class AgentWorkflowBuilder:
    def __init__(self):
        print("[INFO]: Initializing Agent Workflow Builder...")

    async def build(self, checkpointer=None):
        # 1. Initialize Memory for HITL (default if no checkpointer passed)
        if checkpointer is None:
            checkpointer = MemorySaver()
            
        workflow = StateGraph(AgentState)

        # 2. Add All Nodes
        workflow.add_node("Scout", scout_node)
        workflow.add_node("Agent", agent_node)
        workflow.add_node("Inspector", inspector_node)
        workflow.add_node("Interviewer", interviewer_node)
        workflow.add_node("Review_Gate", review_node)
        workflow.add_node("Submitter", submitter_node)

        # 3. Define the Flow
        workflow.add_edge(START, "Scout")
        workflow.add_edge("Scout", "Agent")
        workflow.add_edge("Agent", "Inspector")

        # After Inspection: Go to Interviewer or Review Gate
        workflow.add_conditional_edges(
            "Inspector",
            routing_function_inspector,
            {"incomplete": "Interviewer", "complete": "Review_Gate"}
        )

        # If data was missing, wait for new user input and go back to Agent
        workflow.add_edge("Interviewer", END)

        # 4. HITL Decision Logic
        workflow.add_conditional_edges(
            "Review_Gate",
            routing_function_review,
            {
                "approve": "Submitter", 
                "re-edit": "Agent" # Loops back to fix data if human rejects
            }
        )

        workflow.add_edge("Submitter", END)

        # 5. Compile with Interrupt
        # We PAUSE the graph right before the Review_Gate node runs
        return workflow.compile(checkpointer=checkpointer, interrupt_before=["Review_Gate"])

    def __call__(self):
        return self.build()