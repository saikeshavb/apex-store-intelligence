import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timezone
import os

def ingest_pos_data(csv_file_path):
    print(f"Reading POS data from {csv_file_path}...")
    
    try:
        # Read the CSV using pandas
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Error: Could not find {csv_file_path}. Make sure it is in the api_server folder.")
        return

    # Connect to MongoDB
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/"))
    db = client["apex_retail"]
    pos_collection = db["pos_transactions"]

    # Clear existing data so we don't duplicate on multiple runs
    pos_collection.delete_many({})
    print("Cleared existing POS records to ensure a clean state.")

    records_to_insert = []
    
    # Process each row
    for index, row in df.iterrows():
        # Combine date and time strings (Format in CSV: DD-MM-YYYY and HH:MM:SS)
        date_str = str(row['order_date'])
        time_str = str(row['order_time'])
        
        try:
            # Parse into a timezone-aware datetime object
            combined_dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M:%S")
            combined_dt = combined_dt.replace(tzinfo=timezone.utc)
        except ValueError as e:
            print(f"Skipping row {index} due to date parsing error: {e}")
            continue

        # Extract only the necessary business fields for our analytics
        transaction_doc = {
            "order_id": str(row['order_id']),
            "store_id": str(row['store_id']),
            "order_time": combined_dt,
            "customer_number": str(row['customer_number']) if pd.notna(row['customer_number']) else None,
            "product_name": str(row['product_name']),
            "qty": int(row['qty']) if pd.notna(row['qty']) else 1,
            "total_amount": float(row['total_amount']) if pd.notna(row['total_amount']) else 0.0
        }
        records_to_insert.append(transaction_doc)

    # Bulk insert into MongoDB
    if records_to_insert:
        result = pos_collection.insert_many(records_to_insert)
        print(f"Successfully ingested {len(result.inserted_ids)} POS transactions into the database.")
    else:
        print("No valid records found to insert.")

if __name__ == "__main__":
    ingest_pos_data("pos_data.csv")