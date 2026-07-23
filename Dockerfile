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

# Copy Python requirements and install
COPY trading-bot/requirements.txt ./trading-bot/
RUN pip3 install --no-cache-dir --break-system-packages -r trading-bot/requirements.txt

# Copy everything
COPY . .

# Install dependencies for bots
RUN cd bich-bot && npm install
RUN cd cuong-bot && npm install
RUN cd tradingview-xau-alert && npm install

# Build CEO Voice Assistant
RUN cd ceo-voice-assistant && npm install && npm run build

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Port configuration
ENV PORT=7860
EXPOSE 7860

ENTRYPOINT ["./entrypoint.sh"]
