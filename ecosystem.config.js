module.exports = {
  apps: [
    {
      name: 'ai-sales-backend',
      script: 'python3',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      cwd: './',
      env: {
        SERPER_API_KEY: process.env.SERPER_API_KEY || 'YOUR_SERPER_API_KEY',
        LLM_API_KEY: process.env.LLM_API_KEY || 'YOUR_OPENAI_API_KEY',
        LLM_MODEL_NAME: process.env.LLM_MODEL_NAME || 'gpt-3.5-turbo',
        USE_PLAYWRIGHT: 'false',
        USE_SELENIUM: 'false',
        ENABLE_MCP_FETCH: 'true',
        ENRICHMENT_CONCURRENCY: '5'
      },
      error_file: 'logs/backend-error.log',
      out_file: 'logs/backend-out.log',
      log_file: 'logs/backend-combined.log',
      time: true
    },
    {
      name: 'ai-sales-frontend',
      script: 'python3',
      args: '-m http.server 3000',
      cwd: './frontend',
      error_file: '../logs/frontend-error.log',
      out_file: '../logs/frontend-out.log',
      log_file: '../logs/frontend-combined.log',
      time: true
    }
  ]
};