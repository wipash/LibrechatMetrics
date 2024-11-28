FROM python:3.9-slim

# Set the working directory
WORKDIR /app

COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Prometheus port specified in the environment variable
ENV PROMETHEUS_PORT=${PROMETHEUS_PORT}
EXPOSE ${PROMETHEUS_PORT}

# Command to run the script
CMD ["python", "metrics.py"]