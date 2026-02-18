from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "healthy"}

@router.get("/version")
def version():
    return {"version": "1.0.0"}
