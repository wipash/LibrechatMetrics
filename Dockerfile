FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the updated script
COPY metrics.py ./

# Expose the port for Prometheus to scrape
EXPOSE 8000

# Command to run the script
CMD ["python", "metrics.py"]