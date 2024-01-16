FROM python:3.9-alpine

# Set environment variables for Python
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install ffmpeg as a system dependency
RUN apk --no-cache add ffmpeg

# Set the working directory inside the container to /app
WORKDIR /app

# Copy the local directory's contents into the container at /app
COPY . .

# Install Python dependencies from requirements.txt without caching
RUN pip install -r requirements.txt --no-cache-dir

# Command to run the application when the container starts
CMD ["python", "bot/main.py"]