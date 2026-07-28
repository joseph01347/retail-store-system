from fastapi import FastAPI
from src.db import test_connection

app = FastAPI(title="Retail Store System API")

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Retail Store System!",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/db-test")
def test_supabase():
    """Test endpoint to verify Supabase connection."""
    success, message = test_connection()
    return {
        "connection_test": success,
        "message": message
    }