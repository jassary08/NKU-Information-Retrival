from pymongo import MongoClient
import logging

class URLAnalyzer:
    def __init__(self, uri="mongodb://localhost:27017", db_name="nankai_news"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('url_analysis.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def analyze_urls(self):
        news_urls = set(self.db.news.distinct('url'))
        snapshot_urls = set(self.db.snapshots.distinct('url'))

        # Calculate statistics
        total_news_urls = len(news_urls)
        total_snapshot_urls = len(snapshot_urls)
        common_urls = news_urls.intersection(snapshot_urls)
        only_in_news = news_urls - snapshot_urls
        only_in_snapshots = snapshot_urls - news_urls

        # Log results
        logging.info(f"Unique URLs in news collection: {total_news_urls}")
        logging.info(f"Unique URLs in snapshots collection: {total_snapshot_urls}")
        logging.info(f"URLs present in both collections: {len(common_urls)}")
        logging.info(f"URLs only in news: {len(only_in_news)}")
        logging.info(f"URLs only in snapshots: {len(only_in_snapshots)}")

    def cleanup(self):
        self.client.close()

def main():
    analyzer = None
    try:
        analyzer = URLAnalyzer()
        analyzer.analyze_urls()
    except Exception as e:
        logging.error(f"Error during analysis: {str(e)}")
    finally:
        if analyzer:
            analyzer.cleanup()

if __name__ == "__main__":
    main()