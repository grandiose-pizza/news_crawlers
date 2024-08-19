from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import re
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info(f"Chrome WebDriver initialized. Version: {driver.capabilities['browserVersion']}")
        return driver
    except WebDriverException as e:
        logging.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
        return None

def extract_text(element):
    return ' '.join(element.stripped_strings)

def find_main_content(soup):
    content_selectors = ['article', 'main', '.article-body', '#main-content']
    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            # Remove unwanted elements specific to BBC Sport
            for unwanted in content.select('.social-share, .ad-wrapper, .related-content'):
                unwanted.decompose()
            return content
    return None

def handle_live_updates(driver):
    try:
        live_updates = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".lx-stream__feed"))
        )
        updates = live_updates.find_elements(By.CSS_SELECTOR, ".lx-stream-post")
        return [update.text for update in updates]
    except TimeoutException:
        logging.info("No live updates found")
        return []

def scrape_bbc_sport(url):
    driver = initialize_driver()
    if not driver:
        return "Failed to initialize WebDriver"

    try:
        logging.info(f"Navigating to URL: {url}")
        driver.get(url)
    except WebDriverException as e:
        logging.error(f"Failed to navigate to URL: {str(e)}")
        driver.quit()
        return f"Navigation failed: {str(e)}"

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        logging.error("Timeout waiting for page to load")
        driver.quit()
        return "Timeout: Page failed to load"

    # Handle live updates if present
    live_updates = handle_live_updates(driver)

    # Scroll to load dynamic content
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)  # Wait for content to load

    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source, 'html.parser')
    main_content = find_main_content(soup)

    if not main_content:
        logging.error("Could not find the main content on the page")
        return "Could not find the main content on the page."

    title = main_content.find('h1')
    title_text = extract_text(title) if title else "Title not found"
    logging.info(f"Article title: {title_text}")

    content_elements = main_content.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6'])
    content = "\n\n".join([
        extract_text(elem) for elem in content_elements
        if not elem.find_parent(['aside', 'figure', 'header', 'footer', 'nav'])
        and not any(cls in elem.get('class', []) for cls in ['tags', 'related-content'])
    ])

    full_content = f"{title_text}\n\n{content}"
    if live_updates:
        full_content += "\n\nLive Updates:\n" + "\n".join(live_updates)

    full_content = '\n'.join(line.strip() for line in full_content.splitlines() if line.strip())

    logging.info("Article content successfully scraped")
    return full_content

if __name__ == "__main__":
    url = "http://www.bbc.co.uk/sport/football/live/c2041nprd9nt"
    result = scrape_bbc_sport(url)
    print(result)
