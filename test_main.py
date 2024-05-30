from fastapi.testclient import TestClient

from main import get_client_application, get_worker_application


def test_create_order():
    client_app = get_client_application()
    client = TestClient(client_app)
    response = client.post(
        "/order",
        json={"name": "americano", "description": "yum", "price": 4.00},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Order received"}


def test_rate_limiting():
    client_app = get_client_application()
    normal_client = TestClient(client_app)
    ddoser_client = TestClient(
        client_app, base_url="http://DELUSIONAL_DDOSER_IP"
    )

    for _ in range(10):
        response = normal_client.post(
            "/order",
            json={"name": "americano", "description": "yum", "price": 4.00},
        )
        assert response.status_code == 200

    for _ in range(11):
        response = ddoser_client.post(
            "/order",
            json={"name": "americano", "description": "yum", "price": 4.00},
        )
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]


def test_worker_flow():
    client_app = get_client_application()
    worker_app = get_worker_application()
    client = TestClient(client_app)
    worker = TestClient(worker_app)

    response = client.post(
        "/order",
        json={"name": "americano", "description": "yum", "price": 4.00},
    )
    assert response.status_code == 200

    response = worker.get("/start")
    assert response.status_code == 200
    order = response.json()
    assert order["status"] == "in_progress"

    response = worker.post(f"/finish?order_id={order['id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
