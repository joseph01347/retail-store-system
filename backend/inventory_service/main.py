import sys
import os
from pathlib import Path

# Add the backend folder to path so we can import shared modules
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime

from shared.db import get_shard_connection, SHARD_CONFIGS
from shared.event_bus import event_bus

app = FastAPI(title="Inventory Service", version="1.0.0", port=8002)

# ============================================================
# CORS MIDDLEWARE (Environment-Aware)
# ============================================================

# Get the environment from .env or default to 'development'
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    # In production, ONLY allow the deployed frontend domain
    # Replace with  actual GitHub Pages or Vercel URL later
    allowed_origins = [
        "https://joseph01347.github.io",  # Example for GitHub Pages
        "https://yourdomain.com",         # Custom deployment domain if you have one
    ]
else:
    # In development, allow all origins (because of random ports)
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# PYDANTIC MODELS
# ============================================================

class ProductCreate(BaseModel):
    barcode: str = Field(..., min_length=8, max_length=20)
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    category: str
    unit_price: Decimal = Field(..., ge=0)
    cost_price: Decimal = Field(..., ge=0)
    quantity_on_hand: int = Field(default=0, ge=0)
    store_id: str

class ProductUpdate(BaseModel):
    barcode: Optional[str] = Field(None, min_length=8, max_length=20)
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    unit_price: Optional[Decimal] = Field(None, ge=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    quantity_on_hand: Optional[int] = Field(None, ge=0)
    store_id: Optional[str] = None

class ProductResponse(BaseModel):
    id: UUID
    barcode: str
    sku: str
    name: str
    category: str
    unit_price: float
    cost_price: float
    quantity_on_hand: int
    store_id: str
    created_at: datetime
    updated_at: datetime

# ============================================================
# CRUD ENDPOINTS (FIXED - No async with conn)
# ============================================================

@app.post("/products/", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    """Create a new product. Routes to correct shard based on store_id."""
    conn = None
    shard_idx = None
    try:
        # 1. Get connection to the correct shard
        conn, shard_idx = await get_shard_connection(product.store_id)
        
        # 2. Insert into the shard
        row = await conn.fetchrow(
            """
            INSERT INTO products (id, barcode, sku, name, category, unit_price, cost_price, quantity_on_hand, store_id)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, barcode, sku, name, category, unit_price, cost_price, quantity_on_hand, store_id, created_at, updated_at
            """,
            product.barcode, product.sku, product.name, product.category,
            float(product.unit_price), float(product.cost_price),
            product.quantity_on_hand, product.store_id
        )
        new_product = dict(row)
        
        # 3. Publish event to RabbitMQ
        event_bus.publish("product.created", {
            "product_id": str(new_product["id"]),
            "barcode": new_product["barcode"],
            "name": new_product["name"],
            "price": float(new_product["unit_price"]),
            "store_id": new_product["store_id"],
            "shard": shard_idx
        })
        
        return new_product
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

@app.put("/products/{product_id}")
async def update_product(product_id: UUID, product: ProductUpdate):
    """Update a product. Requires store_id to route to correct shard."""
    conn = None
    shard_idx = None
    try:
        if not product.store_id:
            raise HTTPException(status_code=400, detail="store_id is required for routing")
        
        conn, shard_idx = await get_shard_connection(product.store_id)
        
        # Build dynamic update query
        update_data = {k: v for k, v in product.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Remove store_id from update data (it's used for routing, not for updating)
        update_data.pop("store_id", None)
        
        # Convert Decimal to float for SQL
        for key in ["unit_price", "cost_price"]:
            if key in update_data and update_data[key] is not None:
                update_data[key] = float(update_data[key])
        
        # Build SET clause
        set_clause = ", ".join([f"{k} = ${i+1}" for i, k in enumerate(update_data.keys())])
        values = list(update_data.values())
        values.append(str(product_id))
        
        row = await conn.fetchrow(
            f"UPDATE products SET {set_clause}, updated_at = NOW() WHERE id = ${len(values)} RETURNING *",
            *values
        )
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        updated = dict(row)
        
        # Publish price update event if price changed
        event_bus.publish("product.price_updated", {
            "product_id": str(updated["id"]),
            "barcode": updated["barcode"],
            "new_price": float(updated["unit_price"]),
            "store_id": updated["store_id"]
        })
        
        return updated
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

@app.get("/products/", response_model=List[ProductResponse])
async def get_all_products(
    store_id: str,
    limit: int = 100,
    offset: int = 0
):
    """Get all products for a specific store. Routes to correct shard."""
    conn = None
    try:
        conn, shard_idx = await get_shard_connection(store_id)
        
        rows = await conn.fetch(
            "SELECT * FROM products WHERE store_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            store_id, limit, offset
        )
        products = [dict(row) for row in rows]
        
        return products
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

@app.get("/products/{product_id}")
async def get_product(product_id: UUID, store_id: str):
    """Get a single product. Requires store_id to route to correct shard."""
    conn = None
    try:
        conn, shard_idx = await get_shard_connection(store_id)
        
        row = await conn.fetchrow(
            "SELECT * FROM products WHERE id = $1 AND store_id = $2",
            str(product_id), store_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        product = dict(row)
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            await conn.close()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "inventory_service"}

@app.get("/shard-info/{store_id}")
async def get_shard_info(store_id: str):
    """Utility endpoint to show which shard a store_id routes to."""
    from shared.db import get_shard_index
    shard_idx = get_shard_index(store_id)
    return {
        "store_id": store_id,
        "shard": shard_idx,
        "database": SHARD_CONFIGS[shard_idx]["url"].split("@")[0].split("//")[1].split(":")[0] if "@" in SHARD_CONFIGS[shard_idx]["url"] else "unknown"
    }