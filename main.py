from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
from queue import Queue
import time
import threading
import random

fake_db = {}
order_queue = Queue()


def get_client_application():
    app = FastAPI()

    def rate_limit_key(request: Request):
        return get_remote_address(request)

    limiter = Limiter(key_func=rate_limit_key)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(
        request: Request, exc: RateLimitExceeded
    ):
        JSONResponse(
            {"error": f"Rate limit exceeded: {exc.detail}"}, status_code=429
        )
        return _rate_limit_exceeded_handler(request, exc)

    class Coffee(BaseModel):
        name: str
        description: str
        price: float

    @app.post("/order")
    @limiter.limit("10/minute")
    async def create_order(request: Request, coffee: Coffee):
        if coffee.name != "americano":
            raise HTTPException(
                status_code=400, detail="Only americano is available"
            )

        order = {"id": len(fake_db) + 1, "status": "pending", **coffee.dict()}
        fake_db[order["id"]] = order
        order_queue.put(order["id"])
        return {"message": "Order received"}

    return app


def get_worker_application():
    app = FastAPI()

    @app.get("/start")
    async def get_next_order():
        if order_queue.empty():
            return {"message": "No orders in queue"}

        order_id = order_queue.get()
        order = fake_db[order_id]
        order["status"] = "in_progress"
        return order

    @app.post("/finish")
    async def finish_order(order_id: int):
        if order_id not in fake_db:
            raise HTTPException(status_code=404, detail="Order not found")

        order = fake_db[order_id]
        order["status"] = "ready"
        time.sleep(
            random.randint(30, 60)
        )  # Simulate americano preparation time
        return order

    return app


client_app = get_client_application()
worker_app = get_worker_application()


def start_client():
    import uvicorn

    uvicorn.run(client_app, host="0.0.0.0", port=8000)


def start_worker():
    import uvicorn

    uvicorn.run(worker_app, host="0.0.0.0", port=8001)


threading.Thread(target=start_client).start()
threading.Thread(target=start_worker).start()
