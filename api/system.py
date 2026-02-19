from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health check")
def health_check():
    return {"status": "healthy"}


@router.get("/version", summary="API version")
def version():
    return {"version": "2.0.0", "engine": "SaaS Document Generation Engine"}
# from fastapi import APIRouter

# router = APIRouter()

# @router.get("/health")
# def health_check():
#     return {"status": "healthy"}

# @router.get("/version")
# def version():
#     return {"version": "1.0.0"}
