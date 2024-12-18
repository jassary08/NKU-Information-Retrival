import os


class Config:
    SECRET_KEY = os.urandom(24)
    JWT_SECRET = os.urandom(24)

    # Elasticsearch配置
    ELASTICSEARCH_HOST = "http://localhost:9200"
    ELASTICSEARCH_USER = "elastic"
    ELASTICSEARCH_PASSWORD = "123456"

    # MongoDB配置
    MONGODB_URI = 'mongodb://localhost:27017/'
    MONGODB_DB = 'nankai_news'

    # 索引名称
    NEWS_INDEX = "nankai_news_index"
    DOCS_INDEX = "nankai_docs_index"