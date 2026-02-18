from fastapi import APIRouter

router = APIRouter()

@router.get("/schema")
def get_metadata_schema():
    return {
        "required_fields": [
            "company_name",
            "version",
            "effective_date"
        ]
    }
