# Package marker file for the auto_enrich application

# Make sure gather_web_data is accessible
from .web_scraper import gather_web_data

__all__ = ['gather_web_data']
