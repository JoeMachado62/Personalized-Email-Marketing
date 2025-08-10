# ⚡ Quick Setup Instructions

## ✅ Dependencies Installed Successfully!

All Python packages and Playwright browser have been installed. Here's what's been completed:

### ✅ Installed:
- All Python dependencies (FastAPI, OpenAI SDK, etc.)
- Playwright Chromium browser for web scraping
- All required directories created

## ⚠️ Action Required: Add Your OpenAI API Key

You need to edit the `.env` file and replace the placeholder with your actual OpenAI API key.

### Steps:

1. **Open the .env file** in any text editor:
   ```
   C:\Users\joema\OneDrive\Documents\EZWAI\Personalized Email Marketing\.env
   ```

2. **Find this line:**
   ```
   LLM_API_KEY=your-openai-api-key-here
   ```

3. **Replace it with your actual OpenAI API key:**
   ```
   LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
   ```
   (Your key should start with `sk-proj-` or `sk-`)

4. **Save the file**

## 🚀 After Adding Your API Key:

### 1. Verify Setup:
```bash
python verify_setup.py
```

### 2. Initialize Database:
```bash
python -c "from app.db.connection import init_db; init_db()"
```

### 3. Start the Server:
```bash
uvicorn app.main:app --reload
```
Or simply:
```bash
python run_server.py
```

### 4. Access the Application:
- **Web Interface**: Open `http://localhost:3000` in your browser
- **API Documentation**: Visit `http://localhost:8000/docs`

## 📝 Test the System:

### Option 1: Test with Sample Data
```bash
python scripts/test_integration.py
```

### Option 2: Upload Your CSV
1. Open the web interface at `http://localhost:3000`
2. Drag and drop your CSV file
3. Watch as it enriches your data!

## 🔑 How to Get an OpenAI API Key:

If you don't have an OpenAI API key yet:

1. Go to https://platform.openai.com/signup
2. Create an account or sign in
3. Navigate to API Keys: https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Copy the key (it starts with `sk-`)
6. Add it to your `.env` file

## 💡 Alternative: Use Anthropic Claude

If you prefer to use Anthropic's Claude instead:

1. Get an API key from https://console.anthropic.com/
2. In your `.env` file, set:
   ```
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=your-anthropic-key-here
   LLM_API_KEY=your-anthropic-key-here
   ```

## 🎯 Ready to Go!

Once you've added your API key, the system is fully ready to:
- Process CSV files with contact data
- Discover company websites
- Generate personalized emails
- Handle up to 10,000 records

Your estimated costs:
- ~$0.01-0.02 per contact enriched
- 10,000 records ≈ $100-200 in API costs

## Need Help?

Check these files:
- `START_HERE.md` - Complete getting started guide
- `docs/API_SPECIFICATIONS.md` - API documentation
- `docs/RISK_ASSESSMENT_MITIGATION.md` - Troubleshooting guide