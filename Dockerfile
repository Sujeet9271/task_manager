# Use Python base image (specific version if needed, e.g., python:3.12-slim)
FROM python:3.12-slim

# Set environment variables to optimize Python behavior
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install necessary build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies listed in the requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application files into the container
COPY . /app/

# Set the working directory
WORKDIR /app

# Copy the entrypoint script and make it executable
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose the port for the Django app
EXPOSE 8000

# Set the entrypoint to the custom script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command for the application
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "task_manager.asgi:application"]
