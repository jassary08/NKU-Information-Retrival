from datetime import datetime
from collections import Counter
import re
from flask import current_app

class SearchService:
    @staticmethod
    def analyze_user_preferences(search_history):
        keywords = []
        sources = []
        for entry in search_history:
            query = entry.get('query', '')
            words = re.findall(r'\w+', query.lower())
            keywords.extend(words)
            source = entry.get('source')
            if source:
                sources.append(source)

        keyword_counts = Counter(keywords)
        source_counts = Counter(sources)

        return {
            'top_keywords': [word for word, count in keyword_counts.most_common(10)],
            'top_sources': [source for source, count in source_counts.most_common(5)]
        }

    @staticmethod
    def search_news(es, snapshots_collection, query, query_type="normal", start_date=None,
                   end_date=None, source=None, page=1, size=10, user_preferences=None):
        from_value = (page - 1) * size

        search_body = {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "must": [],
                            "filter": []
                        }
                    },
                    "functions": [
                        {
                            "exp": {
                                "date": {
                                    "origin": "now",
                                    "scale": "180d",
                                    "decay": 0.5,
                                    "offset": "7d"
                                }
                            },
                            "weight": 0.3
                        }
                    ],
                    "score_mode": "multiply",
                    "boost_mode": "multiply"
                }
            },
            "highlight": {
                "fields": {
                    "title": {"number_of_fragments": 1},
                    "content": {"number_of_fragments": 3, "fragment_size": 150}
                },
                "pre_tags": ["<strong>"],
                "post_tags": ["</strong>"]
            },
            "from": from_value,
            "size": size,
            "_source": ["title", "content", "url", "source", "date"]
        }

        # Add query based on type
        if query_type == "phrase":
            search_body["query"]["function_score"]["query"]["bool"]["must"].append({
                "bool": {
                    "should": [
                        {
                            "match_phrase": {
                                "title": {
                                    "query": query,
                                    "slop": 0,
                                    "boost": 3.0
                                }
                            }
                        },
                        {
                            "match_phrase": {
                                "content": {
                                    "query": query,
                                    "slop": 0,
                                    "boost": 1.0
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 2
                }
            })
        elif query_type == "wildcard":
            # 区分通配符处理逻辑
            has_wildcard = any(char in query for char in ['*', '?'])

            if has_wildcard:
                # 如果用户手动输入了通配符，保持原样，使用 wildcard 查询
                search_body["query"]["function_score"]["query"]["bool"]["must"].extend([
                    {
                        "bool": {
                            "should": [
                                {
                                    "wildcard": {
                                        "title": {
                                            "value": query,
                                            "boost": 3
                                        }
                                    }
                                },
                                {
                                    "wildcard": {
                                        "content": {
                                            "value": query
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ])
            else:
                # 如果没有通配符，使用分词和模糊匹配组合
                processed_query = f"*{query}*"
                search_body["query"]["function_score"]["query"]["bool"]["must"].extend([
                    {
                        "bool": {
                            "should": [
                                # 分词匹配
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["title^3", "content"],
                                        "operator": "OR",
                                        "minimum_should_match": "70%",
                                        "analyzer": "ik_smart"
                                    }
                                },
                                # 模糊匹配
                                {
                                    "query_string": {
                                        "fields": ["title^3", "content"],
                                        "query": processed_query,
                                        "analyze_wildcard": True,
                                        "default_operator": "AND"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }
                ])
        else:
            search_body["query"]["function_score"]["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "title.autocomplete^2", "content"],
                    "type": "best_fields",
                    "operator": "and",
                    "fuzziness": "AUTO"
                }
            })

        # Add filters
        if start_date or end_date:
            date_filter = {"range": {"date": {}}}
            if start_date:
                date_filter["range"]["date"]["gte"] = start_date
            if end_date:
                date_filter["range"]["date"]["lte"] = end_date
            search_body["query"]["function_score"]["query"]["bool"]["filter"].append(date_filter)

        if source:
            source_filter = {"term": {"source": source}}
            search_body["query"]["function_score"]["query"]["bool"]["filter"].append(source_filter)

        # Add user preferences
        if user_preferences:
            if user_preferences.get('top_keywords'):
                search_body["query"]["function_score"]["query"]["bool"]["should"] = [
                    {
                        "match": {
                            "content": {
                                "query": keyword,
                                "boost": 0.1
                            }
                        }
                    }
                    for keyword in user_preferences['top_keywords']
                ]

        try:
            response = es.search(index=current_app.config['NEWS_INDEX'], body=search_body)
            hits = response["hits"]["hits"]
            results = []

            for hit in hits:
                source = hit["_source"]
                highlight = hit.get("highlight", {})
                url = source["url"]

                mongo_doc = snapshots_collection.find_one(
                    {"url": url},
                    {"_id": 1, "pagerank_score": 1, "captured_at": 1}
                )

                result = {
                    "title": highlight.get("title", [source["title"]])[0],
                    "url": url,
                    "content": " ... ".join(highlight.get("content", [source["content"][:200] + "..."])),
                    "source": source["source"],
                    "date": source["date"]
                }

                if mongo_doc:
                    result["snapshot"] = {
                        "id": str(mongo_doc["_id"]),
                        "captured_at": mongo_doc.get("captured_at")
                    }

                results.append(result)

            return {
                "results": results,
                "total": response["hits"]["total"]["value"],
                "page": page,
                "size": size
            }

        except Exception as e:
            raise e

    @staticmethod
    def search_documents(es, query, doc_type=None, start_date=None, end_date=None, page=1, size=10):
        from_value = (page - 1) * size

        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^4", "content", "filename"],
                                "type": "best_fields",
                                "operator": "and"
                            }
                        }
                    ],
                    "filter": []
                }
            },
            "highlight": {
                "fields": {
                    "title": {"number_of_fragments": 1},
                    "content": {"number_of_fragments": 2, "fragment_size": 150}
                },
                "pre_tags": ["<strong>"],
                "post_tags": ["</strong>"]
            },
            "from": from_value,
            "size": size,
            "_source": ["title", "content", "filename", "file_type", "url", "date", "length"]
        }

        if doc_type:
            search_body["query"]["bool"]["filter"].append(
                {"term": {"file_type": doc_type.lower()}}
            )

        try:
            response = es.search(index=current_app.config['DOCS_INDEX'], body=search_body)
            hits = response["hits"]["hits"]
            results = []

            for hit in hits:
                source = hit["_source"]
                highlight = hit.get("highlight", {})

                result = {
                    "title": highlight.get("title", [source["title"]])[0],
                    "content": " ... ".join(highlight.get("content", [source["content"][:200] + "..."])),
                    "filename": source["filename"],
                    "file_type": source["file_type"],
                    "url": source["url"],
                    "date": source.get("date"),
                    "length": source["length"]
                }

                results.append(result)

            return {
                "results": results,
                "total": response["hits"]["total"]["value"],
                "page": page,
                "size": size
            }

        except Exception as e:
            raise e