from .settings import *  # noqa

DEBUG = False

ALLOWED_HOSTS = _split_env_list(os.getenv('ALLOWED_HOSTS')) or ['routeplanner.local']

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = _split_env_list(os.getenv('CORS_ALLOWED_ORIGINS'))

CSRF_TRUSTED_ORIGINS = _split_env_list(os.getenv('CSRF_TRUSTED_ORIGINS'))
if not CSRF_TRUSTED_ORIGINS and CORS_ALLOWED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [origin for origin in CORS_ALLOWED_ORIGINS if origin.startswith(('http://', 'https://'))]

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'None')
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'None')
