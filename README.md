# AI Sales Agent - Personalized Email Marketing Platform

This repository contains a comprehensive AI-powered data enrichment platform for personalized email marketing. The system transforms CSV business data into comprehensive profiles with personalized marketing content. The current implementation targets used car dealerships but can be adapted for any industry.

Given a CSV of basic business information (name, address, phone), the application:
- Discovers business websites using intelligent search
- Extracts owner contact information and business details
- Generates personalized email content with subject lines and icebreakers
- Identifies "hot button" topics relevant to each business

## Current Architecture

The system uses a modern, reliable architecture:

* **Selenium-based web scraping** using real Chrome browsers to perform web searches and avoid bot detection
* **MCP Fetch integration** for efficient HTML-to-Markdown conversion with no API costs
* **FastAPI web application** with intuitive web interface for CSV uploads and job monitoring
* **Intelligent column mapping** with auto-detection and manual override capabilities
* **AI-driven content generation** via OpenAI GPT models with campaign context awareness
* **Real-time job monitoring** with progress tracking and status updates
* **Concurrent processing** with configurable limits to balance speed and reliability

## Getting Started

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   # Install Selenium WebDriver (automatically managed)
   # MCP Fetch server is installed automatically
   ```

2. **Configure environment:**

   Copy `.env.example` to `.env` and populate the required values:
   ```env
   LLM_API_KEY=your-openai-api-key
   LLM_MODEL=gpt-4o-mini
   ENABLE_MCP_FETCH=true
   SEARCH_PROVIDER=selenium
   ```

3. **Start the application:**

   ```bash
   python run_server.py
   ```

   This starts both the FastAPI backend (port 8000) and opens the web interface.

4. **Access the web interface:**

   - **Main interface:** http://localhost:8000/static/unified.html
   - **API documentation:** http://localhost:8000/docs
   - **Simple upload:** http://localhost:8000/static/test.html

5. **Alternative command-line usage:**

   ```bash
   python -m auto_enrich.enricher --input path/to/input.csv --output path/to/output.csv
   ```

## System Components

### Core Modules

- **`auto_enrich/web_scraper.py`** - Selenium-based web scraping with MCP Fetch integration
- **`auto_enrich/search_with_selenium.py`** - Real Chrome browser search implementation
- **`auto_enrich/mcp_client.py`** - MCP Fetch client for HTML-to-Markdown conversion
- **`app/main.py`** - FastAPI web application with REST API
- **`frontend/`** - Web interface files (HTML, CSS, JavaScript)

### Web Interface Features

- **Unified Workflow:** Single-page upload with integrated column mapping
- **Progress Monitoring:** Real-time job status and progress tracking  
- **Column Mapping:** Auto-detection with manual override capabilities
- **Campaign Context:** Configurable personalization parameters
- **Download Results:** Enriched CSV with personalized content

### API Endpoints

- `POST /api/v1/jobs/upload` - Upload CSV and start enrichment
- `GET /api/v1/jobs/{id}` - Check job status and progress
- `POST /api/v1/mapping/analyze` - Analyze CSV columns for mapping
- `GET /api/v1/health` - System health check

### Extending the Platform

* **Custom Industries:** Modify prompts and search terms for different business types
* **Additional Data Sources:** Integrate social media, review sites, or business directories
* **Advanced Personalization:** Add A/B testing, sentiment analysis, or demographic targeting
* **CRM Integration:** Connect to Salesforce, HubSpot, or other marketing platforms
* **Multi-channel Content:** Generate SMS, social media, or direct mail content

## License

This project is provided as-is for demonstration purposes. It does not
include a specific open source license; you are free to adapt the
code to your needs.
