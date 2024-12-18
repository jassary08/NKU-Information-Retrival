import requests
from datetime import datetime
import random
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from config import Config
from database import Database
from parser import NewsParser
from bs4 import BeautifulSoup
import time
import gridfs

class NewsScraperNankai:
    def __init__(self):
        self.db = Database()
        self._setup_logging()
        self.fs = gridfs.GridFS(self.db.db)

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def get_page_urls(self):
        urls = [Config.FIRST_PAGE]
        urls.extend(Config.PAGE_TEMPLATE.format(i) for i in range(1, Config.MAX_PAGES + 1))
        return urls

    def get_soup(self, url, retries=3):
        for i in range(retries):
            try:
                time.sleep(random.uniform(1, 3))
                response = requests.get(url, headers=Config.HEADERS, timeout=10)
                response.encoding = 'utf-8'

                if response.status_code == 200:
                    return BeautifulSoup(response.text, 'html.parser'), response.text

            except Exception as e:
                logging.error(f"Attempt {i + 1} failed for {url}: {str(e)}")
                if i == retries - 1:
                    logging.error(f"All attempts failed for {url}")
                time.sleep(random.uniform(2, 5))

        return None, None

    def save_snapshot(self, url, html_content):
        try:
            snapshot_data = {
                'url': url,
                'html_content': html_content,
                'captured_at': datetime.now(),
                'content_hash': hashlib.md5(html_content.encode('utf-8')).hexdigest()
            }
            self.db.snapshot_collection.insert_one(snapshot_data)
            return snapshot_data['content_hash']
        except Exception as e:
            logging.error(f"Error saving snapshot for {url}: {str(e)}")
            return None

    def process_news_list_page(self, url):
        logging.info(f"Processing list page: {url}")
        soup, html_content = self.get_soup(url)
        if not soup:
            return []

        snapshot_hash = self.save_snapshot(url, html_content)
        news_items = NewsParser.parse_list_page(soup)
        logging.info(f"Found {len(news_items)} news items on page {url}")

        for item in news_items:
            logging.info(f"Processing: {item['title']}")
            detail_soup, detail_html = self.get_soup(item['url'])
            if detail_soup:
                detail_content, attachments = NewsParser.parse_detail_page(detail_soup)
                item.update(detail_content)
                item['snapshot_hash'] = self.save_snapshot(item['url'], detail_html)

                # Handle attachments
                item['attachments'] = []
                for attachment in attachments:
                    file_id = self.save_attachment(attachment)
                    if file_id:
                        item['attachments'].append({
                            'file_id': file_id,
                            'url': attachment['url'],
                            'filename': attachment['filename'],
                            'title': attachment['title']
                        })
                        logging.info(f"Saved attachment: {attachment['filename']}")

            time.sleep(random.uniform(1, 2))

        return news_items
    def save_attachment(self, attachment_info):
        """保存附件到GridFS"""
        try:
            response = requests.get(attachment_info['url'], headers=Config.HEADERS, timeout=30)
            if response.status_code == 200:
                file_id = self.fs.put(
                    response.content,
                    filename=attachment_info['filename'],
                    url=attachment_info['url'],
                    title=attachment_info['title'],
                    upload_date=datetime.now()
                )
                return file_id
        except Exception as e:
            logging.error(f"Error saving attachment {attachment_info['url']}: {str(e)}")
        return None

    def scrape_batch(self, urls, batch_size=10):
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            batch_number = i // batch_size + 1

            logging.info(f"Processing batch {batch_number}")

            with ThreadPoolExecutor(max_workers=5) as executor:
                batch_results = list(executor.map(self.process_news_list_page, batch_urls))

            batch_news = [item for sublist in batch_results if sublist for item in sublist]
            inserted, updated = self.db.save_news_batch(batch_news, batch_number)

            logging.info(f"Batch {batch_number} completed: {inserted} new items, {updated} updates")
            time.sleep(random.uniform(3, 5))

    def scrape(self):
        logging.info("Starting to scrape news...")
        urls = self.get_page_urls()
        self.scrape_batch(urls)
        logging.info(f"Scraping completed. Total news: {self.db.get_news_count()}")

    def cleanup(self):
        self.db.close()
def main():
    scraper = None
    try:
        scraper = NewsScraperNankai()
        scraper.scrape()
    except Exception as e:
        logging.error(f"An error occurred during scraping: {str(e)}")
    finally:
        if scraper:
            scraper.cleanup()


if __name__ == "__main__":
    main()