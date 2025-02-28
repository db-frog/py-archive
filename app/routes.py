from bson import ObjectId
from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from typing import List
from fastapi.responses import StreamingResponse

from .models import FolkloreCollection

router = APIRouter()

@router.get("/", response_description="List all folklore", response_model=List[FolkloreCollection])
def list_folklore(request: Request):
    folklore = list(request.app.database["Archive"].find(limit=500))
    return folklore

@router.get("/languages", response_description="List all languages of origin", response_model=List[str])
def list_languages(request: Request):
    genres = list(request.app.database["Archive"].distinct('folklore.language_of_origin'))
    return genres

@router.get("/language/{language}", response_description="Get all of given language of origin", response_model=List[FolkloreCollection])
def get_language(language: str, request: Request):
    folklore = list(request.app.database["Archive"].find({"folklore.language_of_origin": language}))
    return folklore

@router.get("/genres", response_description="List all possible genres", response_model=List[str])
def list_genres(request: Request):
    genres = list(request.app.database["Archive"].distinct('folklore.genre'))
    return genres

@router.get("/genre/{genre}", response_description="Get all of given genre", response_model=List[FolkloreCollection])
def get_genre(genre: str, request: Request):
    folklore = list(request.app.database["Archive"].find({"folklore.genre": genre}))
    return folklore

@router.get("/{id}", response_description="Get a single folklore entry by id", response_model=FolkloreCollection)
def find_folklore(id: str, request: Request):
    if (folklore := request.app.database["Archive"].find_one({"_id": ObjectId(id)})) is not None:
        return folklore

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folklore with ID {id} not found")

@router.get("/{id}/download", response_description="Download a single folklore entry by id")
def download_folklore(id: str, request: Request):
    if (folklore := request.app.database["Archive"].find_one({"_id": ObjectId(id)})) is not None:
        path = folklore["filename"]
        try:
            result = request.app.s3.get_object(Bucket="folklorearchive", Key=path)
            return StreamingResponse(content=result["Body"].iter_chunks())
        except Exception as e:
            if hasattr(e, "message"):
                raise HTTPException(
                    status_code=e.message["response"]["Error"]["Code"],
                    detail=e.message["response"]["Error"]["Message"],
                )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folklore with ID {id} not found")
