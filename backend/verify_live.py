import urllib.request
import json

def verify():
    # 1. Health endpoint
    with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health") as res:
        assert res.status == 200
        data = json.loads(res.read().decode("utf-8"))
        print(f"Health Check: status={data['status']}, db_connected={data['database_connected']}")
        assert data["database_connected"] is True

    # 2. Schemes endpoint
    with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/schemes") as res:
        assert res.status == 200
        schemes_data = json.loads(res.read().decode("utf-8"))
        print(f"Schemes Loaded: total={schemes_data['total']}")
        assert schemes_data["total"] >= 8

    # 3. Session Init endpoint
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/sessions/init",
        data=json.dumps({"preferred_language": "hi", "consent_given": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        sess_data = json.loads(res.read().decode("utf-8"))
        print(f"Session Created: id={sess_data['session_id']}, citizen={sess_data['citizen_id']}")
        assert sess_data["status"] == "active"

    print("ALL LIVE ENDPOINTS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    verify()
