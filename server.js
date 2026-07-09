import http from 'http';

const PORT = process.env.PORT || 7860;

const server = http.createServer((req, res) => {
  if (req.url === '/health' || req.url === '/') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
      services: ['zalo-assistant-bich', 'zalo-assistant-cuong', 'trading-bot']
    }));
  } else if (req.url === '/pm2') {
    import('child_process').then(cp => {
      try {
        const out = cp.execSync('npx pm2 jlist').toString();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(out);
      } catch (err) {
        res.writeHead(500);
        res.end(err.message);
      }
    });
  } else if (req.url === '/logs/cuong') {
    import('fs').then(fs => {
      import('path').then(path => {
        const paths = [
          path.resolve(process.cwd(), 'logs/cuong-out.log'),
          path.resolve(process.env.HOME || '/root', '.pm2/logs/zalo-assistant-cuong-out.log'),
          path.resolve(process.env.HOME || '/root', '.pm2/logs/zalo-assistant-cuong-out-0.log')
        ];
        let found = false;
        for (const p of paths) {
          if (fs.existsSync(p)) {
            res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
            res.end(fs.readFileSync(p, 'utf8'));
            found = true;
            break;
          }
        }
        if (!found) {
          res.writeHead(404);
          res.end('Log not found. Checked: ' + paths.join(', '));
        }
      });
    });
  } else if (req.url === '/logs/cuong-error') {
    import('fs').then(fs => {
      import('path').then(path => {
        const logPath = path.resolve(process.cwd(), 'logs/cuong-error.log');
        if (fs.existsSync(logPath)) {
          res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
          res.end(fs.readFileSync(logPath, 'utf8'));
        } else {
          res.writeHead(404);
          res.end('Log not found at ' + logPath);
        }
      });
    });
  } else if (req.url.startsWith('/logs/')) {
    import('fs').then(fs => {
      const parts = req.url.split('/');
      const botName = parts[2]; // cuong or bich
      const errPath = `/root/.pm2/logs/zalo-assistant-${botName}-error-0.log`;
      const outPath = `/root/.pm2/logs/zalo-assistant-${botName}-out-0.log`;
      const errPath1 = `/root/.pm2/logs/zalo-assistant-${botName}-error-1.log`;
      const outPath1 = `/root/.pm2/logs/zalo-assistant-${botName}-out-1.log`;
      
      let content = `--- ${botName.toUpperCase()} ERROR LOG ---\n`;
      if (fs.existsSync(errPath)) content += fs.readFileSync(errPath, 'utf8').slice(-10000);
      else if (fs.existsSync(errPath1)) content += fs.readFileSync(errPath1, 'utf8').slice(-10000);
      else content += 'Not found\n';
      
      content += `\n--- ${botName.toUpperCase()} OUT LOG ---\n`;
      if (fs.existsSync(outPath)) content += fs.readFileSync(outPath, 'utf8').slice(-10000);
      else if (fs.existsSync(outPath1)) content += fs.readFileSync(outPath1, 'utf8').slice(-10000);
      else content += 'Not found\n';
      
      res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end(content);
    });
  } else if (req.url.startsWith('/download?file=')) {
    import('url').then(url => {
      const query = url.parse(req.url, true).query;
      const fileParam = query.file;
      import('path').then(path => {
        import('fs').then(fs => {
          // Chỉ cho phép tải file mp4 và không cho phép path traversal (..)
          if (!fileParam || !fileParam.endsWith('.mp4') || fileParam.includes('..')) {
            res.writeHead(403);
            res.end('Forbidden: Invalid file path');
            return;
          }
          // process.cwd() trên HF là /app
          const safePath = path.join(process.cwd(), fileParam);
          if (fs.existsSync(safePath)) {
            const stat = fs.statSync(safePath);
            res.writeHead(200, {
              'Content-Type': 'video/mp4',
              'Content-Length': stat.size,
              'Content-Disposition': 'attachment; filename="video-ai.mp4"'
            });
            fs.createReadStream(safePath).pipe(res);
          } else {
            res.writeHead(404);
            res.end('File not found: ' + safePath);
          }
        });
      });
    });
  } else if (req.url === '/logs/secretary') {
    import('fs').then(fs => {
      import('path').then(path => {
        const errPath = '/root/.pm2/logs/telegram-secretary-error-2.log';
        const outPath = '/root/.pm2/logs/telegram-secretary-out-2.log';
        
        let content = '--- ERROR LOG ---\n';
        if (fs.existsSync(errPath)) {
          content += fs.readFileSync(errPath, 'utf8').slice(-10000);
        } else {
          content += 'Not found\n';
        }
        
        content += '\n--- OUT LOG ---\n';
        if (fs.existsSync(outPath)) {
          content += fs.readFileSync(outPath, 'utf8').slice(-10000);
        } else {
          content += 'Not found\n';
        }
        
        res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end(content);
      });
    });
  } else if (req.url === '/test-tg') {
    fetch('https://api.telegram.org/')
      .then(r => r.text())
      .then(t => {
        res.writeHead(200);
        res.end("OK: " + t.substring(0, 50));
      })
      .catch(e => {
        res.writeHead(500);
        res.end("ERR: " + e.message);
      });
  } else if (req.url.startsWith('/config/')) {
    // API để Telegram Secretary (Render) đọc/ghi config.json trên HF
    const botName = req.url.split('/config/')[1].split('?')[0]; // bich hoặc cuong
    if (!['bich', 'cuong'].includes(botName)) {
      res.writeHead(400);
      res.end('Invalid bot name. Use /config/bich or /config/cuong');
      return;
    }
    import('fs').then(fs => {
      import('path').then(path => {
        const configPath = path.resolve(process.cwd(), `${botName}-bot/config.json`);
        
        if (req.method === 'GET') {
          // ĐỌC config
          if (fs.existsSync(configPath)) {
            res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
            res.end(fs.readFileSync(configPath, 'utf8'));
          } else {
            res.writeHead(404);
            res.end(JSON.stringify({ error: `Config not found at ${configPath}` }));
          }
        } else if (req.method === 'POST') {
          // GHI config (từ Telegram Secretary)
          let body = '';
          req.on('data', chunk => body += chunk);
          req.on('end', () => {
            try {
              JSON.parse(body); // Validate JSON
              fs.writeFileSync(configPath, body, 'utf8');
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ success: true, message: `Config ${botName} updated!` }));
            } catch (e) {
              res.writeHead(400);
              res.end(JSON.stringify({ error: 'Invalid JSON: ' + e.message }));
            }
          });
        } else {
          res.writeHead(405);
          res.end('Method not allowed');
        }
      });
    });
  } else if (req.url.startsWith('/proxy/openai/')) {
    // Proxy OpenAI requests via Hugging Face to inject the correct API key
    // This allows Render bots to use HF's secrets without manual configuration
    const targetUrl = 'https://api.groq.com' + req.url.replace('/proxy', '');
    const apiKey = process.env.OPENAI_API_KEY;
    
    if (!apiKey) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: { message: 'OPENAI_API_KEY missing on Hugging Face Server' } }));
      return;
    }

    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      import('https').then(https => {
        const urlObj = new URL(targetUrl);
        const options = {
          hostname: urlObj.hostname,
          path: urlObj.pathname + urlObj.search,
          method: req.method,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
          }
        };

        const proxyReq = https.request(options, (proxyRes) => {
          res.writeHead(proxyRes.statusCode, proxyRes.headers);
          proxyRes.pipe(res, { end: true });
        });

        proxyReq.on('error', (e) => {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: { message: e.message } }));
        });

        if (body) {
          proxyReq.write(body);
        }
        proxyReq.end();
      });
    });
  } else if (req.url.startsWith('/proxy/gemini/')) {
    // Proxy Gemini requests via Hugging Face to inject the correct API key
    const targetUrl = 'https://generativelanguage.googleapis.com' + req.url.replace('/proxy/gemini', '');
    const apiKey = process.env.GEMINI_API_KEY;
    
    if (!apiKey) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: { message: 'GEMINI_API_KEY missing on Hugging Face Server' } }));
      return;
    }

    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      import('https').then(https => {
        const urlObj = new URL(targetUrl);
        urlObj.searchParams.set('key', apiKey); // Thêm key vào query string cho Gemini

        const options = {
          hostname: urlObj.hostname,
          path: urlObj.pathname + urlObj.search,
          method: req.method,
          headers: {
            'Content-Type': 'application/json'
          }
        };

        const proxyReq = https.request(options, (proxyRes) => {
          res.writeHead(proxyRes.statusCode, proxyRes.headers);
          proxyRes.pipe(res, { end: true });
        });

        proxyReq.on('error', (e) => {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: { message: e.message } }));
        });

        if (body) {
          proxyReq.write(body);
        }
        proxyReq.end();
      });
    });
  } else {
    res.writeHead(404);
    res.end('Not found');
  }
});

