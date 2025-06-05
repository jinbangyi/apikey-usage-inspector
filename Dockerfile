FROM python:3.12-slim

WORKDIR /app

# Install uv for faster dependency management
RUN pip install uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/
COPY main.py ./

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Command to run the application
CMD ["uv", "run", "python", "main.py"]
