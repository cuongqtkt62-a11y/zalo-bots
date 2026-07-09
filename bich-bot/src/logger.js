// ============================================================
// logger.js — Winston Logger Configuration
// ============================================================

import winston from 'winston';
import config from './config.js';

// Helper to safely stringify objects with circular references or Error instances
const safeStringify = (obj, indent = 2) => {
  const cache = new Set();
  return JSON.stringify(obj, (key, value) => {
    if (typeof value === 'object' && value !== null) {
      if (cache.has(value)) {
        return '[Circular]';
      }
      cache.add(value);
    }
    if (value instanceof Error) {
      return {
        message: value.message,
        stack: value.stack,
        ...value
      };
    }
    return value;
  }, indent);
};

const logger = winston.createLogger({
  level: config.nodeEnv === 'production' ? 'info' : 'debug',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'zalo-ai-assistant' },
  transports: [
    // Console output (colorized)
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(({ timestamp, level, message, ...meta }) => {
          const metaStr = Object.keys(meta).length > 1
            ? `\n  ${safeStringify(meta, 2)}`
            : '';
          return `${timestamp} [${level}] ${message}${metaStr}`;
        })
      ),
    }),
    // File output for errors
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    }),
    // File output for all logs
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 5242880,
      maxFiles: 10,
    }),
  ],
});

export default logger;
