import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlencode
from datetime import datetime, date
import re
import sys
import os
import random

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Handle ChromeDriverManager import with proper error handling
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
    ChromeDriverManager = None
    print("webdriver-manager not available, will try direct Chrome driver")


# More sophisticated headers to avoid bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
    "Pragma": "no-cache",
    "TE": "Trailers"
}


def build_indeed_url(query: str = "stage OR stagiaire OR internship", start: int = 0, country: str = "Maroc") -> str:
    """
    Build Indeed URL for a specific country.
    country: Country name in French (e.g., 'Maroc', 'France', 'Canada')
    """
    # Map country names to Indeed domains
    country_domains = {
        'Maroc': 'ma',
        'France': 'fr',
        'Canada': 'ca',
        'Belgique': 'be',
        'Suisse': 'ch'
    }
    
    # Default to Morocco if country not found
    domain_suffix = country_domains.get(country, 'ma')
    base = f"https://{domain_suffix}.indeed.com/jobs"
    
    # Set location parameter based on country
    location_param = country
    
    params = {"q": query, "start": start, "l": location_param}
    return f"{base}?{urlencode(params)}"


def parse_date_posted(date_text: str) -> Optional[date]:
    """Parse date text to actual date object"""
    if not date_text:
        return None
    
    today = date.today()
    
    # Patterns communs pour les dates Indeed
    patterns = [
        r'il y a (\d+) jour',  # "il y a 2 jours"
        r'il y a (\d+) heure',  # "il y a 3 heures"
        r'il y a (\d+) semaine',  # "il y a 1 semaine"
        r'il y a (\d+) mois',  # "il y a 2 mois"
        r'(\d+)/(\d+)/(\d+)',  # "15/10/2024"
        r'(\d{4})-(\d{2})-(\d{2})',  # "2024-10-15"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_text.lower())
        if match:
            try:
                if 'jour' in pattern:
                    days_ago = int(match.group(1))
                    from datetime import timedelta
                    return today - timedelta(days=days_ago)
                elif 'heure' in pattern:
                    hours_ago = int(match.group(1))
                    from datetime import timedelta
                    return today - timedelta(hours=hours_ago)
                elif 'semaine' in pattern:
                    weeks_ago = int(match.group(1))
                    from datetime import timedelta
                    return today - timedelta(weeks=weeks_ago)
                elif 'mois' in pattern:
                    months_ago = int(match.group(1))
                    from datetime import timedelta
                    return today - timedelta(days=months_ago * 30)
                elif len(match.groups()) == 3:
                    if '/' in pattern:
                        day, month, year = match.groups()
                        return date(int(year), int(month), int(day))
                    else:
                        year, month, day = match.groups()
                        return date(int(year), int(month), int(day))
            except (ValueError, OverflowError):
                # If date parsing fails, continue to next pattern
                continue
    
    return None


def extract_country_from_location(location: str) -> Optional[str]:
    """Extract country from location string"""
    if not location:
        return None
    
    # Mapping des villes aux pays
    city_to_country = {
        'paris': 'France', 'lyon': 'France', 'marseille': 'France', 'toulouse': 'France',
        'nice': 'France', 'nantes': 'France', 'strasbourg': 'France', 'montpellier': 'France',
        'bordeaux': 'France', 'lille': 'France', 'rennes': 'France', 'reims': 'France',
        'casablanca': 'Maroc', 'rabat': 'Maroc', 'fès': 'Maroc', 'fes': 'Maroc',
        'marrakech': 'Maroc', 'agadir': 'Maroc', 'tanger': 'Maroc', 'meknès': 'Maroc',
        'oujda': 'Maroc', 'kenitra': 'Maroc', 'tétouan': 'Maroc', 'salé': 'Maroc',
        'bruxelles': 'Belgique', 'anvers': 'Belgique', 'gand': 'Belgique', 'charleroi': 'Belgique',
        'genève': 'Suisse', 'zurich': 'Suisse', 'bâle': 'Suisse', 'berne': 'Suisse',
        'montréal': 'Canada', 'toronto': 'Canada', 'vancouver': 'Canada', 'ottawa': 'Canada',
    }
    
    location_lower = location.lower()
    
    # Chercher des patterns de pays
    if any(country in location_lower for country in ['france', 'français', 'french']):
        return 'France'
    elif any(country in location_lower for country in ['maroc', 'morocco', 'marocain']):
        return 'Maroc'
    elif any(country in location_lower for country in ['belgique', 'belgium', 'belge']):
        return 'Belgique'
    elif any(country in location_lower for country in ['suisse', 'switzerland', 'suisse']):
        return 'Suisse'
    elif any(country in location_lower for country in ['canada', 'canadian']):
        return 'Canada'
    
    # Chercher par ville
    for city, country in city_to_country.items():
        if city in location_lower:
            return country
    
    return None


def parse_job_card(card) -> Dict[str, str]:
    # Title and link - based on the HTML you provided
    link_tag = (
        card.select_one("h2 a") 
        or card.select_one("a.jcs-JobTitle") 
        or card.select_one("a[aria-label]")
        or card.select_one("a[data-jk]")
    )
    title = None
    link = None
    if link_tag:
        title = (link_tag.get_text(strip=True) or None)
        href = link_tag.get("href")
        if href:
            link = urljoin("https://ma.indeed.com", href)

    # Company - based on the HTML structure you showed
    company = None
    company_tag = (
        card.select_one("span[data-testid='company-name']")
        or card.select_one("span.companyName")
        or card.select_one(".companyName")
    )
    if company_tag:
        company = company_tag.get_text(strip=True) or None

    # Location - based on the HTML structure you showed
    location = None
    location_tag = (
        card.select_one("div[data-testid='text-location']")
        or card.select_one("div.companyLocation")
        or card.select_one(".companyLocation")
    )
    if location_tag:
        location = location_tag.get_text(strip=True) or None

    # Date posted - try to find any date information with more robust selectors
    date_posted = None
    
    # Try multiple strategies to find date information
    # Strategy 1: Look for specific date containers
    date_containers = card.select("div.jobCardReqMore, span.jobCardReqMore, div.jobCardShelfContainer, span.jobCardShelfContainer")
    for container in date_containers:
        text = container.get_text(strip=True)
        if text and any(keyword in text.lower() for keyword in ["il y a", "jour", "heure", "semaine", "mois", "posted", "hier", "ago"]):
            date_posted = text
            break
    
    # Strategy 2: Look for metadata containers
    if not date_posted:
        metadata_containers = card.select("ul.metadataContainer, div.metadataContainer")
        for container in metadata_containers:
            # Look for list items or spans with date information
            date_elements = container.find_all(['li', 'span'])
            for elem in date_elements:
                text = elem.get_text(strip=True)
                if text and any(keyword in text.lower() for keyword in ["il y a", "jour", "heure", "semaine", "mois", "posted", "hier", "ago"]):
                    date_posted = text
                    break
            if date_posted:
                break
    
    # Strategy 3: Look through all text elements in the card for date patterns
    if not date_posted:
        all_text_elements = card.find_all(text=True)
        for text in all_text_elements:
            stripped_text = text.strip()
            if stripped_text and any(keyword in stripped_text.lower() for keyword in ["il y a", "jour", "heure", "semaine", "mois", "posted", "hier", "ago"]):
                date_posted = stripped_text
                break
    
    # Strategy 4: Try specific selectors as fallback
    if not date_posted:
        date_tag = (
            card.select_one("span[data-testid='myJobsStateDate']")
            or card.select_one("span.date")
            or card.select_one("span.postedAt")
            or card.select_one("div.resultFooter .date")
            or card.select_one(".jobCardShelfContainer .date")
            or card.select_one("span[title*='Posted']")
            or card.select_one("[data-testid*='date']")
            or card.select_one(".jobsearch-SerpJobCard .date")
        )
        if date_tag:
            date_posted = date_tag.get_text(strip=True) or None

    return {
        "title": title or "",
        "company": company or "",
        "location": location or "",
        "date_posted": date_posted or "",
        "link": link or "",
    }


def setup_driver():
    """Setup Chrome driver with anti-detection options"""
    # Don't try to set up Chrome driver in cloud environments
    if os.environ.get('RENDER'):
        print("Skipping Chrome driver setup in cloud environment")
        return None
        
    try:
        options = Options()
        options.add_argument("--headless")  # Run in background
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Try to handle architecture issues
        driver = None
        
        # Try with ChromeDriverManager first if available
        if WEBDRIVER_MANAGER_AVAILABLE and ChromeDriverManager is not None:
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                print("Chrome driver set up with ChromeDriverManager")
            except Exception as arch_error:
                print(f"ChromeDriverManager failed: {arch_error}")
                # Try without ChromeDriverManager
                try:
                    driver = webdriver.Chrome(options=options)
                    print("Chrome driver set up directly")
                except Exception as direct_error:
                    print(f"Direct Chrome driver setup failed: {direct_error}")
                    driver = None
        else:
            # Try without ChromeDriverManager
            try:
                driver = webdriver.Chrome(options=options)
                print("Chrome driver set up directly (webdriver-manager not available)")
            except Exception as direct_error:
                print(f"Direct Chrome driver setup failed: {direct_error}")
                driver = None
        
        if driver:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        return None


def scrape_indeed_selenium(max_pages: int = 50, delay_seconds: float = 1.5, country: str = "Maroc") -> List[Dict[str, str]]:
    """
    Scrape Indeed job listings using Selenium to bypass anti-bot protection.
    Returns list of dicts with keys: title, company, location, date_posted, link
    """
    offers: List[Dict[str, str]] = []
    driver = None
    
    try:
        driver = setup_driver()
        if driver is None:
            print("Failed to setup Chrome driver, falling back to requests method")
            return []
            
        wait = WebDriverWait(driver, 10)
        
        for page in range(max_pages):
            start = page * 10
            url = build_indeed_url(start=start, country=country)
            print(f"Scraping page {page + 1}/{max_pages}: {url}")
            
            driver.get(url)
            time.sleep(delay_seconds)
            
            # Wait for job cards to load
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-jk], .job_seen_beacon, .resultContent")))
            except:
                print(f"No job cards found on page {page + 1}")
                # Try to continue to next page instead of breaking
                continue
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Try multiple selectors for job cards
            cards = soup.select("div.job_seen_beacon")
            if not cards:
                cards = soup.select(".resultContent")
            if not cards:
                cards = soup.select(".jobsearch-SerpJobCard")
            if not cards:
                cards = soup.select("[data-jk]")
            if not cards:
                cards = soup.select("div[data-testid='job-card']")
                
            print(f"Found {len(cards)} job cards on page {page + 1}")

            page_offers = 0
            for card in cards:
                data = parse_job_card(card)
                if data.get("link") and data.get("title"):
                    offers.append(data)
                    page_offers += 1
                    print(f"Added: {data['title'][:50]}...")

            print(f"Page {page + 1}: {page_offers} offers added")
            
            # If no offers found on this page, try a few more pages before stopping
            if page_offers == 0 and page > 5:
                print(f"No offers found on page {page + 1}, trying 3 more pages...")
                empty_pages = 0
                for extra_page in range(page + 1, min(page + 4, max_pages)):
                    start = extra_page * 10
                    url = build_indeed_url(start=start, country=country)
                    driver.get(url)
                    time.sleep(delay_seconds)
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    cards = soup.select("div.job_seen_beacon") or soup.select(".resultContent")
                    if not cards:
                        empty_pages += 1
                        if empty_pages >= 2:
                            print("Too many empty pages, stopping...")
                            break
                break

            time.sleep(delay_seconds)
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                print(f"Error closing driver: {e}")

    print(f"Total offers scraped: {len(offers)}")
    return offers


