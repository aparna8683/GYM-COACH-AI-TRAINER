
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for MediaPipe and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose Render's web service port
EXPOSE 10000

# Start Streamlit
CMD ["sh", "-c", "streamlit run main.py --server.address=0.0.0.0 --server.port=${PORT:-10000}"]
