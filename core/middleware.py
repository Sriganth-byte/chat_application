"""
JWT Authentication Middleware for Django Channels WebSocket connections.

Usage:
    Connect with: ws://host/ws/chat/1/?token=<access_token>

Flow:
    1. Extract token from query string
    2. Decode and validate using SimpleJWT
    3. Fetch user from DB and inject into scope
    4. Fall back to AnonymousUser on any failure
"""
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def get_user_from_token(token_key):
    """Validate JWT access token and return the corresponding user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        token = AccessToken(token_key)
        user_id = token['user_id']
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Authenticates WebSocket connections using a JWT token
    passed as a query parameter: ?token=<access_token>
    """
    async def __call__(self, scope, receive, send):
        # Only process WebSocket connections
        if scope['type'] == 'websocket':
            query_string = scope.get('query_string', b'').decode()
            params = parse_qs(query_string)
            token_list = params.get('token', [])

            if token_list:
                scope['user'] = await get_user_from_token(token_list[0])
            else:
                scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)
