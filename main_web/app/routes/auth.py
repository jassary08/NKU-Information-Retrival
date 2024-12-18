from flask import Blueprint, request, jsonify, session, current_app
from main_web.app.serveices.auth import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册接口"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        if not all([username, password, email]):
            return jsonify({'error': '请填写所有必填字段'}), 400

        users_collection = current_app.db.users
        AuthService.register_user(users_collection, username, password, email)
        return jsonify({'message': '注册成功'}), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': '注册失败，请稍后重试'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录接口"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not all([username, password]):
            return jsonify({'error': '请输入用户名和密码'}), 400

        users_collection = current_app.db.users
        token = AuthService.login_user(users_collection, username, password)

        session['token'] = token
        return jsonify({
            'username': username,
            'token': token
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        return jsonify({'error': '登录失败，请稍后重试'}), 500


@auth_bp.route('/check-login')
def check_login():
    """检查登录状态接口"""
    token = session.get('token')
    if not token:
        return jsonify({'error': '未登录'}), 401

    try:
        username = AuthService.verify_token(token)
        return jsonify({'username': username}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出接口"""
    session.clear()
    return jsonify({'message': '已退出登录'}), 200


@auth_bp.route('/search-history', methods=['GET'])
def get_search_history():
    """获取用户搜索历史接口"""
    token = session.get('token')
    if not token:
        return jsonify({'error': '未登录'}), 401

    try:
        username = AuthService.verify_token(token)
        search_history_collection = current_app.db.search_history

        history = search_history_collection.find(
            {'username': username},
            {'_id': 0, 'query': 1, 'timestamp': 1}
        ).sort('timestamp', -1).limit(20)

        return jsonify(list(history))
    except ValueError as e:
        return jsonify({'error': str(e)}), 401