from fastapi import FastAPI, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import os

app = FastAPI()
# Add session middleware (secret key is used to sign the session data)
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
templates = Jinja2Templates(directory="templates")

MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["questiondb"]
users = db["users"]
questions_collection = db["question"]
responses = db["responses"]
save = db["save"]

# GET METHODS
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/questions", response_class=HTMLResponse)
def questionPage(request: Request):
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)
    # Fetch all questions from MongoDB
    questions = questions_collection.find().to_list(100)
    saved_responses = list(responses.find({"email": request.session.get("email"),"application" : request.session["application_name"] },  {"_id": 0}))
    return templates.TemplateResponse("question.html", {"request": request, "questions": questions, "saved_responses": saved_responses})    

@app.get("/instructions", response_class=HTMLResponse)
def instructions(request: Request):
    if not request.session.get("email"):
        return RedirectResponse(url="/", status_code=303)

    # Fetch app names for this email
    cursor = responses.find({"email": request.session.get("email")}, {"application": 1, "_id": 0})
    appnames = [doc.get("application") for doc in cursor]

    return templates.TemplateResponse("instructions.html", {"request": request, "appnames": appnames}) 

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}

# POST METHODS
@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    user = users.find_one({"email": email, "password": password})
    if not user:
        # Show error on login page
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "message": "Invalid email or password"}
        )

    # Save session
    request.session["email"] = user["email"]
    request.session["username"] = user["username"]

    # Redirect to questions
    return RedirectResponse(url="/instructions", status_code=303)


@app.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    email = form_data.get("email")
    title = form_data.get("title")
    vendor = form_data.get("vendor")
    phone = form_data.get("phone")
    password = form_data.get("password")

    existing_user = users.find_one({"email": username})
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "message": "User already exists."})

    users.insert_one({"email": email,"username": username, "title": title, "vendor": vendor, "phone": phone, "password": password})
    return templates.TemplateResponse("login.html", {"request": request, "message": "Registration successful! Please log in."})

@app.post("/load-application", response_class=HTMLResponse)
async def load_application(request: Request, application_name: str = Form(...), application_name_text: str = Form(...)):
    if not request.session.get("email"):
        raise HTTPException(status_code=401, detail="Not logged in")
    print(application_name, application_name_text)
    if application_name == "new_app_name":
        request.session["application_name"] = application_name_text
    else:
        request.session["application_name"] = application_name
    email = request.session.get("email")
    
    existing = responses.find_one({
        "email": email,
        "application": request.session["application_name"]
    })

    update_data = {
        "email": email,
        "application": request.session["application_name"],
        "data": [],
        "is_submitted": False
    }

    if not existing :
        responses.update_one(
            {"email": email, "application": request.session["application_name"]},
            {"$set": update_data},
            upsert=True
        )

    return RedirectResponse(url="/questions", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/submit-answers")
async def submit_answers(request: Request):
    form_data = await request.form()
    data = build_data(form_data)
    is_submitted = form_data.get("action") == "submit"
    email = request.session.get("email")
    
    # Data to be updated
    update_data = {
        "data": data,
        "is_submitted": is_submitted
    }

    result = responses.update_one(
        {"email": email,"application" : request.session.get("application_name")},  # Filter by email
        {"$set": update_data},  # Fields to update
        upsert=True  # Insert if not found
    )

    if is_submitted:
        return RedirectResponse(url="/questions?submit=true", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/questions?save=true", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/add-comment")
async def add_comment(request: Request):
    data = await request.json()
    question_id = data["question_id"]
    comment = data["comment"]
    # Update MongoDB
    responses.update_one(
        {"email" : request.session.get("email"), "data.question_id": int(question_id)},
        {"$push": 
            {"data.$.comments": 
                {
                "text" : comment, 
                "sender" : request.session.get("username")
                }
            }
        }
    )

    return JSONResponse(content={"success": True})

@app.post("/save-response")
async def save_response(request: Request):
    data = await request.json()
    response = data["response"]
    print(responses)
    update_data = {
        "data": response,
        "is_submitted": False
    }
    result = responses.update_one(
        {"email": request.session.get("email"),"application" : request.session.get("application_name")},
        {"$set": update_data},  # Fields to update
        upsert=True  # Insert if not found
    )


    return JSONResponse(content={"success": True})

# Utility functions from here
def build_data(form_data):
    print(form_data)
    data = []
    for key, value in form_data.items():
        print(key, value)
        if key.startswith('question_'):  # If the key represents a question answer
            question_id = key.split('_')[1]  # Extract question ID from the key
            question = form_data.get(f"question_{question_id}")  # Get the question text
            print("question")
            # if it is text based question let's insert here itself 
            if 'text' in key:
                print("text")
                question_id = key.split('_')[2] 
                question = form_data.get(f"question_{question_id}") 
                answer = form_data.get(f"question_text_{question_id}")
                data.append({
                    "question_id": int(question_id),
                    "question": question,
                    "answer": answer
                })
                continue
        elif key.startswith('option_'):
            print("option")
            option = form_data.get(f"option_{question_id}")  # Check if an option is selected
            option_value, option_weight = option.split('|')
            weight = int(option_weight)
            answer = option_value
        elif key.startswith('additionalinfo_'):
            additional_info = form_data.get(f"additionalinfo_{question_id}")
            print("additionalinfo")
            data.append({
                "question_id": int(question_id),
                "question": question,
                "answer": answer,
                "additional_info" : additional_info if additional_info else "",
                "weight": weight if weight is not None else ""
            })
    return data

