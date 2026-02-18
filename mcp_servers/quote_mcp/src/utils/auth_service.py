import httpx
import sys
from ..config.config import API_BASE_URL, API_USERNAME, API_PASSWORD

async def login_and_get_token():
    """
    Logs in to the external API and returns the JWT token.
    """
    login_url = f"{API_BASE_URL}/API/Account/SignInAsync"
    payload = {
        "userID": API_USERNAME,
        "password": API_PASSWORD
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(login_url, json=payload, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            # Try common token keys
            token = data.get("token") or data.get("accessToken") or data.get("jwt") or data.get("jwToken")
            
            if not token:
                 print(f"[ERROR] Login Response missing token: {data}", file=sys.stderr)
                 return None
                 
            return token

        except Exception as e:
            print(f"[ERROR] Login Failed: {e}", file=sys.stderr)
            return None
