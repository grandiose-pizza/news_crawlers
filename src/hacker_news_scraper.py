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
    # Check for front page
    content = soup.select_one('table.itemlist')
    if content:
        return content

    # Check for individual story page
    content = soup.select_one('.fatitem')
    if content:
        comments = soup.select_one('table.comment-tree')
        if comments:
            content.append(comments)
        return content

    logging.warning("Could not find main content using predefined selectors")
    return None

def scrape_hacker_news(url):
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

    # Extract stories or comments
    items = main_content.find_all('tr', class_='athing')
    content = []

    for item in items:
        title = item.find('span', class_='titleline')
        if title:
            title_text = extract_text(title)
            url = title.find('a')['href'] if title.find('a') else ''
            score = extract_text(item.find_next_sibling('tr').find('span', class_='score')) if item.find_next_sibling('tr') else 'No score'
            author = extract_text(item.find_next_sibling('tr').find('a', class_='hnuser')) if item.find_next_sibling('tr') else 'No author'
            content.append(f"Title: {title_text}\nURL: {url}\nScore: {score}\nAuthor: {author}\n")
        else:
            comment = item.find('span', class_='commtext')
            if comment:
                comment_text = extract_text(comment)
                author = extract_text(item.find('a', class_='hnuser')) if item.find('a', class_='hnuser') else 'No author'
                content.append(f"Comment by {author}: {comment_text}\n")

    full_content = "\n".join(content)

    logging.info("Hacker News content successfully scraped")
    return full_content

if __name__ == "__main__":
    url = "https://news.ycombinator.com/"
    hacker_news_content = scrape_hacker_news(url)
    print(hacker_news_content)
