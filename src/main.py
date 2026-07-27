from fastapi import FastAPI

app = FastAPI(title="Retail Store System API")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Retail Store System!", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}