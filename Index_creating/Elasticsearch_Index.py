import pymongo
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from bson import ObjectId


class NewsIndexer:
    def __init__(self,
                 mongo_host='localhost',
                 mongo_port=27017,
                 mongo_db='nankai_news',
                 es_host='localhost',
                 es_port=9200,
                 index_name='nankai_news_index'):
        # MongoDB连接
        self.mongo_client = pymongo.MongoClient(mongo_host, mongo_port)
        self.mongo_db = self.mongo_client[mongo_db]
        self.news_collection = self.mongo_db['news']

        # Elasticsearch连接
        self.es = Elasticsearch(
            [f'http://{es_host}:{es_port}'],
            basic_auth=('elastic', '123456'),  # 添加身份验证
            timeout = 600,  # 增加超时时间为30秒
            max_retries = 3,
            retry_on_timeout=True,# 添加重试机制
        )
        self.index_name = index_name

    def create_index(self):
        """创建Elasticsearch索引"""
        settings = {
            "index": {
                "number_of_replicas": 2,
                "number_of_shards": 1
            },
            "analysis": {
                "analyzer": {
                    "ik_smart_pinyin": {
                        "type": "custom",
                        "tokenizer": "ik_smart",
                        "filter": ["lowercase", "pinyin_filter"]
                    }
                },
                "filter": {
                    "pinyin_filter": {
                        "type": "pinyin",
                        "keep_full_pinyin": True,
                        "keep_joined_full_pinyin": True,
                        "keep_original": True,
                        "limit_first_letter_length": 16,
                        "remove_duplicated_term": True
                    }
                }
            }
        }

        mappings = {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                    "search_analyzer": "ik_smart",
                    "fields": {
                        "suggest": {
                            "type": "completion",
                            "analyzer": "ik_smart_pinyin",
                            "search_analyzer": "ik_smart_pinyin",
                            "preserve_separators": True,
                            "preserve_position_increments": True,
                            "max_input_length": 50
                        },
                    }
                },
                "url": {"type": "keyword"},
                "content": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                    "search_analyzer": "ik_smart"
                },
                "source": {"type": "keyword"},
                "date": {"type": "date", "format": "yyyy-MM-dd"}
            }
        }

        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)

        self.es.indices.create(
            index=self.index_name,
            body={
                "settings": settings,
                "mappings": mappings
            }
        )

    def prepare_documents(self):
        """准备索引文档"""
        documents = []
        for news_doc in self.news_collection.find():
            title = news_doc.get('title', '')
            doc = {
                "_id": str(news_doc['_id']),
                "title": title,
                "url": news_doc.get('url', ''),
                "content": news_doc.get('content', ''),
                "source": news_doc.get('source', ''),
                "date": news_doc.get('date', ''),
                "suggest": {
                    "input": [title],
                    "weight": 10
                }
            }
            documents.append(doc)

        return documents

    def close(self):
        """关闭数据库连接"""
        self.mongo_client.close()


def main():
    indexer = NewsIndexer(
        mongo_host='localhost',
        mongo_port=27017,
        mongo_db='nankai_news',
        es_host='localhost',
        es_port=9200,
        index_name='nankai_news_index'
    )

    try:
        print("开始创建索引...")
        indexer.create_index()
        print("索引结构创建完成")

        print("开始准备文档...")
        documents = indexer.prepare_documents()
        print(f"文档准备完成，共 {len(documents)} 条记录")

        print("开始批量索引文档...")
        success, failed = bulk(
            indexer.es,
            [
                {
                    '_index': indexer.index_name,
                    '_id': doc['_id'],
                    **doc
                }
                for doc in documents
            ],
            refresh=True
        )
        print(f"文档索引完成，成功：{success} 条，失败：{failed} 条")

    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        indexer.close()


if __name__ == "__main__":
    main()