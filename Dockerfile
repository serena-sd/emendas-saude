FROM selenium/standalone-chrome:latest

USER root
WORKDIR /app

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Os arquivos requirements.txt e main.py estão na mesma pasta que este Dockerfile
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 10000
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
