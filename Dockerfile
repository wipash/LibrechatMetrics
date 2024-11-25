FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Create the logs directory
RUN mkdir -p /opt/librechat/metrics/logs

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY metrics.py ./

# Command to run the script
CMD ["python", "metrics.py"]