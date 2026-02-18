from typing import List, Optional, Literal
from pydantic import BaseModel, Field, create_model

# Standard Enums
ServiceLevelCode = Literal["WG", "ROC", "TRHD", "DS"]
PackingDetails = Literal["ps", "pc", "cc", "bwc", "pcc"]
PickupType = Literal["bp", "dd", "do", "mw", "rp"]

def create_dynamic_model(api_schema: dict):
    """
    Industry-Ready: Creates a Nested Pydantic Model to support multiple items.
    """
    # 1. Define the fields for a SINGLE ITEM
    # We look for fields starting with 'items[]' in your scouted schema
    item_fields = {}
    main_fields = {}
    
    all_fields = api_schema.get("required_fields", []) + api_schema.get("optional_fields", [])
    
    for f in all_fields:
        name = f["name"]
        
        # Determine Python Type
        if name == "service_level": ptype = Optional[ServiceLevelCode]
        elif name == "packing_details": ptype = Optional[PackingDetails]
        elif name == "pickup_type_code": ptype = Optional[PickupType]
        elif f["type"] == "integer": ptype = Optional[int]
        elif f["type"] == "number": ptype = Optional[float]
        elif f["type"] == "boolean": ptype = Optional[bool]
        else: ptype = Optional[str]

        # Check if this belongs inside the 'items' list
        if "items[]." in name:
            clean_name = name.replace("items[].", "")
            item_fields[clean_name] = (ptype, Field(default=None))
        elif "quotebasicinfo[]." in name:
            # We can handle quotebasicinfo as a flat prefix for extraction
            main_fields[name] = (ptype, Field(default=None))
        else:
            main_fields[name] = (ptype, Field(default=None))

    # 2. Create the Sub-Model for Items
    ItemModel = create_model("ItemModel", **item_fields)
    
    # 3. Add the List of Items to the Main Model
    main_fields["items"] = (List[ItemModel], Field(default_factory=list))

    return create_model("StrictNestedFormModel", **main_fields)