import json
from ..agent_state.state import AgentState
from ..utils.model_loader import ModelLoader
from ..prompt_library.prompts import FORM_FILLER_SYSTEM_PROMPT
from ..schemas.form_schema import create_dynamic_model
from shared_core.logger.logging import logger

# Load the model once
model_loader = ModelLoader()
llm = model_loader.load_llm(model_type="smart")

def format_fields_for_prompt(fields_list):
    mapping_reference = {
        "pickup_type_code": "bp: Business Pickup, rp: Residential Pickup, dd: Drop-off at Metro Destination Terminal, do: Drop-off at Metro Origin Terminal, mw: Release from Metro Warehouse",
        "packing_details": "ps: Packed by Shipper, pc: Packed by Carrier, cc: Crated by Carrier, bwc: Blanket Wrapped by Carrier, pcc: Packed & Crated by Carrier",
        "service_level": "WG: White Glove, ROC: Room of Choice, TRHD: Threshold, DS: Door Step Delivery"
    }

    formatted = []
    for f in fields_list:
        name = f['name']
        # IMPORTANT: Identification of list fields
        is_list = "items" in name or "quotebasicinfo" in name
        clean_name = name.replace("items[].", "").replace("quotebasicinfo[].", "")
        
        line = f"- {clean_name} ({f.get('type')})"
        if is_list:
            line += " [PART OF A LIST OBJECT]"
            
        for key in mapping_reference:
            if key in clean_name:
                line += f" | USE CODES ONLY: [{mapping_reference[key]}]"
        formatted.append(line)
    return formatted

async def agent_node(state: AgentState):
    logger.info("--- [NODE]: AGENT (Multiple Items Extraction) ---")
    
    api_schema = state.get("form_schema", {})
    DynamicModel = create_dynamic_model(api_schema)
    
    # api_schema = state.get("form_schema", {}) # Already retrieved above
    # DynamicModel is created above
    
    # OPTIMIZATION: Removed manual schema injection ("Context Bloat").
    # The llm.with_structured_output(DynamicModel) handles the schema definition natively.
    
    sys_msg = (
        f"{FORM_FILLER_SYSTEM_PROMPT}\n\n"
        "CRITICAL INSTRUCTIONS FOR MULTIPLE ITEMS:\n"
        "1. If the user describes separate items (e.g. 'Item 1 is X, Item 2 is Y'), you MUST create TWO separate objects inside the 'items' list.\n"
        "2. Do NOT combine separate items into one by just increasing the quantity.\n"
        "3. Each object in the 'items' list must have its own 'value_', 'estimated_weight', etc.\n"
        "4. For fields like 'service_level', use the short code 'WG' only."
    )

    structured_llm = llm.with_structured_output(DynamicModel)
    logger.info("Invoking Agent...")
    try:
        response = await structured_llm.ainvoke([("system", sys_msg)] + state["messages"][-6:])
        new_data = response.model_dump(exclude_none=True)
        
        # Professional State Merging: 
        # For 'items', we overwrite the list if new specific item data is provided
        updated_data = state.get("extracted_data", {}).copy()
        updated_data.update(new_data)

        logger.info(f"Extracted {len(updated_data.get('items', []))} distinct items.")
        return {"extracted_data": updated_data, "messages": [("assistant", "Details updated.")]}
    except Exception as e:
        logger.error(f"Extraction Error: {e}")
        return state