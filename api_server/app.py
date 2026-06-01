from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from datetime import datetime, timezone, timedelta
import os

app = Flask(__name__)

# Database Connection
client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/"))
db = client["apex_retail"]
events_collection = db["cv_events"]
pos_collection = db["pos_transactions"]

# ==========================================
# HEALTH & INGESTION (Existing)
# ==========================================

@app.route('/health', methods=['GET'])
def health_check():
    try:
        client.admin.command('ping')
        latest_event = events_collection.find_one(sort=[("timestamp", -1)])
        status = "HEALTHY"
        
        if latest_event:
            last_time = latest_event.get("timestamp")
            if hasattr(last_time, 'tzinfo') and last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - last_time).total_seconds() > 600:
                status = "STALE_FEED"

        return jsonify({"status": status, "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "UNHEALTHY", "error": str(e)}), 500

@app.route('/events/ingest', methods=['POST'])
def ingest_events():
    data = request.json
    if not isinstance(data, list): data = [data]
    if not data: return jsonify({"error": "Empty payload"}), 400

    for event in data:
        if isinstance(event.get('timestamp'), str):
            event['timestamp'] = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))

    try:
        result = events_collection.insert_many(data, ordered=False)
        return jsonify({"status": "success", "inserted": len(result.inserted_ids), "duplicates_ignored": 0}), 201
    except BulkWriteError as bwe:
        write_errors = bwe.details.get('writeErrors', [])
        duplicates = len([e for e in write_errors if e['code'] == 11000])
        return jsonify({"status": "success", "inserted": bwe.details.get('nInserted', 0), "duplicates_ignored": duplicates}), 201

# ==========================================
# INTELLIGENCE ANALYTICS (New)
# ==========================================

@app.route('/stores/<store_id>/metrics', methods=['GET'])
def get_metrics(store_id):
    """Calculates North Star offline metrics for a specific store."""
    
    # 1. Unique Visitors (Excluding staff)
    unique_visitors = len(events_collection.distinct("visitor_id", {
        "store_id": store_id, 
        "event_type": "ENTRY",
        "is_staff": False
    }))

    # 2. Average Dwell Time (Aggregation pipeline)
    dwell_pipeline = [
        {"$match": {"store_id": store_id, "event_type": "ZONE_DWELL", "is_staff": False}},
        {"$group": {"_id": "$visitor_id", "max_dwell": {"$max": "$dwell_ms"}}},
        {"$group": {"_id": None, "avg_dwell": {"$avg": "$max_dwell"}}}
    ]
    dwell_res = list(events_collection.aggregate(dwell_pipeline))
    avg_dwell_ms = dwell_res[0]['avg_dwell'] if dwell_res else 0

    # 3. Queue Analytics
    joins = events_collection.count_documents({"store_id": store_id, "event_type": "BILLING_QUEUE_JOIN"})
    abandons = events_collection.count_documents({"store_id": store_id, "event_type": "BILLING_QUEUE_ABANDON"})
    
    # 4. Total Unique Purchases (POS Data)
    unique_purchases = len(pos_collection.distinct("order_id", {"store_id": store_id}))

    # 5. Calculations
    queue_depth = max(0, joins - abandons - unique_purchases)
    abandonment_rate = (abandons / joins * 100) if joins > 0 else 0
    conversion_rate = (unique_purchases / unique_visitors * 100) if unique_visitors > 0 else 0

    return jsonify({
        "store_id": store_id,
        "metrics": {
            "unique_visitors": unique_visitors,
            "avg_dwell_seconds": round(avg_dwell_ms / 1000, 2),
            "conversion_rate_percent": round(conversion_rate, 2),
            "current_queue_depth": queue_depth,
            "queue_abandonment_rate_percent": round(abandonment_rate, 2)
        }
    }), 200

@app.route('/stores/<store_id>/funnel', methods=['GET'])
def get_funnel(store_id):
    """Maps the spatial conversion funnel: Entry -> Zone -> Billing -> Purchase"""
    
    # Step 1: Store Entry
    entries = len(events_collection.distinct("visitor_id", {"store_id": store_id, "event_type": "ENTRY", "is_staff": False}))
    
    # Step 2: Zone Engagement (Did they browse the racks?)
    zone_visits = len(events_collection.distinct("visitor_id", {"store_id": store_id, "event_type": "ZONE_ENTER", "is_staff": False}))
    
    # Step 3: Intent to Buy (Joined queue)
    billing_queue = len(events_collection.distinct("visitor_id", {"store_id": store_id, "event_type": "BILLING_QUEUE_JOIN", "is_staff": False}))
    
    # Step 4: Actual Purchase (From POS database)
    purchases = len(pos_collection.distinct("order_id", {"store_id": store_id}))

    return jsonify({
        "store_id": store_id,
        "funnel": {
            "1_entries": entries,
            "2_zone_visits": zone_visits,
            "3_billing_queue": billing_queue,
            "4_purchases": purchases
        },
        "drop_offs": {
            "entry_to_zone": max(0, entries - zone_visits),
            "zone_to_billing": max(0, zone_visits - billing_queue),
            "billing_to_purchase": max(0, billing_queue - purchases)
        }
    }), 200

@app.route('/stores/<store_id>/anomalies', methods=['GET'])
def get_anomalies(store_id):
    """Detects operational anomalies using statistical thresholds."""
    anomalies = []
    
    # 1. Fetch current baseline metrics
    joins = events_collection.count_documents({"store_id": store_id, "event_type": "BILLING_QUEUE_JOIN"})
    abandons = events_collection.count_documents({"store_id": store_id, "event_type": "BILLING_QUEUE_ABANDON"})
    purchases = len(pos_collection.distinct("order_id", {"store_id": store_id}))
    
    queue_depth = max(0, joins - abandons - purchases)
    abandonment_rate = (abandons / joins * 100) if joins > 0 else 0
    
    # 2. Rule 1: Queue Spike (More than 10 people in line)
    if queue_depth > 10:
        anomalies.append({
            "type": "QUEUE_SPIKE",
            "severity": "HIGH",
            "message": f"Critical queue buildup detected. Current depth: {queue_depth}."
        })
        
    # 3. Rule 2: High Abandonment (Over 15% of people leaving the line)
    if abandonment_rate > 15.0:
        anomalies.append({
            "type": "HIGH_ABANDONMENT",
            "severity": "CRITICAL",
            "message": f"Customers are abandoning the billing queue at a {round(abandonment_rate, 1)}% rate."
        })

    # 4. Rule 3: Dead Zones (Zones with visitors but 0 average dwell time)
    zone_visits = events_collection.aggregate([
        {"$match": {"store_id": store_id, "event_type": "ZONE_ENTER"}},
        {"$group": {"_id": "$zone_id", "count": {"$sum": 1}}}
    ])
    
    for zone in zone_visits:
        zone_id = zone["_id"]
        # Check if there are any DWELL events for this zone
        dwells = events_collection.count_documents({"store_id": store_id, "zone_id": zone_id, "event_type": "ZONE_DWELL"})
        if dwells == 0 and zone["count"] > 0:
            anomalies.append({
                "type": "DEAD_ZONE",
                "severity": "MEDIUM",
                "message": f"Zone '{zone_id}' has traffic but 0 recorded dwell time."
            })

    return jsonify({
        "store_id": store_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_anomalies": anomalies
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)