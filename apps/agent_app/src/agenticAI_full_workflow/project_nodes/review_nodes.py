from ..agent_state.state import AgentState

async def review_node(state: AgentState):
    """
    This node runs AFTER the user says 'Yes' and the graph is resumed.
    """
    print("--- [NODE]: REVIEW GATE (Verified) ---")
    # No changes needed to state here, as app.py already set is_approved = True
    return state