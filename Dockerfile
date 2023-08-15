# Use the latest Python version with Alpine
FROM python:alpine

# Set the working directory inside the container
WORKDIR /app

# Copy the local package directories to the container
COPY . /app

# Install system dependencies for Chromium
RUN apk add --no-cache \
    chromium \
    chromium-chromedriver

# Install the required Python packages
RUN pip install --trusted-host pypi.python.org Flask requests BeautifulSoup4 validators python-dotenv selenium

# Make port 80 available to the world outside this container
EXPOSE 80

# Set environment variables for production
ENV FLASK_ENV=production

# Optionally, set Chrome binary path for Selenium
ENV CHROME_BIN=/usr/bin/chromium-browser

# Run app.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
