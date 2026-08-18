FROM python:3.11-slim

# 1. Tizim paketlarini va zaruriy utilitalarni o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    unzip \
    perl \
    nmap \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 2. Nikto skanerini o'rnatish
RUN git clone --depth=1 https://github.com/sullo/nikto.git /opt/nikto \
 && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
 && chmod +x /usr/local/bin/nikto

# 3. Nuclei binarini yuklab olish va o'rnatish
RUN NUCLEI_VERSION=$(curl -s https://api.github.com/repos/projectdiscovery/nuclei/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/') \
 && [ -z "$NUCLEI_VERSION" ] && NUCLEI_VERSION="3.3.0" || true \
 && curl -sL "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" -o /tmp/nuclei.zip \
 && unzip /tmp/nuclei.zip -d /usr/local/bin nuclei \
 && chmod +x /usr/local/bin/nuclei \
 && rm /tmp/nuclei.zip

WORKDIR /app

# 4. Python kutubxonalarini o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 5. Loyiha kodini va skriptlarni ko'chirish
COPY . .

# 6. Skriptlarga bajarish (execute) huquqini berish
RUN chmod +x /app/routers/*.sh 2>/dev/null || true

EXPOSE 8000