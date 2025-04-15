from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cacheout import Cache
from pymongo import MongoClient
from .routes import router as folklore_router
from .auth_routes import router as auth_router
from .auth import OidcClient
import boto3
from dotenv import load_dotenv
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    app.mongodb_client = MongoClient(os.environ["ATLAS_URI"])
    app.database = app.mongodb_client[os.environ["DB_NAME"]]
    app.auth = OidcClient(
        client_id=os.environ["OIDC_CLIENT_ID"],
        client_secret=os.environ["OIDC_CLIENT_SECRET"],
        authority_url=os.environ["OIDC_AUTHORITY_URL"],
        redirect_url=os.environ["OIDC_REDIRECT_URL"],
        frontend_url=os.environ["FRONTEND_URL"]
    )
    app.state.session_store = Cache(maxsize=4096, ttl=15 * 60, default=None)
    app.state.jwkts_store = Cache(maxsize=1, ttl=24*60*60, default=None)

    app.s3 = boto3.client("s3")
    yield
    app.mongodb_client.close()
app = FastAPI(lifespan=lifespan)
origins = [
    "https://docker15547-env-7928981.us.reclaim.cloud",
    "https://env-7928981.us.reclaim.cloud",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(folklore_router, tags=["folklore"], prefix="/folklore")
app.include_router(auth_router, tags=["auth"], prefix="/auth")
