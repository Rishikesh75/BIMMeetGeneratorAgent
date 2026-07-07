from fastapi import FastAPI

from app.routers.ifc import router as ifc_router

app = FastAPI(title="BIMMeet Generator API", version="1.0.0")
app.include_router(ifc_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to BIMMeet Generator API",
        "docs": "/docs",
    }