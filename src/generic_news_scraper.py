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

def extract_text(element):
    return ' '.join(element.stripped_strings)

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

def bypass_paywall(driver):
    # Attempt to bypass common paywall implementations
    try:
        # Try clicking a "REGISTER FOR FREE" button
        register_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'REGISTER FOR FREE')]"))
        )
        register_button.click()
        logging.info("Clicked 'REGISTER FOR FREE' button")
        time.sleep(2)
    except TimeoutException:
        logging.info("No 'REGISTER FOR FREE' button found or unable to click")

    try:
        # Try closing a popup
        close_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Close']"))
        )
        close_button.click()
        logging.info("Popup closed successfully")
    except TimeoutException:
        logging.info("No popup found or unable to close")

def find_main_content(soup):
    # Try to find the main content container
    content_selectors = ['article', 'main', 'div.content', 'div.article-body']
    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            # Remove headers, footers, and side news sections
            for unwanted in content.select('header, footer, aside, nav, section.related-news'):
                unwanted.decompose()
            return content
    return None

def scrape_article(url):
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

    # Wait for the page to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        logging.error("Timeout waiting for page to load")
        driver.quit()
        return "Timeout: Page failed to load"

    bypass_paywall(driver)

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

    title = main_content.find(['h1', 'h2'])
    title_text = extract_text(title) if title else "Title not found"
    logging.info(f"Article title: {title_text}")

    content_elements = main_content.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6'])
    content = "\n\n".join([
        extract_text(elem) for elem in content_elements
        if not elem.find_parent(['aside', 'figure', 'header', 'footer', 'nav', 'section'])
        and not any(cls in elem.get('class', []) for cls in ['paywall', 'ad', 'promo', 'social-share'])
        and not (elem.name == 'h2' and elem.text.strip() == "Stream on")
        and not (elem.name in ['p', 'h2', 'h3', 'h4', 'h5', 'h6'] and elem.text.strip().startswith("MORE:"))
    ])

    if not content or re.search(r'subscribe|sign.?up|register', content, re.IGNORECASE):
        logging.warning("Possible paywall detected")
        return "The article content might be behind a paywall."

    full_content = f"{title_text}\n\n{content}"
    full_content = '\n'.join(line.strip() for line in full_content.splitlines() if line.strip())

    logging.info("Article content successfully scraped")
    return full_content


urls = [
    "https://news.google.com/rss/articles/CBMicEFVX3lxTFBjeGtxeElTQ0NlVzJ4SVNsZzJxdnFPQjFKZTdHVVdXTVJOVmRIOXJFU2hXV0s1NUV1YXJPMGtIdUFSOTJVRFV2VkdhdU5oSVdKcS1PR1UtMlduNXhnU3hCTHJDU2sxNXRWRXVSdjRUVmI?oc=5",
    "https://abcnews.go.com/Politics/trump-campaign-office-burglarized-virginia-officials-release-photo/story?id=112789192",
    'http://www.afr.com/companies/retail/former-senior-super-retail-lawyer-revealed-as-second-whistleblower-20240814-p5k2b5',
    "https://www.washingtonpost.com/politics/2024/08/18/harris-trump-post-abc-ipsos-poll/"
]
for url in urls:
    print(f"Scraping: {url}")
    article_content = scrape_article(url)
    print(article_content)
    print("\n" + "="*50 + "\n")
