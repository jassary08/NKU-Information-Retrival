from flask import Blueprint, request, jsonify, current_app, session, render_template
from main_web.app.serveices.search import SearchService
from main_web.app.serveices.auth import AuthService
from datetime import datetime
from bson.objectid import ObjectId

search_bp = Blueprint('search', __name__)


@search_bp.route('/')
def home():
    """渲染主页"""
    return render_template('web.html')


@search_bp.route('/search')
def search():
    """搜索接口"""
    query = request.args.get('q', '')
    query_type = request.args.get('type', 'normal')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    source = request.args.get('source')
    doc_type = request.args.get('doc_type')
    page = int(request.args.get('page', 1))

    if not query:
        return jsonify({"error": "请输入搜索关键词"})

    try:
        # 处理文档搜索
        if query_type == 'document':
            results = SearchService.search_documents(
                current_app.elasticsearch,
                query=query,
                doc_type=doc_type,
                start_date=start_date,
                end_date=end_date,
                page=page
            )
        else:
            # 处理新闻搜索
            token = session.get('token')
            user_preferences = None

            if token:
                try:
                    username = AuthService.verify_token(token)
                    search_history = current_app.db.search_history.find(
                        {'username': username},
                        {'_id': 0, 'query': 1, 'source': 1}
                    ).sort('timestamp', -1).limit(50)

                    user_preferences = SearchService.analyze_user_preferences(search_history)

                    # 记录搜索历史
                    current_app.db.search_history.update_one(
                        {
                            'username': username,
                            'query': query,
                            'source': source
                        },
                        {
                            '$set': {
                                'timestamp': datetime.utcnow()
                            }
                        },
                        upsert=True
                    )

                except ValueError:
                    pass  # Token 验证失败，继续搜索但不使用用户偏好

            results = SearchService.search_news(
                current_app.elasticsearch,
                current_app.db.snapshots,
                query=query,
                query_type=query_type,
                start_date=start_date,
                end_date=end_date,
                source=source,
                page=page,
                user_preferences=user_preferences
            )

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@search_bp.route('/suggest')
def suggest():
    """搜索建议接口"""
    prefix = request.args.get('q', '')
    if not prefix:
        return jsonify([])

    try:
        suggest_body = {
            "_source": ["title", "source", "url"],
            "suggest": {
                "title-suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": "title.suggest",
                        "size": 10,
                        "skip_duplicates": True,
                        "fuzzy": {
                            "fuzziness": "AUTO",
                            "prefix_length": 1
                        }
                    }
                }
            }
        }

        response = current_app.elasticsearch.search(
            index=current_app.config['NEWS_INDEX'],
            body=suggest_body
        )

        suggestions = response["suggest"]["title-suggest"][0]["options"]
        results = [
            {
                "text": suggestion["_source"]["title"],
                "source": suggestion["_source"].get("source", ""),
                "url": suggestion["_source"].get("url", "")
            }
            for suggestion in suggestions
        ]

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@search_bp.route('/snapshot/<snapshot_id>')
def view_snapshot(snapshot_id):
    """查看网页快照接口"""
    try:
        snapshot = current_app.db.snapshots.find_one({'_id': ObjectId(snapshot_id)})
        if snapshot:
            return render_template(
                'snapshot.html',
                html_content=snapshot['html_content'],
                captured_at=snapshot['captured_at'],
                original_url=snapshot['url']
            )
        return "未找到网页快照", 404
    except Exception as e:
        return str(e), 500