import https from 'https';

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🌐 Health check server listening on port ${PORT}`);
  
  // Self-ping to prevent Hugging Face Space from sleeping
  const SPACE_URL = 'https://cuongnguyenchi-zalo-bots.hf.space/';
  const RENDER_URL = 'https://trading-telegram-bot-ozhm.onrender.com/health';
  const SECRETARY_URL = 'https://zalo-bots.onrender.com/';
  
  const pingServices = () => {
    // Ping Zalo Bots on HF
    https.get(SPACE_URL, (res) => {
      console.log(`[Self-Ping] Pinged ${SPACE_URL} with status ${res.statusCode} to keep space awake`);
      res.resume();
    }).on('error', (err) => {
      console.error(`[Self-Ping] Error:`, err.message);
    });

    // Ping Trading Bot on Render to keep it awake 24/7
    https.get(RENDER_URL, (res) => {
      console.log(`[Render-Ping] Pinged Trading Bot ${RENDER_URL} with status ${res.statusCode}`);
      res.resume();
    }).on('error', (err) => {
      console.error(`[Render-Ping] Error:`, err.message);
    });

    // Ping Telegram Secretary on Render to keep it awake 24/7
    https.get(SECRETARY_URL, (res) => {
      console.log(`[Secretary-Ping] Pinged Secretary ${SECRETARY_URL} with status ${res.statusCode}`);
      res.resume();
    }).on('error', (err) => {
      console.error(`[Secretary-Ping] Error:`, err.message);
    });
  };

  // Ping ngay khi khởi động
  pingServices();
  // Sau đó lặp lại mỗi 10 phút
  setInterval(pingServices, 10 * 60 * 1000);
});
