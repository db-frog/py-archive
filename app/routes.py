from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Request, HTTPException, status, Depends
from typing import List
from fastapi.responses import StreamingResponse
import json

from .oidc_auth import oidc_auth
from .models import FolkloreCollection
router = APIRouter(dependencies=[Depends(oidc_auth)])

# Store thesaurus mapping to avoid repeated DB queries + small size
mapto_mapfrom : dict[str, dict[str, List[str]]] = {}
mapfrom_mapto : dict[str, dict[str, str]] = {}

def filter_from_json_str(filters: str, request: Request):
    if not filters:
        return {}
    populate_thesaurus_maps(request)
    filters_dict: dict[str, List[str] | str] = json.loads(filters)
    query_filters = {} # Need to remove empty filters
    search_stage = None # If cleaned_full_text is in filters

    for field_key, values in filters_dict.items():
        if not values:
            continue
        if field_key == "cleaned_full_text":
            search_stage = { "$search": { "index": "search", "text": {
                "query": values,
                "path": "cleaned_full_text"
            }}}
        else:
            reduced_key = field_key.split(".")[-1] # field_key has format path.field
            # Check if reduced_key has no mapping
            if reduced_key not in ["genre", "language_of_origin"]:
                query_filters[field_key] = {"$in": values}
                continue
            expanded_values : List[str] = []
            for v in values:
                expanded_values.extend(mapto_mapfrom[reduced_key][v])
            query_filters[field_key] = {"$in": expanded_values}
    return query_filters, search_stage

@router.get("/", response_description="List all folklore based on an optional filter", response_model=List[FolkloreCollection])
def list_folklore(request: Request, filters: str = None):
    query_filters, search_stage = filter_from_json_str(filters, request)
    if search_stage:
        pipeline = [search_stage]
        if query_filters:
            pipeline.append({"$match": query_filters})
        pipeline.append({"$limit": 500})
        return list(request.app.database["Archive"].aggregate(pipeline))
    else:
        return list(request.app.database["Archive"].find(query_filters).limit(500))

@router.get("/paginated", response_description="List folklore specified by page size, page, and optional filters", response_model=List[FolkloreCollection])
def list_paginated_folklore(request: Request, page_size: int = 20, page: int = 1, filters: str = None):
    query_filters, search_stage = filter_from_json_str(filters, request)
    page = max(page, 1)
    page_size = max(min(page_size, 20), 1)
    if search_stage:
        pipeline = [search_stage]
        if query_filters:
            pipeline.append({"$match": query_filters})
        pipeline.append({"$skip": (page - 1) * page_size})
        pipeline.append({"$limit": 500})
        return list(request.app.database["Archive"].aggregate(pipeline))
    else:
        return list(request.app.database["Archive"].find(query_filters).skip((page - 1) * page_size).limit(page_size))

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
    query_filters, search_stage = filter_from_json_str(filters, request)
    pipeline = []
    if search_stage:
        pipeline.append(search_stage)
    if query_filters:
        pipeline.append({"$match": query_filters})
    pipeline.append({"$sample": {"size": 1}})
    return list(request.app.database["Archive"].aggregate(pipeline))

@router.get("/count", response_description="Get the number of entries in the archive with optional filter", response_model=int)
def num_entries(request: Request, filters: str = None):
    query_filters, search_stage = filter_from_json_str(filters, request)
    pipeline = []
    if search_stage:
        pipeline.append(search_stage)
    if query_filters:
        pipeline.append({"$match": query_filters})
    pipeline.append({"$count": "total"})
    res = list(request.app.database["Archive"].aggregate(pipeline))
    return res[0]["total"] if res else 0

@router.get("/filters", response_description="Get available options for specified filter fields in the archive", response_model=dict[str, List[str]])
def get_filters(request: Request, field_to_path: str = None):
    if not field_to_path:
        return []
    populate_thesaurus_maps(request)
    field_to_path_dict: dict[str, str] = json.loads(field_to_path)
    unique_options: dict[str, list[str]] = {}
    for field_key in field_to_path_dict:
        unique_options[field_key] = list(request.app.database["Archive"].distinct(field_to_path_dict[field_key]))
        if None in unique_options[field_key]:
            unique_options[field_key].remove(None)
        # Convert options to a smaller set to resolve formatting mistakes
        if field_key in ["genre", "language_of_origin"]:
            for i, value in enumerate(unique_options[field_key]):
                unique_options[field_key][i] = mapfrom_mapto[field_key][value]

    return unique_options

@router.get("/{id}", response_description="Get a single folklore entry by id", response_model=FolkloreCollection)
def find_folklore(id: str, request: Request):
    if (folklore := request.app.database["Archive"].find_one({"_id": ObjectId(id)})) is not None:
        return folklore

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folklore with ID {id} not found")

def populate_thesaurus_maps(request):
    if len(mapto_mapfrom) != 0 or len(mapfrom_mapto) != 0:
        return
    thesaurus_documents = list(request.app.database["Thesaurus"].find())
    for entry in thesaurus_documents:
        # Populate mapto_mapfrom to support backend mapping frontend options to cleaner subset
        if entry["type"] not in mapto_mapfrom:
            mapto_mapfrom[entry["type"]] = {}
        mapto_mapfrom[entry["type"]][entry["maps_to"]] = entry["maps_from"]
        # Populate mapfrom_mapto to support mapping frontend options back to original set
        if entry["type"] not in mapfrom_mapto:
            mapfrom_mapto[entry["type"]] = {}
        for e in entry["maps_from"]:
            mapfrom_mapto[entry["type"]][e] = entry["maps_to"]

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

