FROM python:3.10-slim

# Create non-root user (required by Choreo)
RUN useradd -m -u 10001 botuser

# Install dependencies first (layer cache)
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r /requirements.txt

# Setup app directory
RUN mkdir /app && chown botuser:botuser /app
WORKDIR /app

# Copy source code
COPY --chown=botuser:botuser . /app

# Expose port for Choreo health check
EXPOSE 8000

# Switch to non-root user
USER 10001

CMD ["python3", "bot.py"]
