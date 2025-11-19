import os
import time
from typing import Optional, Dict, Any, Union, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests

from database import db, create_document, get_documents
from schemas import RequestConfig, RequestHistory, Collection, CollectionItem

app = FastAPI(title="API Testing Tool Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "API Testing Tool Backend is running"}


# ---- Health & DB test ----
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ---- Proxy endpoint to execute requests ----
class ExecuteRequestBody(RequestConfig):
    save: bool = Field(default=True, description="Save to history")


@app.post("/proxy")
def proxy_request(payload: ExecuteRequestBody):
    method = payload.method.upper()
    url = payload.url
    headers = payload.headers or {}
    params = payload.params or {}

    data = None
    json_body = None
    if payload.body is not None:
        if isinstance(payload.body, dict):
            json_body = payload.body
        else:
            data = str(payload.body)

    start = time.time()
    try:
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_body,
            data=data,
            timeout=30,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Request failed: {str(e)}")

    elapsed_ms = int((time.time() - start) * 1000)

    # Build response summary
    response_headers = {k: v for k, v in resp.headers.items()}
    response_status = resp.status_code

    # Try to parse JSON, else return text
    response_body: Union[Dict[str, Any], str]
    try:
        response_body = resp.json()
    except ValueError:
        response_body = resp.text

    history_doc = RequestHistory(
        request=RequestConfig(
            url=url,
            method=method,  # type: ignore
            headers=headers,
            params=params,
            body=payload.body,
        ),
        response_status=response_status,
        response_time_ms=elapsed_ms,
        response_headers=response_headers,
        response_body=response_body,
    )

    if payload.save:
        try:
            create_document("requesthistory", history_doc)
        except Exception as e:
            # Don't fail the proxy if saving fails; just include info
            pass

    return {
        "status": response_status,
        "time_ms": elapsed_ms,
        "headers": response_headers,
        "body": response_body,
    }


# ---- History endpoints ----
@app.get("/history")
def list_history(limit: int = 50):
    try:
        docs = get_documents("requesthistory", limit=limit)
    except Exception as e:
        docs = []
    # Convert ObjectId and datetime to strings
    def normalize(doc):
        d = dict(doc)
        for k, v in list(d.items()):
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        if "_id" in d:
            d["_id"] = str(d["_id"])
        return d

    return [normalize(x) for x in docs][::-1]


# ---- Collections endpoints ----
class CreateCollectionBody(BaseModel):
    name: str
    description: Optional[str] = None


@app.post("/collections")
def create_collection(body: CreateCollectionBody):
    col = Collection(name=body.name, description=body.description, items=[])
    try:
        inserted_id = create_document("collection", col)
        return {"id": inserted_id, "message": "Collection created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections")
def get_collections():
    try:
        docs = get_documents("collection")
    except Exception as e:
        docs = []

    def normalize(doc):
        d = dict(doc)
        for k, v in list(d.items()):
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        if "_id" in d:
            d["_id"] = str(d["_id"])
        return d

    return [normalize(x) for x in docs]


class AddItemBody(BaseModel):
    collection_id: str = Field(..., description="Not used directly by Mongo helper; included for clarity")
    title: str
    request: RequestConfig


@app.post("/collections/add-item")
def add_item_to_collection(body: AddItemBody):
    # Manual update using pymongo client since helpers are simple
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    from bson import ObjectId

    try:
        db["collection"].update_one(
            {"_id": ObjectId(body.collection_id)},
            {"$push": {"items": {"title": body.title, "request": body.request.model_dump()}}},
        )
        return {"message": "Item added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Maintain compatibility with earlier hello route
@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