def scrape_indeed(max_pages: int = 1, delay_seconds: float = 5.0, country: str = "Maroc") -> List[Dict[str, str]]:
    """
    Main scraping function - enhanced for cloud environments with multiple bypass strategies
    """
    print(f"Trying requests scraping for {country}...")
    
    # Try multiple strategies
    strategies = [
        ("scraperapi", lambda: scrape_with_scraperapi(max_pages, delay_seconds, country)),
        ("direct_requests", lambda: scrape_with_direct_requests(max_pages, delay_seconds, country)),
    ]
    
    # Only try Selenium if not in cloud environment
    if not os.environ.get('RENDER'):
        strategies.append(("selenium", lambda: scrape_indeed_selenium(max_pages, delay_seconds, country)))
    
    for strategy_name, strategy_func in strategies:
        try:
            print(f"Trying strategy: {strategy_name}")
            offers = strategy_func()
            if offers and len(offers) > 0:
                print(f"Success with {strategy_name}: {len(offers)} offers found")
                return offers
            else:
                print(f"Strategy {strategy_name} returned no offers")
        except Exception as e:
            print(f"Strategy {strategy_name} failed: {e}")
            continue
    
    # If all strategies failed, provide guidance
    print("\n" + "="*50)
    print("ALL SCRAPING STRATEGIES FAILED")
    print("RECOMMENDATIONS:")
    print("1. Get a ScraperAPI key and set SCRAPER_API_KEY environment variable")
    print("2. Try using proxy services")
    print("3. Reduce scraping frequency")
    print("4. Check if Indeed has changed their HTML structure")
    print("="*50)
    
    return []


