from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import dotenv_values
from pymongo import MongoClient
from routes import router as folklore_router
import boto3

config = dotenv_values(".env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = MongoClient(config["ATLAS_URI"])
    app.database = app.mongodb_client[config["DB_NAME"]]
    app.s3 = boto3.client("s3")
    yield
    app.mongodb_client.close()

app = FastAPI(lifespan=lifespan)

app.include_router(folklore_router, tags=["folklore"], prefix="/folklore")

