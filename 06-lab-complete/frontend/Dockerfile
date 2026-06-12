FROM python:3.12-slim

WORKDIR /app

COPY 06-lab-complete/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 06-lab-complete/frontend .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
