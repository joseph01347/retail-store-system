from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.db import test_connection
from src.routes.products import router as products_router

app = FastAPI(title="Retail Store System API", version="1.0.0")

# ============================================================
# GLOBAL EXCEPTION HANDLER FOR VALIDATION ERRORS
# ============================================================

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """
    Converts Pydantic validation errors into clean, user-friendly messages.
    This catches wrong datatypes, missing fields, invalid values, etc.
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        # Make messages more readable
        if "missing" in message.lower():
            message = f"Field '{field}' is required"
        elif "not a valid decimal" in message.lower() or "not a valid number" in message.lower():
            message = f"Field '{field}' must be a number (got: {error.get('input', 'unknown')})"
        elif "not a valid integer" in message.lower():
            message = f"Field '{field}' must be a whole number (got: {error.get('input', 'unknown')})"
        elif "ensure this value is greater than" in message.lower() or "greater than or equal" in message.lower():
            message = f"Field '{field}' must be a positive number"
        errors.append({"field": field, "message": message})
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": errors,
            "hint": "Check the data types and required fields in your request."
        }
    )

# ============================================================
# INCLUDE ROUTERS
# ============================================================

app.include_router(products_router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Retail Store System!",
        "status": "running",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/db-test")
def test_supabase():
    success, message = test_connection()
    return {"connection_test": success, "message": message}

@app.get("/api-info")
def get_api_info():
    return {
        "title": "Retail Store System API",
        "version": "1.0.0",
        "endpoints": {
            "products": [
                {"path": "/products/", "method": "GET", "description": "List all products"},
                {"path": "/products/{id}", "method": "GET", "description": "Get single product"},
                {"path": "/products/", "method": "POST", "description": "Create new product"},
                {"path": "/products/{id}", "method": "PUT", "description": "Update product"},
                {"path": "/products/{id}", "method": "DELETE", "description": "Delete product"},
            ],
            "system": [
                {"path": "/", "method": "GET"},
                {"path": "/health", "method": "GET"},
                {"path": "/db-test", "method": "GET"},
            ]
        }
    }