FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

COPY tests/ ./tests/

CMD ["python", "-m", "lenovo_tool.main"]