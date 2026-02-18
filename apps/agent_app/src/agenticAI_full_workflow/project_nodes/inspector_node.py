import re
from ..agent_state.state import AgentState
from shared_core.logger.logging import logger

async def inspector_node(state: AgentState):
    logger.info("--- [NODE]: INSPECTOR (Strict Enforcement) ---")
    
    data = state.get("extracted_data", {})
    api_schema = state.get("form_schema", {})
    items = data.get("items", [])
    missing_fields = []

    # 1. CATEGORY VALIDATION MAP
    valid_codes = {
        "pickup_type_code": ["bp", "dd", "do", "mw", "rp"],
        "packing_details": ["ps", "pc", "cc", "bwc", "pcc"],
        "service_level": ["WG", "ROC", "TRHD", "DS"]
    }

    def clean_code(val):
        if isinstance(val, str) and " (" in val:
            return val.split(" (")[0].strip()
        return val

    # 2. ENFORCE REQUIRED TOP-LEVEL FIELDS (From Schema)
    # Humein check karna hai ke kya Zip Codes aur Key maujood hain?
    required_names = [f['name'] for f in api_schema.get("required_fields", [])]
    
    for f_name in required_names:
        # Skip items/quotebasicinfo for specialized check below
        if "items" in f_name or "quotebasicinfo" in f_name:
            continue
            
        val = data.get(f_name)
        if val is None or str(val).strip() == "":
            missing_fields.append(f"{f_name.replace('_', ' ').title()} is missing.")

    # 3. ENFORCE ITEMS (Must have at least one item)
    if not items or len(items) == 0:
        missing_fields.append("Shipment Items details are missing.")
    else:
        for i, item in enumerate(items):
            # Clean and Validate each item
            if item.get("packing_details"):
                item["packing_details"] = clean_code(item["packing_details"])
            
            # Check mandatory item fields
            if not item.get("estimated_weight"):
                missing_fields.append(f"Item {i+1}: Weight is missing.")
            if not item.get("quantity"):
                missing_fields.append(f"Item {i+1}: Quantity is missing.")
            
            # XOR Logic for Dims/Vol
            has_vol = item.get("user_cu_feet") or item.get("total_cubic_feet")
            has_dims = all([item.get("dim_length"), item.get("dim_width"), item.get("dim_height")])
            if not has_vol and not has_dims:
                missing_fields.append(f"Item {i+1}: Dimensions or Volume missing.")

    # 4. ENFORCE CATEGORY CODES
    for field, allowed in valid_codes.items():
        val = data.get(field) or data.get(f"quotebasicinfo[].{field}")
        if val:
            cleaned = clean_code(val)
            if cleaned not in allowed:
                missing_fields.append(f"Invalid {field}: '{cleaned}'.")

    # 5. LOOP BREAKER (Only if data is actually there)
    last_msg = state["messages"][-1].content.lower()
    confirmation_words = ["save", "ok", "good", "yes", "correct", "proceed"]
    
    # Industrial Rule: If user says 'ok' but data is empty, DO NOT proceed.
    if any(word in last_msg for word in confirmation_words) and not missing_fields and len(items) > 0:
        logger.info("  >> All checks passed. Moving to Review Gate.")
        return {"missing_fields": [], "extracted_data": data}

    logger.info(f"RESULT: Found {len(missing_fields)} issues.")
    return {"missing_fields": missing_fields, "extracted_data": data}