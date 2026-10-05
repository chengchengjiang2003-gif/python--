FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --index-url https://pypi.org/simple -r requirements.lock
COPY app ./app
COPY frontend ./frontend
ENV RELAY_DATA_DIR=/app/data
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
