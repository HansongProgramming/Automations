import aiohttp
import asyncio
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Configuration for batch processing
BATCH_SIZE = 15  # Process 10 URLs at a time
MAX_CONCURRENT_PER_HOST = 5  # Max concurrent connections per host


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


async def fetch_batch(urls: List[str], session: aiohttp.ClientSession, batch_num: int, total_batches: int) -> List[Dict[str, Any]]:
    """
    Fetch a batch of URLs concurrently.
    
    Args:
        urls: List of URLs in this batch
        session: aiohttp ClientSession
        batch_num: Current batch number (for logging)
        total_batches: Total number of batches (for logging)
        
    Returns:
        List of fetch results for this batch
    """
    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(urls)} URLs)...")
    tasks = [fetch_html(url, session) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    logger.info(f"Batch {batch_num}/{total_batches} complete")
    return results


async def fetch_multiple_html(urls: list) -> list:
    """
    Fetch multiple URLs concurrently with batching.
    
    This function processes URLs in batches to ensure all URLs are processed
    even when there are many (e.g., 30+). Each batch is processed sequentially,
    but URLs within each batch are fetched concurrently.
    
    Args:
        urls: List of URLs to fetch
        
    Returns:
        List of dicts with fetch results for all URLs
    """
    if not urls:
        return []
    
    total_urls = len(urls)
    logger.info(f"Starting to fetch {total_urls} URL(s)...")
    
    # Split URLs into batches
    batches = [urls[i:i + BATCH_SIZE] for i in range(0, len(urls), BATCH_SIZE)]
    total_batches = len(batches)
    
    if total_batches > 1:
        logger.info(f"Split into {total_batches} batches of up to {BATCH_SIZE} URLs each")
    
    # Use connection pooling with reasonable limits
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=MAX_CONCURRENT_PER_HOST)
    timeout = aiohttp.ClientTimeout(total=60)
    
    all_results = []
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Process each batch sequentially to avoid overwhelming the system
        for batch_num, batch_urls in enumerate(batches, 1):
            batch_results = await fetch_batch(batch_urls, session, batch_num, total_batches)
            all_results.extend(batch_results)
            
            # Small delay between batches to be polite to servers
            if batch_num < total_batches:
                await asyncio.sleep(0.5)
    
    successful = sum(1 for r in all_results if r['status'] == 'success')
    failed = len(all_results) - successful
    logger.info(f"Fetch complete: {successful} successful, {failed} failed, {len(all_results)} total")
    
    return all_results