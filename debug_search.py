"""
Debug search to see what's actually being returned
"""
import httpx
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import json

def test_google_search():
    """Test Google search and see what HTML we get"""
    
    query = "Bob's Used Cars Miami FL"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'DNT': '1',
    }
    
    params = {
        'q': query,
        'hl': 'en',
        'gl': 'us',
        'num': 10
    }
    
    print(f"Searching Google for: {query}")
    response = httpx.get(
        'https://www.google.com/search',
        params=params,
        headers=headers,
        follow_redirects=True
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response length: {len(response.text)} characters")
    
    # Save HTML for inspection
    with open('google_response.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("Saved response to google_response.html")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try different selectors
    selectors = [
        ('div.g', 'Standard result div'),
        ('div[data-sokoban-container]', 'Sokoban container'),
        ('div.hlcw0c', 'Alternative result div'),
        ('div#search', 'Search container'),
        ('div#rso', 'Results container'),
        ('a[href]', 'All links'),
        ('h3', 'All H3 headers')
    ]
    
    for selector, description in selectors:
        elements = soup.select(selector)
        print(f"\n{description} ({selector}): {len(elements)} found")
        if elements and len(elements) < 5:
            for elem in elements[:3]:
                print(f"  - {elem.get_text()[:100]}...")
    
    # Check if we're hitting a CAPTCHA
    if 'captcha' in response.text.lower() or 'unusual traffic' in response.text.lower():
        print("\n⚠️ CAPTCHA or rate limit detected!")
    
    # Check for "No results found"
    if 'did not match any documents' in response.text:
        print("\n⚠️ No results found message detected")
    
    return response.text

def test_duckduckgo_search():
    """Test DuckDuckGo search"""
    
    query = "Bob's Used Cars Miami FL"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    params = {
        'q': query,
        't': 'h_',
        'ia': 'web'
    }
    
    print(f"\nSearching DuckDuckGo for: {query}")
    response = httpx.get(
        'https://html.duckduckgo.com/html/',
        params=params,
        headers=headers,
        follow_redirects=True
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response length: {len(response.text)} characters")
    
    # Save HTML
    with open('duckduckgo_response.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("Saved response to duckduckgo_response.html")
    
    # Parse
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # DuckDuckGo specific selectors
    selectors = [
        ('a.result__a', 'Result links'),
        ('div.result', 'Result divs'),
        ('div.results', 'Results container'),
        ('h2', 'All H2 headers'),
        ('a[href]', 'All links')
    ]
    
    for selector, description in selectors:
        elements = soup.select(selector)
        print(f"\n{description} ({selector}): {len(elements)} found")
        if elements and len(elements) > 0:
            for elem in elements[:3]:
                text = elem.get_text()[:100] if elem.get_text() else "No text"
                href = elem.get('href', 'No href') if hasattr(elem, 'get') else 'N/A'
                print(f"  - Text: {text}...")
                if href != 'N/A' and href != 'No href':
                    print(f"    URL: {href[:100]}")

if __name__ == "__main__":
    print("=" * 80)
    print("DEBUGGING SEARCH ENGINES")
    print("=" * 80)
    
    try:
        google_html = test_google_search()
    except Exception as e:
        print(f"Google search error: {e}")
    
    try:
        test_duckduckgo_search()
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
    
    print("\n" + "=" * 80)
    print("Check google_response.html and duckduckgo_response.html for full HTML")
    print("=" * 80)