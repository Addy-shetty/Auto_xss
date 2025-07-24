# Use Ubuntu as base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV GO_VERSION=1.21.3
ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    python3 \
    python3-pip \
    jq \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install Go
RUN wget https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz \
    && rm go${GO_VERSION}.linux-amd64.tar.gz

# Install security tools
RUN go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install github.com/hakluke/hakrawler@latest && \
    go install github.com/tomnomnom/waybackurls@latest && \
    go install github.com/projectdiscovery/katana/cmd/katana@latest && \
    go install github.com/tomnomnom/gf@latest && \
    go install github.com/KathanP19/Gxss@latest && \
    go install github.com/hahwul/dalfox/v2@latest && \
    go install github.com/ameenmaali/urldedupe@latest

# Install gf patterns
RUN git clone https://github.com/1ndianl33t/Gf-Patterns /root/.gf

# Create application directory
WORKDIR /app

# Copy application files
COPY auto_xss.sh /app/
COPY Install_tools.sh /app/
COPY src/ /app/src/
COPY config/ /app/config/

# Make scripts executable
RUN chmod +x /app/auto_xss.sh /app/Install_tools.sh

# Create results directory
RUN mkdir -p /app/results

# Install Python dependencies for API server
COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

# Expose port for API server
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set default command
CMD ["python3", "src/api/main.py"]