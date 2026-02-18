import sys
from ..utils.quote_service import fetch_quote_from_api
from ..utils.auth_service import login_and_get_token

async def test_connection() -> str:
    """
    Tests the connection by attempting to login and get a token.
    """
    token = await login_and_get_token()
    
    if token:
        masked_token = token[:10] + "..." + token[-5:]
        return f"SUCCESS: Login successful! Token retrieved: {masked_token}"
    else:
        return "FAILURE: Could not log in. Check server logs for details."

async def generate_quote(data: dict) -> str:
    """
    Generates a quote by forwarding the provided JSON payload to the API.
    The server handles authentication automatically.
    
    Args:
        data: The full JSON payload required by the Quote API.
    """
    print(f"[INFO] Received Quote Request. Payload keys: {list(data.keys())}", file=sys.stderr)

    # Call API Service directly with the data
    return await fetch_quote_from_api(data)
