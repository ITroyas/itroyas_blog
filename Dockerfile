FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static/upload

CMD ["gunicorn", "--workers=2", "--bind=0.0.0.0:5000", "app:app"]
