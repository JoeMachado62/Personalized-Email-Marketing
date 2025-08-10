"""
Configuration loader for the enrichment application.

This module loads environment variables that are used by the
scraping and AI enrichment components. API keys should be
stored in a `.env` file at the project root. You can create
this file from the provided `.env.example` template and supply
your own keys. See the README for details.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# Attempt to load a `.env` file located in the project root. If the file
# doesn't exist, `load_dotenv` does nothing. This allows the application
# to operate with environment variables set externally as well.
dotenv_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path)

# API keys and other secrets are optional. They will evaluate to `None`
# when not provided. You can override these values by setting
# environment variables in your deployment environment or editing
# the `.env` file.
LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")
TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")
PERPLEXITY_API_KEY: str | None = os.getenv("PERPLEXITY_API_KEY")

# Name of the model to use when communicating with the language model
# provider. Adjust this value to match the API you're using. The default
# `gpt-4o` is a placeholder and may need to be updated when running
# against other providers.
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o")

# Timeout (in seconds) for outbound API calls. Increasing this value
# can help avoid timeouts on slower connections or with larger models.
API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))
