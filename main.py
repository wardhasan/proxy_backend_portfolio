from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx, os
from dotenv import load_dotenv

load_dotenv()

FRONTEND_SECRET = os.getenv("FRONTEND_SECRET")
BACKEND_SECRET = os.getenv("BACKEND_SECRET")
BACKEND_URL = os.getenv("BACKEND_URL")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN")

app = FastAPI()

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

@app.post("/chat")
@limiter.limit("5/minute")
async def proxy_chat(request: Request, x_frontend_secret: str = Header(None)):
    if x_frontend_secret != FRONTEND_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid frontend secret")

    body = await request.json()
    timeout = httpx.Timeout(
        connect=5.0,  # time to establish connection
        read=60.0,    # time to wait for response body
        write=5.0,    # time to upload the request
        pool=5.0      # how long to wait for a free connection from the pool
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.post(
            BACKEND_URL,
            headers={"X-Api-Secret": BACKEND_SECRET},
            json=body
        )

    return JSONResponse(status_code=res.status_code, content=res.json())

