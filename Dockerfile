FROM node:20-slim

# Install Python and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    fonts-noto-core \
    fontconfig \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

WORKDIR /app

# Copy root deployment package files
COPY package.json ./
RUN npm install

# Copy PM2 config, sync script, health server and entrypoint
COPY ecosystem.config.cjs ./
COPY gist-sync.js ./
COPY server.js ./
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Copy Bích Bot package files and install dependencies
COPY bich-bot/package*.json ./bich-bot/
RUN cd bich-bot && npm install

# Copy Cường Bot package files and install dependencies
COPY cuong-bot/package*.json ./cuong-bot/
RUN cd cuong-bot && npm install

# Copy Trading Bot requirements and install dependencies
COPY trading-bot/requirements.txt ./trading-bot/
RUN pip3 install --no-cache-dir --break-system-packages -r trading-bot/requirements.txt

# Copy the rest of the application files
COPY bich-bot/ ./bich-bot/
COPY cuong-bot/ ./cuong-bot/
COPY trading-bot/ ./trading-bot/
COPY telegram-secretary/ ./telegram-secretary/

# Hugging Face Spaces requires port 7860
ENV PORT=7860
EXPOSE 7860

ENTRYPOINT ["./entrypoint.sh"]
