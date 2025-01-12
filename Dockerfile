# Use an official Python image as the base image
FROM python:3.9-slim

# Set environment variables to avoid Python writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt to the working directory
COPY requirements.txt /app/

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the entire project folder to the working directory
COPY . /app/

# Expose the port the Flask app runs on (5000 by default)
EXPOSE 5000

# Command to run the Flask app
CMD ["python", "app.py"]
