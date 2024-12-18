from flask import Flask
from elasticsearch import Elasticsearch
from pymongo import MongoClient
from main_web.config import Config
from main_web.app.routes.auth import auth_bp
from main_web.app.routes.search import search_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Elasticsearch
    app.elasticsearch = Elasticsearch(
        app.config['ELASTICSEARCH_HOST'],
        basic_auth=(app.config['ELASTICSEARCH_USER'], app.config['ELASTICSEARCH_PASSWORD']),
        verify_certs=False
    )

    # Initialize MongoDB
    mongo_client = MongoClient(app.config['MONGODB_URI'])
    app.db = mongo_client[app.config['MONGODB_DB']]

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)

    return app