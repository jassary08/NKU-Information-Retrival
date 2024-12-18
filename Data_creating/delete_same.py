from pymongo import MongoClient
import logging
from datetime import datetime


class SnapshotDeduplicator:
    def __init__(self, uri="mongodb://localhost:27017", db_name="nankai_news"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('snapshot_deduplication.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def remove_duplicates(self):
        collection = self.db.snapshots

        # 找出所有重复的URL
        pipeline = [
            {
                "$group": {
                    "_id": "$url",
                    "count": {"$sum": 1},
                    "docs": {"$push": {"_id": "$_id"}}
                }
            },
            {
                "$match": {"count": {"$gt": 1}}
            }
        ]

        duplicates = collection.aggregate(pipeline)
        total_removed = 0

        for doc in duplicates:
            url = doc['_id']
            ids = doc['docs']

            # 保留第一条，删除其他的
            keep_id = ids[0]['_id']
            remove_ids = [d['_id'] for d in ids[1:]]

            try:
                # 删除多余的记录
                result = collection.delete_many({"_id": {"$in": remove_ids}})
                total_removed += result.deleted_count

                # 记录处理信息
                logging.info(f"URL: {url}")
                logging.info(f"Kept document ID: {keep_id}")
                logging.info(f"Removed {result.deleted_count} duplicates\n")

            except Exception as e:
                logging.error(f"Error processing URL {url}: {str(e)}")

        return total_removed

    def cleanup(self):
        if self.client:
            self.client.close()


def main():
    deduplicator = None
    try:
        deduplicator = SnapshotDeduplicator()

        # 执行去重
        total_removed = deduplicator.remove_duplicates()

        # 记录结果
        logging.info("Deduplication completed")
        logging.info(f"Total duplicates removed: {total_removed}")

    except Exception as e:
        logging.error(f"Deduplication failed: {str(e)}")
    finally:
        if deduplicator:
            deduplicator.cleanup()


if __name__ == "__main__":
    main()