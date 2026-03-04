FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install uv && uv sync
EXPOSE 8000
CMD ["uv", "run", "python", "-m", "slides.mcp"]
