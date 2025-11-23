FROM python:3.11-slim

WORKDIR /app

COPY generate_containers_block.py .

RUN pip install docker pyyaml requests beautifulsoup4

CMD ["python3", "generate_containers_block.py"]
