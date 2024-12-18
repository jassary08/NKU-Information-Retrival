from pymongo import MongoClient
import gridfs
from datetime import datetime
import logging
from config import Config


class Database:
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URI)
        self.db = self.client[Config.DB_NAME]
        self.news_collection = self.db['news']
        self.snapshot_collection = self.db['snapshots']
        self.fs = gridfs.GridFS(self.db)
        self._create_indexes()

    def _create_indexes(self):
        self.news_collection.create_index([('url', 1)], unique=True)
        self.snapshot_collection.create_index([('url', 1), ('captured_at', -1)])

    def save_news_batch(self, news_items, batch_number=None):
        inserted_count = updated_count = 0

        for item in news_items:
            try:
                item['created_at'] = datetime.now()
                item['batch_number'] = batch_number

                result = self.news_collection.update_one(
                    {'url': item['url']},
                    {'$set': item},
                    upsert=True
                )

                if result.upserted_id:
                    inserted_count += 1
                elif result.modified_count:
                    updated_count += 1

            except Exception as e:
                logging.error(f"Error saving to MongoDB: {str(e)}")
                continue

        return inserted_count, updated_count

    def get_news_count(self):
        return self.news_collection.count_documents({})

    def close(self):
        self.client.close()