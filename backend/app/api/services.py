from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/services")
def list_services(request: Request) -> list[dict]:
    return [s.model_dump(mode="json") for s in request.app.state.catalog.served()]


@router.get("/services/{service_id}")
def get_service(service_id: str, request: Request) -> dict:
    rec = request.app.state.catalog.services.get(service_id)
    if rec is None or rec.status == "unverified":
        raise HTTPException(404, "Service not found")
    return rec.model_dump(mode="json")
