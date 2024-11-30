# Dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for Flask API
EXPOSE 5000

# Start the Flask app
CMD ["python", "api.py"]
