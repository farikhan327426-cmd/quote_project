from ..agent_state.state import AgentState
from ..utils.model_loader import ModelLoader

model_loader = ModelLoader()
llm = model_loader.load_llm(model_type="fast")

async def interviewer_node(state: AgentState):
    """
    The Voice: Requests specific missing info and provides dropdown options to the user.
    """
    print("--- [NODE]: INTERVIEWER (Requesting Clarification) ---")
    
    missing_info = state.get("missing_fields", [])
    
    # INDUSTRIAL CONFIG: Define the "Menu" options to show the user
    categorical_help = {
        "service_level": "WG (White Glove), ROC (Room of Choice), TRHD (Threshold), DS (Door Step)",
        "packing_details": "ps (Shipper Packed), pc (Carrier Packed), cc (Crated)",
        "pickup_type_code": "bp (Business Pickup), rp (Residential Pickup), do (Origin Drop-off)"
    }

    # 1. Create a "Field Guide" for the LLM based on what is actually missing
    field_guide = []
    for issue in missing_info:
        guide_entry = f"- {issue}"
        # Check if we have specific options for this missing field
        for key, options in categorical_help.items():
            if key in issue.lower().replace(" ", "_"):
                guide_entry += f" | Available Options: [{options}]"
        field_guide.append(guide_entry)

    # 2. Professional Prompting
    system_prompt = (
        "You are a professional logistics coordinator. Your goal is to collect missing data for a shipping quote.\n"
        "INSTRUCTIONS:\n"
        "1. Be polite but extremely specific about the field names.\n"
        "2. For fields with 'Available Options', you MUST list those options so the user knows what to type.\n"
        "3. If multiple items are involved, ask for details for each item clearly.\n"
        "4. Keep it concise. Do not talk about things that are NOT in the issues list.\n\n"
        "ISSUES TO RESOLVE:\n" + "\n".join(field_guide)
    )
    
    # 3. Generate response using context
    messages = [("system", system_prompt)] + state["messages"][-5:] # Last few messages for context
    response = await llm.ainvoke(messages)
    
    return {
        "messages": [response]
    }