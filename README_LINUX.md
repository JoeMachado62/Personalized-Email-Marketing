# AI Sales Agent - Linux Deployment Guide

## Quick Start on Linux VPS

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Run Setup Script
```bash
chmod +x setup_linux.sh
./setup_linux.sh
```

This will:
- Install Python, Node.js, and all dependencies
- Create virtual environment
- Install Playwright browsers
- Setup MCP servers
- Create .env configuration

### 3. Start the Server
```bash
source venv/bin/activate
./start_server.sh
```

Access the application at:
- Frontend: `http://YOUR_SERVER_IP:3000/unified.html`
- API Docs: `http://YOUR_SERVER_IP:8000/docs`

## Production Deployment with PM2

### Install PM2
```bash
npm install -g pm2
```

### Start with PM2
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Enable auto-start on reboot
```

### Monitor
```bash
pm2 monit
pm2 logs
```

## System Architecture

### Enrichment Pipeline
1. **Serper API** - Fast, reliable search (2,500 free searches)
2. **MCP Fetch** - Content extraction (no token costs)
3. **OpenAI GPT** - AI analysis and content generation
4. **No Browser Windows** - Fully headless operation

### Performance
- 5-8 seconds per record
- 5 concurrent enrichments
- ~100 records in 2-3 minutes

## Configuration

### Environment Variables (.env)
```env
# API Keys
SERPER_API_KEY=your_serper_key
LLM_API_KEY=your_openai_key
LLM_MODEL_NAME=gpt-3.5-turbo

# Processing
ENRICHMENT_CONCURRENCY=5
ENABLE_MCP_FETCH=true
USE_PLAYWRIGHT=false  # Not needed with Serper
```

## Nginx Configuration (Optional)

### Install Nginx
```bash
sudo apt install nginx
```

### Configure Reverse Proxy
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Troubleshooting

### Check Logs
```bash
# PM2 logs
pm2 logs

# Application logs
tail -f logs/backend-out.log
tail -f logs/backend-error.log
```

### Restart Services
```bash
pm2 restart all
# or
./stop_server.sh
./start_server.sh
```

### Test API
```bash
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

## Security Notes

1. **Move API Keys to Environment**
   - Don't commit API keys to git
   - Use environment variables or secrets manager

2. **Setup Firewall**
```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable
```

3. **Use HTTPS in Production**
   - Setup SSL with Let's Encrypt
   - Use Nginx as reverse proxy

## Support

For issues or questions, check:
- Application logs in `logs/` directory
- PM2 status: `pm2 status`
- System resources: `htop`

## Benefits of Linux Deployment

✅ **No Windows event loop issues**  
✅ **Playwright works natively**  
✅ **Better performance**  
✅ **Production-ready**  
✅ **Easy scaling**  
✅ **Standard deployment environment**