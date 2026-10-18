import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "25ds1000097@ds.study.iitm.ac.in"

# Step 1: who may read our answers from a browser
ALLOWED_ORIGINS = [
    "https://app-da4ar0.example.com",   # your assigned origin
    "https://exam.sanand.workers.dev",  # the exam page
]

LIMIT = 15      # B = 15 requests...
WINDOW = 10     # ...per 10 seconds

app = FastAPI()
hits = defaultdict(deque)  # client id -> timestamps of recent requests


# Middleware 2: rate limiting (per X-Client-Id)
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client = request.headers.get("x-client-id", "anonymous")
    now = time.monotonic()
    q = hits[client]

    # forget requests older than 10 seconds
    while q and now - q[0] >= WINDOW:
        q.popleft()

    if len(q) >= LIMIT:
        return JSONResponse(
            {"detail": "Too Many Requests"},
            status_code=429,
            headers={"Retry-After": str(WINDOW)},
        )

    q.append(now)
    return await call_next(request)


# Middleware 1: request context (the name tag)
@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# Middleware 3: CORS. Added LAST so it is the OUTERMOST layer.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,          # exact list, no "*"
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID"],        # lets browser JS read this header
)


@app.get("/ping")
async def ping(request: Request):
    return {"email": EMAIL, "request_id": request.state.request_id}
