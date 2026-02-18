from ..agent_state.state import AgentState
import os
import sys

# Try importing MCP components
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    # If mcp is not installed directly, we might need to handle it or rely on langchain adapters if used differently.
    # But for this custom integration, we need direct mcp access.
    pass 

async def submitter_node(state: AgentState):
    """
    Final node that runs after manual approval.
    TRANSFORMS extracted data into the exact MetroQuotes API Payload.
    """
    print("--- [NODE]: SUBMITTER (Final Submission) ---")
    
    data = state.get("extracted_data", {})
    
    # --- 1. SMART UNFLATTENING & MAPPING ---
    
    # helper to clean keys
    # e.g. "quotebasicinfo[].pickup_zip_code" -> "pickup_zip_code"
    # e.g. "items[].quantity" -> requires aggregation
    
    clean_data = {}
    items_list_map = {} # Index -> Item Dict
    
    # We iterate over all extracted keys
    for k, v in data.items():
        # Handle Basic Info Strings
        if "quotebasicinfo" in k and "items" not in k:
            # e.g. quotebasicinfo[].pickup_zip_code
            clean_key = k.split(".")[-1] # take the last part
            clean_data[clean_key] = v
            continue

        # Handle Items
        if "items[]" in k:
             # e.g. items[].quantity
             # Problem: logic above produced "items[].quantity": 2 (Single value or List?)
             # If users gave multiple items, Agent might return list? 
             # Log shows: "items[].quantity": 2. This suggests only ONE item was extracted flatly.
             # OR if multiple: "items[].quantity": [2, 1] ? 
             # Let's handle both.
             
             field_name = k.split(".")[-1]
             
             if isinstance(v, list):
                 # Parallel lists
                 for idx, val in enumerate(v):
                     if idx not in items_list_map: items_list_map[idx] = {}
                     items_list_map[idx][field_name] = val
             else:
                 # Single item case
                 idx = 0
                 if idx not in items_list_map: items_list_map[idx] = {}
                 items_list_map[idx][field_name] = v
            
             continue
             
        # Handle Direct keys (if Agent extracted cleanly)
        clean_data[k] = v

    # --- HELPER: Safe Get from Clean Data ---
    def get_val(key, default=None):
        return clean_data.get(key, default)

    # Map Pickup Type
    pickup_type = get_val("pickup_type") or get_val("pickup_type_code", "bp")
    pickup_type_code = str(pickup_type).upper() if pickup_type else "BP"

    # Service Level
    service_level = get_val("service_level", "WG")
    if isinstance(service_level, list):
        service_level = service_level[0] if service_level else "WG"

    # Items Transformation (From our Reconstructed Map)
    api_items = []
    
    # If we found items via "items[].X" keys
    if items_list_map:
        for idx in sorted(items_list_map.keys()):
            item = items_list_map[idx]
            # Same logic as before
            api_item = {
                "furniture_type": "OTH", 
                "quantity": int(item.get("quantity", 1)),
                "assembly_time": int(item.get("assembly_time", 0)), 
                "value_": float(item.get("value_", 1)),
                "packing_details": item.get("packing_details", "ps"), 
                "estimated_weight": float(item.get("estimated_weight", 1)),
                "estimated_weight_unit": item.get("estimated_weight_unit", "lb"),
                "dim_length": float(item.get("dim_length", 0) or item.get("length", 0)),
                "dim_width": float(item.get("dim_width", 0) or item.get("width", 0)),
                "dim_height": float(item.get("dim_height", 0) or item.get("height", 0)),
                "dim_unit": "IN", 
                "user_cu_feet": float(item.get("user_cu_feet", 0) or item.get("total_cubic_feet", 0))
            }
            api_items.append(api_item)
    
    # Fallback: If Agent extracted "items" as a list of dicts directly (standard)
    elif isinstance(get_val("items"), list):
        raw_items = get_val("items")
        for item in raw_items:
             api_item = {
                "furniture_type": "OTH",
                "quantity": int(item.get("quantity", 1)),
                "assembly_time": int(item.get("assemble_time", 0)), 
                "value_": float(item.get("value_", 1)),
                "packing_details": item.get("packing_details", "ps"), 
                "estimated_weight": float(item.get("estimated_weight", 1)),
                "estimated_weight_unit": item.get("estimated_weight_unit", "lb"),
                "dim_length": float(item.get("dim_length", 0) or item.get("length", 0)),
                "dim_width": float(item.get("dim_width", 0) or item.get("width", 0)),
                "dim_height": float(item.get("dim_height", 0) or item.get("height", 0)),
                "dim_unit": "IN", 
                "user_cu_feet": float(item.get("user_cu_feet", 0) or item.get("total_cubic_feet", 0))
            }
             api_items.append(api_item)

    # --- 2. CONSTRUCT FINAL PAYLOAD ---
    final_payload = {
        "quotebasicinfo": [
            {
                "pickup_zip_code": get_val("pickup_zip_code", ""),
                "pickup_military_base": False,
                "delivery_zip_code": get_val("delivery_zip_code", ""),
                "delivery_military_base": False,
                "service_level": service_level,
                "pickup_type_code": pickup_type_code 
            }
        ],
        "floor_no": int(get_val("floor_number", 0) or get_val("floor_no", 0)),
        "seats": 0,
        "order_type": 10000,
        "max_item_weight": 10, 
        "max_item_one_side_dim": 0,
        "client_identifier": "",
        "elevator_available": False,
        "insurance_required": True,
        "items": api_items,
        "key": get_val("key", ""),
        "mainkey": get_val("key", ""),
        "channel_id": "WEBQ2",
        "loginuser": 12708,
        "aviod_ferry": False,
        "aviod_outsource": False,
        "aviod_pickup_radius": False
    }
    
    # --- 3. OUTPUT ---
    import json
    formatted_json = json.dumps(final_payload, indent=2)
    
    print("\n" + "="*50)
    print("       [FINAL API PAYLOAD] (COPY BELOW)       ")
    print("="*50)
    print(formatted_json)
    print("="*50 + "\n")

    # --- 4. MCP INTEGRATION FOR PRICING ---
    mcp_output = ""
    try:
        # Resolve Project Root
        # We are at: .../apps/agent_app/src/agenticAI_full_workflow/project_nodes/submitter_node.py
        # We need: .../mcp_servers/pricing_server/src/server.py
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Walk up to find 'apps' folder, then go one level up to root
        # Heuristic: Find directory containing 'mcp_servers'
        
        root_dir = current_dir
        while len(root_dir) > 5 and not os.path.exists(os.path.join(root_dir, "mcp_servers")):
            parent = os.path.dirname(root_dir)
            if parent == root_dir: break
            root_dir = parent
            
        # Updated to point to 'quote_mcp'
        server_dir = os.path.join(root_dir, "mcp_servers", "quote_mcp")
        server_script = os.path.join(server_dir, "server.py")
        
        if os.path.exists(server_script):
            print("\n" + "-"*40)
            print("MCP AGENT: Connecting to Quote Server...")
            print("-" * 40)
            
            # Run the MCP server using 'uv'
            server_params = StdioServerParameters(
                command="uv",
                args=["run", "python", "server.py"],
                cwd=server_dir,
                env=os.environ.copy() 
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Call the generate_quote tool
                    print(">> Requesting Quote Generation...")
                    # The tool expects 'data' as the argument name
                    result = await session.call_tool("generate_quote", arguments={"data": final_payload})
                    
                    if result and hasattr(result, 'content'):
                        for content in result.content:
                            if content.type == "text":
                                print(f"\n{content.text}\n")
                                mcp_output += content.text + "\n"
                    else:
                        print(">> No content in result.")
                        
            print("-" * 40 + "\n")
        else:
            print(f"[WARNING]: Quote Server not found at {server_script}")
            mcp_output = f"Could not find Quote Server at {server_script}"
            
    except Exception as e:
        print(f"[ERROR]: MCP Pricing Check Failed: {e}")
        mcp_output = f"MCP Error: {str(e)}"
    
    final_message = "Order successfully generated! Please copy the JSON payload above."
    if mcp_output:
        final_message = f"Order successfully generated!\n\nQuote Result:\n{mcp_output}"

    return {
        "messages": [("assistant", final_message)]
    }