# Free proxy list - in a real application, you'd use a paid proxy service
FREE_PROXIES = [
    # These are example proxies - you would replace with real ones
    # Format: "ip:port" or "username:password@ip:port"
]

def get_proxy_list():
    """Get proxy list from environment variable or use free proxies"""
    proxy_list = os.environ.get('SCRAPER_PROXIES', '')
    if proxy_list:
        return [p.strip() for p in proxy_list.split(',') if p.strip()]
    return FREE_PROXIES

def scrape_indeed_requests(max_pages: int = 1, delay_seconds: float = 5.0, country: str = "Maroc") -> List[Dict[str, str]]:
    """
    Fallback scraping method using requests with multiple bypass strategies
    """
    offers: List[Dict[str, str]] = []
    
    print(f"Starting requests-based scraping for {country} with {max_pages} pages")
    
    # Try multiple bypass strategies
    strategies = [
        scrape_with_scraperapi,  # Try ScraperAPI first if available
        scrape_with_direct_requests,  # Direct requests with enhanced headers
    ]
    
    for strategy_func in strategies:
        try:
            print(f"Trying strategy: {strategy_func.__name__}")
            result = strategy_func(max_pages, delay_seconds, country)
            if result and len(result) > 0:
                print(f"Success with {strategy_func.__name__}: {len(result)} offers found")
                return result
            else:
                print(f"Strategy {strategy_func.__name__} returned no offers")
        except Exception as e:
            print(f"Strategy {strategy_func.__name__} failed: {e}")
            continue
    
    return []

