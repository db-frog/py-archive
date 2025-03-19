from bson import ObjectId
from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from typing import List
from fastapi.responses import StreamingResponse
import json

from .models import FolkloreCollection

router = APIRouter()

def filter_from_json_str(filters: str):
    if not filters:
        return {}
    filters_dict: dict[str, List[str]] = json.loads(filters)
    query_filters: dict[str, List[str]] = {} # Need to remove empty filters
    for key in filters_dict:
        if filters_dict[key]:
            query_filters[f"folklore.{key}"] = {"$in": filters_dict[key]}
    return query_filters

@router.get("/", response_description="List all folklore", response_model=List[FolkloreCollection])
def list_folklore(request: Request):
    folklore = list(request.app.database["Archive"].find(limit=500))
    return folklore

@router.get("/paginated", response_description="List folklore specified by page size, page, and optional filters", response_model=List[FolkloreCollection])
def list_paginated_folklore(request: Request, page_size: int = 20, page: int = 1, filters: str = None):
    query_filters = filter_from_json_str(filters)
    page = max(page, 1)
    page_size = max(min(page_size, 20), 1)
    folklore = list(request.app.database["Archive"].find(query_filters).skip((page - 1) * page_size).limit(page_size))
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

@router.get("/random", response_description="Get a single folklore entry randomly with optional filter", response_model=List[FolkloreCollection])
def random_folklore(request: Request, filters: str = None):
    query_filters = filter_from_json_str(filters)
    folklore = list(request.app.database["Archive"].aggregate([
        {"$match": query_filters},
        {"$sample": {"size": 1}}
    ]))
    return folklore

@router.get("/count", response_description="Get the number of entries in the archive with optional filter", response_model=int)
def num_entries(request: Request, filters: str = None):
    query_filters = filter_from_json_str(filters)
    num = request.app.database["Archive"].count_documents(query_filters)
    return num

@router.get("/filters", response_description="Get available options for each filter field in the archive", response_model=dict[str, List[str]])
def get_filters(request: Request):
    languages = list(request.app.database["Archive"].distinct('folklore.language_of_origin'))
    genres = list(request.app.database["Archive"].distinct('folklore.genre'))
    return {
        "language_of_origin": languages,
        "genre": genres
    }

@router.get("/{id}", response_description="Get a single folklore entry by id", response_model=FolkloreCollection)
def find_folklore(id: str, request: Request):
    if (folklore := request.app.database["Archive"].find_one({"_id": ObjectId(id)})) is not None:
        return folklore

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folklore with ID {id} not found")

'''@router.get("/{id}/download", response_description="Download a single folklore entry by id")
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
'''
