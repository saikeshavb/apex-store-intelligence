from pymongo import MongoClient
import pymongo
import os

def setup_database():
    print("Connecting to MongoDB...")
    
    # CRITICAL FIX: Use Docker's environment variable, fallback to localhost if running locally
    mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
    client = MongoClient(mongo_uri)
    
    db = client["apex_retail"]
    
    # Collection for CV Events
    events_collection = db["cv_events"]
    # Collection for POS Data
    pos_collection = db["pos_transactions"]

    print("Building strict idempotency indices...")
    events_collection.create_index([("event_id", pymongo.ASCENDING)], unique=True)
    events_collection.create_index([("store_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])
    events_collection.create_index([("visitor_id", pymongo.ASCENDING)])
    pos_collection.create_index([("order_time", pymongo.ASCENDING)])

    print("Database setup complete and ready for ingestion.")

if __name__ == "__main__":
    setup_database()