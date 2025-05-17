from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from db import ResponsesColl


admin_router = APIRouter()
templates = Jinja2Templates(directory="templates/admin")

@admin_router.get("/admin/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    # Fetch all documents from responses collection
    response_docs = list(ResponsesColl.find({}))
    print("Response documents fetched from MongoDB:", response_docs)
    # Convert ObjectId to string for JSON
    for doc in response_docs:
        doc["_id"] = str(doc["_id"])
        doc["total_weight"] = sum(item.get("weight", 0) for item in doc.get("data", []))


    return templates.TemplateResponse("admin_table.html", {
        "request": request,
        "data": response_docs
    })
