from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from src.db import supabase

router = APIRouter(prefix="/products", tags=["Products"])

# ============================================================
# PYDANTIC MODELS (Input/Output Validation)
# ============================================================

class ProductCreate(BaseModel):
    """Schema for creating a new product."""
    barcode: str = Field(..., min_length=8, max_length=20, description="8-20 digit barcode")
    sku: str = Field(..., min_length=1, max_length=50, description="Internal SKU code")
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    category: str = Field(..., description="Product category")
    unit_price: Decimal = Field(..., ge=0, description="Selling price (must be >= 0)")
    cost_price: Decimal = Field(..., ge=0, description="Purchase cost (must be >= 0)")
    quantity_on_hand: int = Field(default=0, ge=0, description="Current stock quantity")
    store_id: Optional[UUID] = None

class ProductUpdate(BaseModel):
    """Schema for updating an existing product. All fields optional."""
    barcode: Optional[str] = Field(None, min_length=8, max_length=20)
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    unit_price: Optional[Decimal] = Field(None, ge=0)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    quantity_on_hand: Optional[int] = Field(None, ge=0)

class ProductResponse(BaseModel):
    """Schema for product response."""
    id: UUID
    barcode: str
    sku: str
    name: str
    category: str
    unit_price: Decimal
    cost_price: Decimal
    quantity_on_hand: int
    store_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def sanitize_data(data: dict) -> dict:
    """
    Converts Decimal values to float for Supabase JSON serialization.
    Also handles UUID conversion.
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, Decimal):
            sanitized[key] = float(value)
        elif isinstance(value, UUID):
            sanitized[key] = str(value)
        else:
            sanitized[key] = value
    return sanitized

# ============================================================
# CRUD OPERATIONS
# ============================================================

@router.get("/", response_model=List[ProductResponse])
async def get_all_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Max results (1-1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    try:
        query = supabase.table("products").select("*", count="exact")
        
        if category:
            query = query.eq("category", category)
            
        result = query.limit(limit).offset(offset).execute()
        
        return result.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve products: {str(e)}")

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID):
    try:
        result = supabase.table("products").select("*").eq("id", str(product_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"No product found with ID: {product_id}")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve product: {str(e)}")

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    try:
        # Check if barcode already exists
        existing = supabase.table("products").select("id").eq("barcode", product.barcode).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail=f"A product with barcode '{product.barcode}' already exists")
        
        # Sanitize data (converts Decimal → float for Supabase)
        insert_data = sanitize_data(product.dict())
        
        result = supabase.table("products").insert(insert_data).execute()
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: UUID, product: ProductUpdate):
    try:
        # Verify product exists
        existing = supabase.table("products").select("id, barcode").eq("id", str(product_id)).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail=f"No product found with ID: {product_id}")
        
        # Build update dict (only non-None fields)
        update_data = {k: v for k, v in product.dict().items() if v is not None}
        
        # Return 400 if no fields provided
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided to update. Send at least one field.")
        
        # Sanitize data (converts Decimal → float for Supabase)
        update_data = sanitize_data(update_data)
        
        # Check barcode uniqueness if it's being updated
        if update_data.get("barcode"):
            barcode_check = (
                supabase.table("products")
                .select("id")
                .eq("barcode", update_data["barcode"])
                .neq("id", str(product_id))
                .execute()
            )
            if barcode_check.data:
                raise HTTPException(status_code=409, detail=f"Another product already uses barcode '{update_data['barcode']}'")
        
        result = supabase.table("products").update(update_data).eq("id", str(product_id)).execute()
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")

@router.delete("/{product_id}")
async def delete_product(product_id: UUID):
    try:
        result = supabase.table("products").delete().eq("id", str(product_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"No product found with ID: {product_id}")
        
        return {"message": "Product deleted successfully", "id": str(product_id), "deleted_product": result.data[0]["name"]}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")