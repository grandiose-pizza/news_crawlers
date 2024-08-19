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
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

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
    content_selectors = [
        '#siteTable',  # Main content area for Reddit
        '.thing',      # Individual post container
        '.entry'       # Post content
    ]
    for selector in content_selectors:
        content = soup.select(selector)
        if content:
            # Remove unwanted elements
            for unwanted in content:
                for elem in unwanted.select('.promoted, .ad-container, .sponsored-headline'):
                    elem.decompose()
            return content
    logging.warning("Could not find main content using predefined selectors")
    return None

def scrape_reddit_r_all(url):
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
            EC.presence_of_element_located((By.ID, "siteTable"))
        )
    except TimeoutException:
        logging.error("Timeout waiting for page to load")
        driver.quit()
        return "Timeout: Page failed to load"

    # Scroll to load more content
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source, 'html.parser')
    main_content = find_main_content(soup)

    if not main_content:
        logging.error("Could not find the main content on the page")
        return "Could not find the main content on the page."

    posts = []
    for post in main_content:
        title = post.select_one('.title a')
        title_text = extract_text(title) if title else "Title not found"

        author = post.select_one('.author')
        author_text = extract_text(author) if author else "Author not found"

        score = post.select_one('.score.unvoted')
        score_text = extract_text(score) if score else "Score not found"

        comments_link = post.select_one('.comments')
        comments_text = extract_text(comments_link) if comments_link else "Comments link not found"

        posts.append(f"Title: {title_text}\nAuthor: {author_text}\nScore: {score_text}\nComments: {comments_text}\n")

    full_content = "\n".join(posts)
    logging.info("Reddit r/all content successfully scraped")
    return full_content

if __name__ == "__main__":
    url = "https://www.reddit.com/r/all/"
    reddit_content = scrape_reddit_r_all(url)
    print(reddit_content)
