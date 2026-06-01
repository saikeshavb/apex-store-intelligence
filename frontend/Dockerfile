# Lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Install system graphics libraries required by OpenCV and YOLO
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# UPGRADE PIP, then install requirements with a massive timeout
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy the dashboard code
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Command to run the dashboard
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]