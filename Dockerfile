FROM python:3.10-slim

# Install required Python packages for benign code skills
RUN pip install requests

# Create a non‑root user
RUN useradd -m -s /bin/bash sandbox

# Set working directory
WORKDIR /app

# Disable network by default (can be overridden)
# We'll enforce network_mode="none" at runtime

ENTRYPOINT ["python", "-c"]