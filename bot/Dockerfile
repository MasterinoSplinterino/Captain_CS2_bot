FROM python:3.11-slim

WORKDIR /app

# Install network tools for connectivity checks
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
