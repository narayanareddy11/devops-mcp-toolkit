FROM python:3.11-slim

LABEL maintainer="Narayana Reddy"
LABEL description="DevOps MCP Toolkit — 15 MCP servers + Streamlit dashboard"
LABEL version="2.1.0"

WORKDIR /app

# Install system deps (kubectl, helm, terraform, trivy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg unzip git && \
    rm -rf /var/lib/apt/lists/*

# kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && mv kubectl /usr/local/bin/

# helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY servers/     ./servers/
COPY streamlit_app/ ./streamlit_app/
COPY terraform/   ./terraform/
COPY k8s/         ./k8s/

# Expose Streamlit port
EXPOSE 8501

ENV PYTHONUNBUFFERED=1

CMD ["python3", "-m", "streamlit", "run", "streamlit_app/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
