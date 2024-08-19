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
    content_selectors = ['article', 'main', '.article-content', '.article__content', '.article-body', '.zn-body__paragraph']
    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            # Remove unwanted elements specific to Mashable
            unwanted_classes = [
                'ad-container', 'related-articles', 'share-buttons', 'author-box',
                'newsletter-signup', 'sidebar', 'comments-area', 'mashable-footer',
                'mashable-header', 'mashable-nav', 'social-share', 'sponsored-content',
                'article-tags', 'article-footer', 'article-header', 'see-also'
            ]
            for unwanted in content.select(', '.join(f'.{cls}' for cls in unwanted_classes)):
                unwanted.decompose()
            # Remove script, style, iframe, and svg tags
            for tag in content(['script', 'style', 'iframe', 'svg']):
                tag.decompose()
            return content
    logging.warning("Could not find main content using predefined selectors")
    return None

def bypass_paywall(driver):
    try:
        # Try closing any popups or dismissing paywalls
        close_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='CLOSE'], .close-button, .modal-close")
        for button in close_buttons:
            if button.is_displayed():
                button.click()
                logging.info("Popup or paywall dismissed")
                time.sleep(1)  # Wait for the popup to close
        return True
    except Exception as e:
        logging.info(f"No popup or paywall found or unable to dismiss: {str(e)}")
        return False

def scrape_mashable(url):
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

    bypass_successful = bypass_paywall(driver)

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

    title = soup.find('h1')
    title_text = extract_text(title) if title else "Title not found"
    logging.info(f"Article title: {title_text}")

    # Extract author and publication date
    author = soup.select_one('.author-name, .byline__author, .c-author__name')
    author_text = extract_text(author) if author else "Author not found"

    date = soup.select_one('time[datetime], .c-article__published')
    date_text = extract_text(date) if date else "Date not found"

    content_elements = main_content.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6'])
    content = "\n\n".join([
        extract_text(elem) for elem in content_elements
        if not elem.find_parent(['aside', 'figure', 'header', 'footer', 'nav'])
        and not any(cls in elem.get('class', []) for cls in ['ad-container', 'related-articles', 'share-buttons'])
    ])

    if not content or (not bypass_successful and re.search(r'subscribe|sign.?up|register', content, re.IGNORECASE)):
        logging.warning("Possible paywall detected")
        return "The article content might be behind a paywall."

    full_content = f"{title_text}\n\nBy {author_text}\n{date_text}\n\n{content}"
    full_content = '\n'.join(line.strip() for line in full_content.splitlines() if line.strip())

    logging.info("Article content successfully scraped")
    return full_content

if __name__ == "__main__":
    url = "https://mashable.com/article/screen-time-ios-iphone-wwdc-2019-improve/"
    article_content = scrape_mashable(url)
    print(article_content)
