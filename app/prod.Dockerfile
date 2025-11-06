FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 8000

# Ejecutamos con fastapi run
CMD ["fastapi", "run", "main.py", "--port", "8000"]
