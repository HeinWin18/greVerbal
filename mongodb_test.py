import certifi
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("MONGODB_URI")
database_name = os.getenv("MONGODB_DATABASE", "gre_planner")

if not uri:
    raise SystemExit("ERROR: MONGODB_URI is missing from .env")

try:
    client = MongoClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,
    )

    # Verify that Atlas is reachable
    client.admin.command("ping")
    print("SUCCESS: Connected to MongoDB Atlas!")

    # Use the same database and collection shown in Atlas
    db = client[database_name]
    collection = db["connectionTests"]

    # Write a test document
    test_document = {
        "message": "GRE Planner MongoDB connection test",
        "test": True
    }

    result = collection.insert_one(test_document)
    print("SUCCESS: Inserted document ID:", result.inserted_id)

    # Read the document back
    saved_document = collection.find_one({"_id": result.inserted_id})
    print("SUCCESS: Read document back:", saved_document)

    print("\nTEST PASSED: MongoDB can connect, write, and read!")

except Exception as error:
    print("TEST FAILED:", type(error).__name__)
    print("Details:", str(error))
finally:
    if "client" in locals():
        client.close()
