# Use a lightweight Python image optimized for ARM64 (MacBook Air compatible)
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy dependency list and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files (app.py, ingestion_db.py, pos_data.csv)
COPY . .

# Expose the API port
EXPOSE 5000

# Zero-manual-step execution: Set up the DB indices, then start the server
# (Using 0.0.0.0 ensures the Flask app is accessible outside the container)
CMD python ingestion_db.py && flask --app app run --host=0.0.0.0 --port=5000