def scrape_with_scraperapi(max_pages: int, delay_seconds: float, country: str) -> List[Dict[str, str]]:
    """Scrape using ScraperAPI service to bypass anti-bot protection"""
    scraperapi_key = os.environ.get('SCRAPER_API_KEY')
    if not scraperapi_key:
        print("No SCRAPER_API_KEY found, skipping ScraperAPI strategy")
        return []
    
    print(f"Using ScraperAPI with key: {scraperapi_key[:5]}...")
    offers: List[Dict[str, str]] = []
    
    for page in range(max_pages):
        start = page * 10
        url = build_indeed_url(start=start, country=country)
        print(f"Scraping page {page + 1} via ScraperAPI: {url}")
        
        # Add delay
        delay = delay_seconds + random.uniform(2.0, 5.0)
        time.sleep(delay)
        
        try:
            # ScraperAPI endpoint
            scraperapi_url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={url}"
            
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
            
            resp = requests.get(scraperapi_url, headers=headers, timeout=60)
            print(f"ScraperAPI response status: {resp.status_code}")
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                job_cards = soup.select("div.job_seen_beacon") or soup.select(".resultContent")
                
                if job_cards:
                    page_offers = 0
                    for card in job_cards:
                        data = parse_job_card(card)
                        if data.get("link") and data.get("title"):
                            offers.append(data)
                            page_offers += 1
                            if page_offers <= 2:  # Only print first 2 offers
                                print(f"Added: {data['title'][:50]}...")
                    
                    print(f"Page {page + 1}: {page_offers} offers added via ScraperAPI")
                    return offers  # Return what we have
                else:
                    print("No job cards found in ScraperAPI response")
            else:
                print(f"ScraperAPI failed with status {resp.status_code}")
                
        except Exception as e:
            print(f"ScraperAPI error: {e}")
            continue
    
    return offers

