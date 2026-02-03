import aiohttp
import asyncio
from typing import Dict, Any


async def fetch_html(url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Fetch HTML content from a URL asynchronously.
    
    Args:
        url: The URL to fetch
        session: aiohttp ClientSession for connection pooling
        
    Returns:
        Dict with url, status, and either html_content or error
    """
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                html_content = await response.text()
                return {
                    'url': url,
                    'status': 'success',
                    'html_content': html_content
                }
            else:
                return {
                    'url': url,
                    'status': 'error',
                    'error': f'HTTP {response.status}'
                }
    except asyncio.TimeoutError:
        return {
            'url': url,
            'status': 'error',
            'error': 'Request timeout (30s)'
        }
    except Exception as e:
        return {
            'url': url,
            'status': 'error',
            'error': str(e)
        }


async def fetch_multiple_html(urls: list) -> list:
    """
    Fetch multiple URLs concurrently.
    
    Args:
        urls: List of URLs to fetch
        
    Returns:
        List of dicts with fetch results
    """
    # Use connection pooling with reasonable limits
    connector = aiohttp.TCPConnector(limit=30, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [fetch_html(url, session) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results