from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from flask import current_app
class AuthService:
    @staticmethod
    def register_user(users_collection, username, password, email):
        if users_collection.find_one({'username': username}):
            raise ValueError('用户名已存在')

        if users_collection.find_one({'email': email}):
            raise ValueError('邮箱已被注册')

        hashed_password = generate_password_hash(password)
        user = {
            'username': username,
            'password': hashed_password,
            'email': email,
            'created_at': datetime.utcnow()
        }

        users_collection.insert_one(user)
        return True

    @staticmethod
    def login_user(users_collection, username, password):
        user = users_collection.find_one({'username': username})
        if not user or not check_password_hash(user['password'], password):
            raise ValueError('用户名或密码错误')

        token = jwt.encode(
            {
                'username': username,
                'exp': datetime.utcnow() + timedelta(days=1)
            },
            current_app.config['JWT_SECRET'],
            algorithm='HS256'
        )

        return token

    @staticmethod
    def verify_token(token):
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET'],
                algorithms=['HS256']
            )
            return payload['username']
        except jwt.ExpiredSignatureError:
            raise ValueError('登录已过期')
        except jwt.InvalidTokenError:
            raise ValueError('无效的令牌')