"""
Enhanced Windows-compatible Playwright wrapper with better error handling.
Runs Playwright in subprocess to avoid Windows event loop conflicts.
"""

import asyncio
import sys
import json
import subprocess
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
import traceback

logger = logging.getLogger(__name__)


class PlaywrightSubprocessWrapperV2:
    """
    Enhanced subprocess wrapper with better error handling and method coverage.
    """
    
    @staticmethod
    def _create_subprocess_script(method_name: str, **kwargs) -> str:
        """
        Create a generic subprocess script for any method.
        
        Args:
            method_name: Name of the method to call
            **kwargs: Arguments to pass to the method
            
        Returns:
            Python script as string
        """
        # Escape strings properly
        escaped_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                escaped_kwargs[key] = value.replace('"', '\\"')
            elif value is None:
                escaped_kwargs[key] = None
            else:
                escaped_kwargs[key] = json.dumps(value)
        
        # Add the project root to Python path
        project_root = Path(__file__).parent.parent.absolute()
        
        script = f"""
import sys
import os
import json
import asyncio
import traceback
from datetime import datetime

# Add project root to path
sys.path.insert(0, r'{project_root}')
os.chdir(r'{project_root}')

# Set Windows event loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Custom JSON encoder for non-serializable objects
class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        if hasattr(obj, '__dict__'):
            return str(obj)
        return super().default(obj)

async def run_method():
    try:
        from auto_enrich.web_scraper_playwright import PlaywrightWebGatherer
        
        async with PlaywrightWebGatherer() as gatherer:
            method = getattr(gatherer, '{method_name}')
            kwargs = {json.dumps(escaped_kwargs)}
            
            # Fix None values and escaped strings
            for key, value in kwargs.items():
                if value is None:
                    continue
                if isinstance(value, str) and value != 'null':
                    kwargs[key] = value.replace('\\\\"', '"')
                elif value == 'null':
                    kwargs[key] = None
            
            result = await method(**kwargs)
            return result
    except Exception as e:
        return {{
            'error': str(e),
            'traceback': traceback.format_exc(),
            'method': '{method_name}'
        }}

try:
    result = asyncio.run(run_method())
    print(json.dumps(result, cls=EnhancedJSONEncoder))
except Exception as e:
    error_result = {{
        'error': str(e),
        'traceback': traceback.format_exc(),
        'method': '{method_name}'
    }}
    print(json.dumps(error_result))
"""
        return script
    
    @staticmethod
    async def _run_subprocess(script: str, timeout: int = 120) -> Dict[str, Any]:
        """
        Run a Python script in a subprocess and return the result.
        
        Args:
            script: Python script to run
            timeout: Timeout in seconds
            
        Returns:
            Result dictionary or error information
        """
        try:
            # Write script to temp file for better debugging
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script)
                script_path = f.name
            
            try:
                result = await asyncio.create_subprocess_exec(
                    sys.executable, script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=Path(__file__).parent.parent
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        result.communicate(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    result.kill()
                    await result.wait()
                    logger.error(f"Subprocess timed out after {timeout} seconds")
                    return {
                        'error': f'Subprocess timed out after {timeout} seconds',
                        'timeout': True
                    }
                
                if result.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    logger.error(f"Subprocess failed: {error_msg}")
                    return {
                        'error': 'Subprocess failed',
                        'stderr': error_msg,
                        'returncode': result.returncode
                    }
                
                # Parse JSON output
                output = stdout.decode('utf-8', errors='ignore').strip()
                if not output:
                    return {'error': 'No output from subprocess'}
                
                return json.loads(output)
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(script_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Subprocess execution error: {e}")
            return {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    async def search_web(self, query: str, max_results: int = 10) -> List[Dict]:
        """Run web search in subprocess."""
        script = self._create_subprocess_script(
            'search',
            query=query,
            max_results=max_results
        )
        result = await self._run_subprocess(script, timeout=60)
        
        if 'error' in result:
            logger.error(f"Search failed: {result.get('error')}")
            return []
        
        return result.get('results', [])
    
    async def scrape_website(self, url: str) -> Dict[str, Any]:
        """Scrape a website in subprocess."""
        script = self._create_subprocess_script(
            '_scrape_website',
            url=url
        )
        result = await self._run_subprocess(script, timeout=90)
        
        if 'error' in result:
            logger.error(f"Scrape failed for {url}: {result.get('error')}")
            return {'error': result.get('error'), 'url': url}
        
        return result
    
    async def gather_web_data(self, company_name: str, location: str = "",
                             additional_data: Optional[Dict] = None,
                             campaign_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Full web data gathering in subprocess."""
        script = self._create_subprocess_script(
            'search_and_gather',
            company_name=company_name,
            location=location,
            additional_data=additional_data or {},
            campaign_context=campaign_context or {}
        )
        
        result = await self._run_subprocess(script, timeout=180)  # 3 minutes
        
        if 'error' in result:
            logger.error(f"Gather failed for {company_name}: {result.get('error')}")
            if 'traceback' in result:
                logger.debug(f"Traceback: {result['traceback']}")
            
            # Return empty structure on error
            return {
                'search_results': [],
                'website_found': False,
                'website_url': None,
                'website_data': {},
                'confidence_score': 0.0,
                'error': result.get('error')
            }
        
        return result


# Enhanced compatibility class for web_scraper.py
class WindowsPlaywrightGatherer:
    """
    Windows-compatible gatherer that uses subprocess wrapper.
    Implements all required methods.
    """
    
    def __init__(self):
        self.wrapper = PlaywrightSubprocessWrapperV2()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    async def search_and_gather(self, company_name: str, location: str = "",
                               additional_data: Optional[Dict] = None,
                               campaign_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Main search and gather method."""
        return await self.wrapper.gather_web_data(
            company_name=company_name,
            location=location,
            additional_data=additional_data,
            campaign_context=campaign_context
        )
    
    async def search(self, query: str, **kwargs) -> List[Dict]:
        """Search method."""
        return await self.wrapper.search_web(query, kwargs.get('max_results', 10))
    
    async def _scrape_website(self, url: str) -> Dict[str, Any]:
        """Private scrape method (called by some modules)."""
        return await self.wrapper.scrape_website(url)
    
    async def scrape_website(self, url: str) -> Dict[str, Any]:
        """Public scrape method."""
        return await self.wrapper.scrape_website(url)


# Compatibility function
async def gather_web_data_subprocess(company_name: str, location: str = "",
                                    additional_data: Optional[Dict] = None,
                                    campaign_context: Optional[Dict] = None,
                                    **kwargs) -> Dict[str, Any]:
    """
    Wrapper function that uses subprocess for Windows compatibility.
    """
    wrapper = PlaywrightSubprocessWrapperV2()
    return await wrapper.gather_web_data(
        company_name=company_name,
        location=location,
        additional_data=additional_data,
        campaign_context=campaign_context
    )