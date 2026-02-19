import os
import json
import httpx
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# 1. Improved .env Loading (Docker & Local Friendly)
def setup_env():
    # Pehle check karein ke kya hum Docker mein hain ya Environment Variables set hain
    # Agar OPENAI_API_KEY pehle se environment mein hai, toh .env ki zaroorat nahi
    if os.getenv("OPENAI_API_KEY"):
        print("[INFO]: Environment variables already loaded from System/Docker.")
        return

    current_dir = Path(__file__).resolve().parent
    env_found = False
    
    # Parents mein .env dhoondhein (sirf local development ke liye)
    for parent in [current_dir, *current_dir.parents]:
        env_file = parent / ".env"
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=True)
            print(f"[INFO]: Loaded environment from {env_file}")
            env_found = True
            break
    
    # Agar na system variables milein aur na .env file, toh sirf warning dein (crash na karein)
    if not env_found and not os.getenv("OPENAI_API_KEY"):
        print("[WARNING]: No .env file found and no environment variables detected.")

# Initialize environment
setup_env()

class MetroApiSchemaParser:
    def __init__(self):
        self.schema_url = os.getenv("FORM_GET_SCHEMA_URL")
        self.target_path = "/API/Price/GetPrice2"
        self.schema_data: Dict[str, Any] = {}

    def _resolve_ref(self, ref: str) -> Dict[str, Any]:
        """Resolves $ref pointers (e.g., #/components/schemas/QuoteRequest2)"""
        parts = ref.split('/')
        current = self.schema_data
        for part in parts:
            if part == '#': continue
            current = current.get(part, {})
        return current

    def _parse_schema_recursive(self, schema: Dict[str, Any], name_prefix: str = "") -> List[Dict[str, Any]]:
        # Yeh function same rahega kyunke ye nested fields (children) ko nikaalta hai
        fields = []
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"])

        properties = schema.get("properties", {})
        required_list = schema.get("required", [])

        for field_name, info in properties.items():
            if "$ref" in info:
                info = self._resolve_ref(info["$ref"])

            field_type = info.get("type", "object")
            label = info.get("title") or field_name.replace("_", " ").title()
            
            field_data = {
                "name": f"{name_prefix}{field_name}",
                "label": label,
                "type": field_type,
                "required": field_name in required_list,
                "description": info.get("description", ""),
                "example": info.get("example", ""),
                "format_regex": info.get("pattern") or info.get("format") or None,
                "options": info.get("enum", None)
            }

            # Recurse for Objects
            nested_info = info
            if "$ref" in info:
                nested_info = self._resolve_ref(info["$ref"])
            
            # DEBUG: Print keys to understand structure
            # DEBUG: Print keys to understand structure
            # DEBUG: Print keys to understand structure
            # DEBUG: Print keys to understand structure
            if "basicinfo" in field_name:
                with open("debug_schema.json", "w") as f:
                    json.dump(nested_info, f, default=str)
                print("DEBUG: Wrote debug_schema.json")

            # Handle allOf (Composition)
            if "allOf" in nested_info:
                for sub_schema in nested_info["allOf"]:
                     # Recurse into the sub-schema with the SAME prefix to flatten it into this object
                     child_fields = self._parse_schema_recursive(sub_schema, name_prefix=f"{name_prefix}{field_name}.")
                     fields.extend(child_fields)
                continue

            # If it has properties, it's a nested object we should flatten
            if "properties" in nested_info:
                child_fields = self._parse_schema_recursive(nested_info, name_prefix=f"{name_prefix}{field_name}.")
                fields.extend(child_fields)
                continue

            if field_type == "array":
                items_schema = info.get("items", {})
                if "$ref" in items_schema:
                    resolved_items = self._resolve_ref(items_schema["$ref"])
                    # Flatten arrays too
                    child_fields = self._parse_schema_recursive(resolved_items, name_prefix=f"{name_prefix}{field_name}[].")
                    fields.extend(child_fields)
                    continue
                else:
                    field_data["item_type"] = items_schema.get("type")

            fields.append(field_data)
        return fields

    async def get_price_v2_metadata(self) -> Optional[Dict[str, Any]]:
        """Main method to fetch and split fields into Required and Optional."""
        if not self.schema_url:
            return None

        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.get(self.schema_url, timeout=15.0)
                response.raise_for_status()
                self.schema_data = response.json()

                path_info = self.schema_data.get("paths", {}).get(self.target_path, {})
                content = path_info.get("post", {}).get("requestBody", {}).get("content", {})
                root_schema_ref = content.get("application/json", {}).get("schema", {}).get("$ref")
                
                if not root_schema_ref:
                    return {"error": "Root schema not found"}

                root_schema = self._resolve_ref(root_schema_ref)
                all_fields = self._parse_schema_recursive(root_schema)

                # --- 4. ENFORCE CRITICAL FIELDS (OVERRIDE API) ---
                # User wants Agent to ASK if these are missing, even if API says optional.
                CRITICAL_FIELDS = [
                    "quotebasicinfo[].pickup_zip_code",
                    "quotebasicinfo[].delivery_zip_code",
                    "quotebasicinfo[].service_level",
                    "items[].quantity",
                    "items[].estimated_weight",
                    "items[].value_"
                ]
                
                # Logic: Iterate and Force 'required=True'
                for field in all_fields:
                    # Check exact match or suffix match
                    # e.g. match "pickup_zip_code" if schema is "quotebasicinfo[].pickup_zip_code"
                    if field["name"] in CRITICAL_FIELDS:
                        field["required"] = True
                    # Partial match support if needed?
                    # For now, strict match based on known schema structure.
                    
                    # Also enforce Dims/Vol check at Inspector level (already done),
                    # so we don't strictly require one vs the other here, 
                    # but we do require basic Item info.

                # --- Yahan splitting logic hai ---
                required_fields = [f for f in all_fields if f['required'] is True]
                optional_fields = [f for f in all_fields if f['required'] is False]

                return {
                    "endpoint": self.target_path,
                    "method": "POST",
                    "required_fields": required_fields,
                    "optional_fields": optional_fields
                }

            except Exception as e:
                print(f"[ERROR]: {e}")
                return None

# --- Entry Point ---
async def main():
    parser = MetroApiSchemaParser()
    metadata = await parser.get_price_v2_metadata()
    if metadata:
        # Outputting as JSON for your Model to use
        print(json.dumps(metadata, indent=4))

if __name__ == "__main__":
    asyncio.run(main())