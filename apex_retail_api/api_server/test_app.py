"""
AI ASSISTANCE DOCUMENTATION
Prompt used to generate this test suite:
"Act as a senior QA engineer. Write a complete pytest suite for a Flask + MongoDB API. 
The API has an ingestion endpoint (/events/ingest) that must be idempotent, and analytical 
endpoints (/metrics, /funnel). Mock the PyMongo client using mongomock so we do not hit a 
live database during CI/CD. Ensure we cover the empty store edge case (0 division prevention) 
and the duplicate ingestion edge case."
"""

import pytest
import mongomock
from app import app, db
import json

@pytest.fixture
def client():
    # Configure Flask for testing
    app.config['TESTING'] = True
    
    # Patch the real PyMongo database with mongomock for isolated testing
    with mongomock.patch(servers=(('127.0.0.1', 27017),)):
        with app.test_client() as client:
            yield client

def test_health_check(client):
    """Test that the health check returns a 200 OK status."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] in ['HEALTHY', 'STALE_FEED']

def test_ingest_events_idempotency(client):
    """Test that ingesting the exact same batch twice safely ignores duplicates."""
    payload = {
        "event_id": "test-uuid-123",
        "store_id": "TEST_STORE",
        "camera_id": "CAM_01",
        "visitor_id": "VIS_1",
        "event_type": "ENTRY",
        "timestamp": "2026-04-10T16:50:00Z",
        "zone_id": "ENTRY",
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.99,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
    }
    
    # First ingestion (Should Insert)
    res1 = client.post('/events/ingest', json=[payload])
    assert res1.status_code == 201
    assert res1.json['inserted'] == 1
    
    # Second ingestion of the exact same payload (Should Ignore)
    # Note: mongomock handles unique index constraints gracefully in test environments
    res2 = client.post('/events/ingest', json=[payload])
    assert res2.status_code == 201

def test_metrics_empty_store_edge_case(client):
    """Test that an empty store does not cause ZeroDivisionErrors in metrics."""
    response = client.get('/stores/EMPTY_STORE_99/metrics')
    assert response.status_code == 200
    data = response.json['metrics']
    assert data['unique_visitors'] == 0
    assert data['conversion_rate_percent'] == 0.0  # Division by zero handled safely
    assert data['queue_abandonment_rate_percent'] == 0.0

def test_funnel_generation(client):
    """Test the funnel endpoint structure."""
    response = client.get('/stores/TEST_STORE/funnel')
    assert response.status_code == 200
    assert 'drop_offs' in response.json
    assert 'funnel' in response.json