import httpx
import sys
import json
from ..config.config import GET_PRICE_API
from .auth_service import login_and_get_token

async def fetch_quote_from_api(payload: dict) -> str:
    """
    Authenticates and sends the quote payload to the API.
    Returns JSON string.
    """
    # 1. Login
    token = await login_and_get_token()
    if not token:
        return json.dumps({"error": "Could not authenticate with Quote Service."})

    # 2. Setup Request
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 3. Send
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(GET_PRICE_API, json=payload, headers=headers, timeout=30.0)
            
            try:
                data = response.json()
                return json.dumps(data, indent=2)
            except:
                return json.dumps({"error": "Failed to parse API response", "raw_text": response.text})

        except Exception as e:
            print(f"[ERROR] Quote Request Failed: {e}", file=sys.stderr)
            return json.dumps({"error": f"System Error: {str(e)}"})
