from pymongo import MongoClient
import logging
from datetime import datetime

class SnapshotCleaner:
   def __init__(self, uri="mongodb://localhost:27017", db_name="test"):
       self.client = MongoClient(uri)
       self.db = self.client[db_name]
       self.setup_logging()

   def setup_logging(self):
       logging.basicConfig(
           level=logging.INFO,
           format='%(asctime)s - %(levelname)s - %(message)s',
           handlers=[
               logging.FileHandler('snapshot_cleaning.log', encoding='utf-8'),
               logging.StreamHandler()
           ]
       )

   def clean_snapshots(self):
       news_collection = self.db.news
       snapshots_collection = self.db.snapshots

       # 获取news集合中的所有URL
       news_urls = set(news_collection.distinct('url'))
       logging.info(f"Found {len(news_urls)} unique URLs in news collection")

       # 删除不在news集合中的snapshots记录
       result = snapshots_collection.delete_many({
           'url': {'$nin': list(news_urls)}
       })

       logging.info(f"Removed {result.deleted_count} snapshots that were not referenced in news collection")
       logging.info(f"Remaining snapshots: {snapshots_collection.count_documents({})}")

       return result.deleted_count

   def cleanup(self):
       self.client.close()

def main():
   cleaner = None
   try:
       cleaner = SnapshotCleaner()
       removed_count = cleaner.clean_snapshots()
       logging.info(f"Snapshot cleaning completed. Total removed: {removed_count}")
   except Exception as e:
       logging.error(f"Error during snapshot cleaning: {str(e)}")
   finally:
       if cleaner:
           cleaner.cleanup()

if __name__ == "__main__":
   main()