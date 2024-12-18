from bs4 import BeautifulSoup
import re
import logging
from config import Config
import os

class NewsParser:
    @staticmethod
    def parse_list_page(soup):
        news_items = []

        # Find the news list container
        news_container = soup.find('ul', class_='wp_article_list')
        if not news_container:
            return news_items

        # Get all news items
        articles = news_container.find_all('li', class_='list_item')

        for article in articles:
            # Extract title and link
            article_title = article.find('span', class_='Article_Title')
            if not article_title:
                continue

            link_tag = article_title.find('a')
            if not link_tag:
                continue

            # Get URL
            href = link_tag.get('href', '')
            if href:
                if href.startswith('http'):
                    news_url = href
                else:
                    news_url = f"https://economics.nankai.edu.cn{href}"
            else:
                news_url = ''

            # Get title
            title = link_tag.get('title', '').strip()

            # Get date
            date_span = article.find('span', class_='Article_PublishDate')
            date = date_span.text.strip() if date_span else '无日期'

            # Save the extracted information
            news_items.append({
                'title': title,
                'url': news_url,
                'date': date,
                'source': '南开大学经济学院'
            })

        return news_items

    @staticmethod
    def parse_detail_page(soup):
        """
        Parse the news content from the HTML page.

        Args:
            soup (BeautifulSoup): BeautifulSoup object of the HTML page

        Returns:
            dict: Dictionary containing only the content
        """
        try:
            content_list = []

            # Find the article container
            article_content = soup.find('div', class_='wp_articlecontent')

            if article_content:
                # Find all paragraphs that contain content
                paragraphs = article_content.find_all(['p', 'span'])

                for p in paragraphs:
                    # Get text content
                    text = p.get_text().strip()

                    # Skip empty paragraphs
                    if not text:
                        continue

                    # Skip image descriptions
                    if text.startswith('sudyfile-attr') or 'original-src' in text:
                        continue

                    # Skip metadata
                    if '通讯员' in text or '编辑' in text or '审核' in text:
                        continue

                    # Clean up whitespace and special characters
                    text = re.sub(r'\s+', ' ', text)
                    text = text.replace('\u3000', '')  # Remove Chinese full-width space
                    text = text.replace('\xa0', ' ')  # Remove &nbsp;
                    text = text.replace('\r', '')  # Remove carriage returns
                    text = text.replace('\n', '')  # Remove newlines
                    text = text.strip()

                    # Only add non-empty paragraphs
                    if text:
                        content_list.append(text)

            # Join paragraphs with newlines
            content = '\n'.join(content_list) if content_list else '无内容'

            # Find attachments
            attachments = NewsParser.find_attachments(soup, Config.BASE_URL)

            return {
                'content': content
            }, attachments

        except Exception as e:
            logging.error(f"Error parsing detail page: {str(e)}")
            return {'content': '无内容'}, attachments
    @staticmethod
    def find_attachments(soup, base_url):
        attachments = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if any(ext in href for ext in Config.SUPPORTED_ATTACHMENTS):
                full_url = base_url + href if href.startswith('/') else href
                attachments.append({
                    'url': full_url,
                    'filename': os.path.basename(href),
                    'title': link.text.strip()
                })
        return attachments