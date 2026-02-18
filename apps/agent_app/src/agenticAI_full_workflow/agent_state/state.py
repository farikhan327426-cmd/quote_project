from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # This replaces MessagesState
    messages: Annotated[list, add_messages]
    # To store the fields we got from the API (Scout)
    form_schema: dict 
    # To store extracted values
    extracted_data: dict
    # To track what is missing
    missing_fields: List[str]
    # Approval flag
    is_approved: bool