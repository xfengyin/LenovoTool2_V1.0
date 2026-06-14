const http = require('http');
const fs = require('fs');
const path = require('path');

const contentDir = process.env.CONTENT_DIR;
const stateDir = process.env.STATE_DIR;
const PORT = 52341;

const server = http.createServer((req, res) => {
  if (req.method === 'POST') {
    // Record user choice
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      const eventFile = path.join(stateDir, 'events');
      fs.appendFileSync(eventFile, body + '\n');
      res.writeHead(200, {'Content-Type': 'application/json'});
      res.end('{"ok":true}');
    });
    return;
  }
  
  // Serve latest HTML file from content dir
  const files = fs.readdirSync(contentDir)
    .filter(f => f.endsWith('.html'))
    .sort((a, b) => fs.statSync(path.join(contentDir, b)).mtimeMs - fs.statSync(path.join(contentDir, a)).mtimeMs);
  
  if (files.length === 0) {
    res.writeHead(200, {'Content-Type': 'text/html'});
    res.end('<html><body><h1>Waiting for content...</h1></body></html>');
    return;
  }
  
  const html = fs.readFileSync(path.join(contentDir, files[0]), 'utf-8');
  res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'});
  res.end(html);
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(JSON.stringify({type:'server-started', port:PORT, url:`http://localhost:${PORT}`, contentDir, stateDir}));
});
