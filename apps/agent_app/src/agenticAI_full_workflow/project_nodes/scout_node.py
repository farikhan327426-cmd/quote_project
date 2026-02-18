from ..agent_state.state import AgentState
from ..utils.api_loader import MetroApiSchemaParser
from shared_core.logger.logging import logger

async def scout_node(state: AgentState):
    """
    Industrial Node: Checks cache first. Hits API ONLY if schema is missing.
    """
    logger.info("--- [NODE]: SCOUT (Schema Discovery) ---")
    
    # 1. PROFESSIONAL CHECK: Dekhein ke kya form_schema pehle se maujood hai?
    # Agar Postgres mein pehle se schema save hai, toh dobara API hit karne ki zaroorat nahi.
    current_schema = state.get("form_schema")
    
    if current_schema and current_schema.get("required_fields"):
        logger.info("  >> Schema found in Persistent State. Skipping API call.")
        return state

    # 2. FETCH ONLY IF NECESSARY
    try:
        logger.info("  >> Cache Miss! Fetching fresh schema from API...")
        parser = MetroApiSchemaParser()
        metadata = await parser.get_price_v2_metadata()
        
        if not metadata:
            # Defensive coding: error handle karein bajaye crash karne ke
            logger.error("API returned empty metadata.")
            return state 

        logger.info("  >> Successfully fetched and parsed schema.")
        
        # 3. SAVE TO STATE
        return {
            "form_schema": {
                "required_fields": metadata["required_fields"],
                "optional_fields": metadata["optional_fields"],
                "endpoint_info": {
                    "path": metadata["endpoint"],
                    "method": metadata["method"]
                }
            }
        }
    except Exception as e:
        logger.error(f"Scout API Error: {str(e)}")
        # Production practice: Agar schema nahi mila, toh crash na karein, 
        # balkay purana state return kar dein ya error state set karein.
        raise ValueError(f"CRITICAL: Failed to load API metadata. Details: {e}")