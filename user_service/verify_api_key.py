from fastapi import Header, HTTPException
import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("SERVICE_KEY")
async def verify_api_key(api_key: str = Header(None, alias="X-API-Key")):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail=f"API Key không hợp lệ. Vui lòng liên hệ Admin để biết thêm chi tiết.")
    return api_key