def scrape_with_direct_requests(max_pages: int, delay_seconds: float, country: str) -> List[Dict[str, str]]:
    """Scrape directly with enhanced headers and delays"""
    offers: List[Dict[str, str]] = []
    session = requests.Session()
    
    # Enhanced headers to avoid bot detection
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
        "Pragma": "no-cache",
    }
    session.headers.update(headers)
    
    for page in range(max_pages):
        start = page * 10
        url = build_indeed_url(start=start, country=country)
        print(f"Scraping page {page + 1} directly: {url}")
        
        # Increase delay for direct requests
        delay = delay_seconds + random.uniform(5.0, 10.0) + (page * 3.0)
        print(f"Waiting {delay:.2f} seconds before request...")
        time.sleep(delay)
        
        try:
            resp = session.get(url, timeout=30, allow_redirects=True)
            print(f"Direct request HTTP {resp.status_code} for {url}")
            
            # Check if we're being blocked
            if resp.status_code in [403, 429]:
                print(f"Blocked with status {resp.status_code}")
                return []  # Don't continue if blocked
                
            if resp.status_code != 200:
                print(f"Failed with status {resp.status_code}")
                continue
                
            # Check response validity
            if len(resp.text) < 1000:
                print(f"Suspiciously short response ({len(resp.text)} chars)")
                continue
            
            # Parse the response
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Check if we got a valid Indeed page
            job_cards = soup.select("div.job_seen_beacon") or soup.select(".resultContent")
            if not job_cards:
                print("No job cards found in direct response")
                continue
            
            print(f"Successfully parsed page {page + 1} with {len(job_cards)} job cards")
            
            # Process the job cards
            page_offers = 0
            for card in job_cards:
                data = parse_job_card(card)
                if data.get("link") and data.get("title"):
                    offers.append(data)
                    page_offers += 1
                    if page_offers <= 2:  # Only print first 2 offers
                        print(f"Added: {data['title'][:50]}...")

            print(f"Page {page + 1}: {page_offers} offers added")
            
            # If we got offers, we're successful
            if page_offers > 0:
                print(f"Successfully scraped {len(offers)} offers so far")
                return offers  # Return early on success
                
        except requests.exceptions.RequestException as e:
            print(f"Direct request error: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return offers

if __name__ == "__main__":
    # Simple test function
    print("Testing Indeed scraper...")
    print("Environment variables:")
    for key in ['RENDER', 'SCRAPER_PROXIES']:
        if os.environ.get(key):
            print(f"  {key}: {os.environ.get(key)}")
    
    offers = scrape_indeed(max_pages=1, country="Maroc")
    print(f"Found {len(offers)} offers")
    for i, offer in enumerate(offers[:3]):  # Show first 3 offers
        print(f"{i+1}. {offer['title']} at {offer['company']} in {offer['location']}")
