FROM tiangolo/uvicorn-gunicorn-fastapi:latest

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["uvicorn", "main:client_app", "--host", "0.0.0.0", "--port", "8000"]