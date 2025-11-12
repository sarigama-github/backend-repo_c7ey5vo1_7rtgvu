import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import create_document, get_documents

app = FastAPI(title="Panda Vapes API", description="API for Panda Vapes store", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VapeQuery(BaseModel):
    search: Optional[str] = None
    brand: Optional[str] = None
    flavor: Optional[str] = None
    nicotine_strength: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = 24


@app.get("/")
def read_root():
    return {"message": "Panda Vapes API is running"}


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
        from database import db

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

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.get("/api/products")
async def list_products(search: Optional[str] = None,
                        brand: Optional[str] = None,
                        flavor: Optional[str] = None,
                        nicotine_strength: Optional[str] = None,
                        min_price: Optional[float] = None,
                        max_price: Optional[float] = None,
                        limit: int = 24):
    """List vape products with optional filters"""
    filter_dict = {"category": "disposable"}

    if search:
        # Basic text search across fields
        filter_dict["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"brand": {"$regex": search, "$options": "i"}},
            {"flavor": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]

    if brand:
        filter_dict["brand"] = {"$regex": f"^{brand}$", "$options": "i"}
    if flavor:
        filter_dict["flavor"] = {"$regex": flavor, "$options": "i"}
    if nicotine_strength:
        filter_dict["nicotine_strength"] = {"$regex": nicotine_strength, "$options": "i"}

    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        filter_dict["price"] = price_filter

    docs = await get_documents("vapeproduct", filter_dict, limit)
    return {"items": docs}


class NewVapeProduct(BaseModel):
    title: str
    brand: str
    description: Optional[str] = None
    price: float
    flavor: str
    nicotine_strength: str
    puff_count: Optional[int] = None
    image_url: Optional[str] = None
    in_stock: bool = True
    rating: Optional[float] = 4.5
    category: str = "disposable"


@app.post("/api/products")
async def create_product(product: NewVapeProduct):
    doc = await create_document("vapeproduct", product.dict())
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create product")
    return doc


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
