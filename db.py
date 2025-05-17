import os
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI")
if MONGO_URI is None:
    raise ValueError("MONGO_URI environment variable not set.")

client = MongoClient(MONGO_URI)
db = client["questiondb"]

# Collections
UsersColl = db["users"]
QuestionsColl = db["question"]
ResponsesColl = db["responses"]