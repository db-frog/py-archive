from bson import ObjectId
from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from typing import List
from fastapi.responses import StreamingResponse
from sentence_transformers import SentenceTransformer

import json

from .models import FolkloreCollection

router = APIRouter()

# Store thesaurus mapping to avoid repeated DB queries + small size
mapto_mapfrom : dict[str, dict[str, List[str]]] = {}
mapfrom_mapto : dict[str, dict[str, str]] = {}

# Load an open-source embedding model
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)

@router.get("/", response_description="List all folklore based on an optional filter", response_model=List[FolkloreCollection])
def list_folklore(request: Request, filters: str = None):
    query_filters, search_stage = filter_from_json_str(filters, request)
    if not search_stage:
        return list(request.app.database["Archive"].find(query_filters).limit(500))
    pipeline = build_pipeline(query_filters, search_stage, [{"$limit": 500}])
    return list(request.app.database["Archive"].aggregate(pipeline))

@router.get("/paginated", response_description="List folklore specified by page size, page, and optional filters", response_model=List[FolkloreCollection])
def list_paginated_folklore(request: Request, page_size: int = 20, page: int = 1, filters: str = None):
    query_filters, search_stage = filter_from_json_str(filters, request)
    page = max(page, 1)
    page_size = max(min(page_size, 20), 1)
    if not search_stage:
        return list(request.app.database["Archive"].find(query_filters).skip((page - 1) * page_size).limit(page_size))
    extra_stages = [{"$skip": (page - 1) * page_size}, {"$limit": page_size}]
    pipeline = build_pipeline(query_filters, search_stage, extra_stages)
    return list(request.app.database["Archive"].aggregate(pipeline))

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
def random_folklore(request: Request, filters: str = None, folder_path_str: str = None):
    # Only allow 1 query parameter, either filters for map/table view or folder for index view
    pipeline = []
    if folder_path_str:
        folder_path = json.loads(folder_path_str)
        folder_dict : dict[str, str] = {}
        # Query to find documents in same folder path
        for i, folder in enumerate(folder_path):
            if i == 0: folder_dict["archive_index.geography"] = folder
            elif i == 1: folder_dict["archive_index.genre"] = folder
            else: folder_dict[f"archive_index.sub_category_{i - 1}"] = folder
        pipeline.append({"$match": folder_dict})
    else:
        query_filters, search_stage = filter_from_json_str(filters, request)
        pipeline = build_pipeline(query_filters, search_stage)
    pipeline.append({"$sample": {"size": 1}})
    return list(request.app.database["Archive"].aggregate(pipeline))

@router.get("/count", response_description="Get the number of entries in the archive with optional filter", response_model=int)
def num_entries(request: Request, filters: str = None):
    query_filters, search_stage = filter_from_json_str(filters, request)
    pipeline = build_pipeline(query_filters, search_stage, [{"$count": "total"}])
    res = list(request.app.database["Archive"].aggregate(pipeline))
    return res[0]["total"] if res else 0

@router.get("/folderContents", response_description="Get the name of folders or entries in the current folder path specified by query parameter", response_model=List[str | FolkloreCollection])
def get_folder_names(request: Request, folder_path_str: str = None, return_elems: bool = False):
    if not folder_path_str: folder_path = []
    else: folder_path = json.loads(folder_path_str)

    # No need for match pipeline
    if len(folder_path) == 0:
        res = list(request.app.database["Archive"].distinct("archive_index.geography"))
        return res
    
    folder_dict : dict[str, str] = {}
    next_layer : str = ""
    # Query to find documents in same folder path
    for i, folder in enumerate(folder_path):
        if i == 0:
            folder_dict["archive_index.geography"] = folder
            next_layer = "archive_index.genre"
        elif i == 1:
            folder_dict["archive_index.genre"] = folder
            next_layer = "archive_index.sub_category_1"
        else:
            folder_dict[f"archive_index.sub_category_{i - 1}"] = folder
            next_layer = f"archive_index.sub_category_{i}"
    pipeline = [{"$match": folder_dict}]
    if not return_elems:
        pipeline.append({"$group": {"_id": f"${next_layer}"}})
    res = list(request.app.database["Archive"].aggregate(pipeline))
    if return_elems:
        return res
    res = [e["_id"] for e in res if e["_id"] is not None]
    return res

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

'''
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
'''

# Helper functions

# Converts filter string into query dictionary for mongodb
def filter_from_json_str(filters: str, request: Request):
    if not filters:
        return {}
    populate_thesaurus_maps(request)
    filters_dict: dict[str, List[str] | str] = json.loads(filters)
    query_filters = {} # Need to remove empty filters
    search_stage = None # If cleaned_full_text is in filters

    # Only 1 search stage allowed
    for field_key, values in filters_dict.items():
        if not values:
            continue
        if field_key == "cleaned_full_text":
            search_stage = { "$search": { "index": "search", "text": {
                "query": values,
                "path": "cleaned_full_text"
            }}}
        elif field_key == "cleaned_full_text_embedding":
            query_embedding = model.encode(values, precision="float32").tolist()
            search_stage = {
                "$vectorSearch": {
                    "index": "vector_text",
                    "queryVector": query_embedding,
                    "path": field_key,
                    "exact": False,
                    "limit": 10,
                    "numCandidates": 100,
                }
            }
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

# Template for building mongodb pipeline
def build_pipeline(query_filters: dict, search_stage: dict, extra_stages: List[dict] = []):
    pipeline = []
    if search_stage:
        pipeline.append(search_stage)
    if query_filters:
        pipeline.append({"$match": query_filters})
    pipeline.extend(extra_stages)
    return pipeline

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