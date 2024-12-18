from pymongo import MongoClient
import logging
from datetime import datetime


class NewsRecordCleaner:
    def __init__(self, uri="mongodb://localhost:27017", db_name="test"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('news_cleaning.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def remove_orphaned_news(self):
        news_collection = self.db.news
        snapshot_urls = set(self.db.snapshots.distinct('url'))

        # Find and remove news records without snapshots
        result = news_collection.delete_many({
            'url': {'$nin': list(snapshot_urls)}
        })

        logging.info(f"Initial news records count: {news_collection.count_documents({})}")
        logging.info(f"Removed {result.deleted_count} news records without snapshots")
        logging.info(f"Remaining news records: {news_collection.count_documents({})}")

        return result.deleted_count

    def cleanup(self):
        self.client.close()


def main():
    cleaner = None
    try:
        cleaner = NewsRecordCleaner()
        removed_count = cleaner.remove_orphaned_news()
        logging.info(f"News cleaning completed successfully")
        logging.info(f"Total records removed: {removed_count}")
    except Exception as e:
        logging.error(f"Error during cleaning process: {str(e)}")
    finally:
        if cleaner:
            cleaner.cleanup()


if __name__ == "__main__":
    main()