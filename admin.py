from fastapi import APIRouter

admin_router = APIRouter()

@admin_router.get("/admin/dashboard")
def get_dashboard():
    return {"message": "Welcome to the Admin Dashboard"}
