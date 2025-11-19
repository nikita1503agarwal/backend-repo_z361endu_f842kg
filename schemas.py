"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal, Union


# -----------------------------
# Core models for API Tester
# -----------------------------

HttpMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]

class RequestConfig(BaseModel):
    url: str = Field(..., description="Target API URL")
    method: HttpMethod = Field("GET")
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Union[Dict[str, Any], str]] = Field(
        default=None, description="Request body as JSON object or raw string"
    )

class RequestHistory(BaseModel):
    """
    Collection name: "requesthistory"
    Stores each executed request plus response summary.
    """
    request: RequestConfig
    response_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    response_body: Optional[Union[Dict[str, Any], str]] = None

class CollectionItem(BaseModel):
    title: str = Field(..., description="Label for this saved request")
    request: RequestConfig

class Collection(BaseModel):
    """
    Collection name: "collection"
    Represents a folder of saved API requests.
    """
    name: str
    description: Optional[str] = None
    items: List[CollectionItem] = Field(default_factory=list)


# Example schemas kept for reference; not used directly by the app
class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# --------------------------------------------------
