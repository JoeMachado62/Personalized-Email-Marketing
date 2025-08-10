# Auto Enrich Application

This repository contains a prototype for a data enrichment of user provided marketing list. The initial MVP will use a specific pipeline targeting used car dealerships. Given a CSV of basic dealership
information (name, address, phone, email), the application attempts
to discover each dealer’s website, infer owner names and contact
details, and generate personalized marketing copy. The generated
content includes a subject line, a multi‑line icebreaker and a
“hot button” topic relevant to the dealer’s business.

## Features

* **Asynchronous scraping** using Playwright to perform web searches
  for dealer websites. The scraper is simplistic and can be extended
  to extract additional contact information from the site itself.
* **AI‑driven content generation** via large language models (LLMs).
  It composes prompts that incorporate known details about each
  dealership and returns short marketing segments.
* **Concurrency control** to limit the number of simultaneous network
  requests, reducing the risk of hitting rate limits or CAPTCHAs.
* **Configurable via environment variables.** API keys and model
  names are read from a `.env` file. An `.env.example` file
  documents the expected variables.

## Getting Started

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   # Install browser binaries for Playwright
   playwright install
   ```

2. **Configure environment:**

   Copy `.env.example` to `.env` and populate the required values,
   especially `LLM_API_KEY` and `LLM_MODEL_NAME`. You can also set
   optional keys for future integrations (Tavily, Perplexity).

3. **Run enrichment:**

   ```bash
   python -m auto_enrich.enricher --input path/to/input.csv --output path/to/output.csv
   ```

   You can adjust concurrency with the `--concurrency` flag to control
   how many enrichment jobs run in parallel.

## Extending the Pipeline

* **Improve Scraping:** The current implementation of
  `extract_contact_info` is a stub. You could add logic to fetch the
  discovered website, parse HTML to find phone numbers, emails or
  owner names using regexes or libraries such as BeautifulSoup.
* **Use Additional Research APIs:** Integrate services like Tavily or
  Perplexity to gather more context about a dealership (e.g. years
  in business, specialization). Use the provided API key variables.
* **Expose as a Web Service:** With FastAPI or Flask you can wrap
  `enrich_dataframe` in an HTTP endpoint to trigger enrichment via a
  REST API. See the commented dependencies in `requirements.txt`.

## License

This project is provided as-is for demonstration purposes. It does not
include a specific open source license; you are free to adapt the
code to your needs.
