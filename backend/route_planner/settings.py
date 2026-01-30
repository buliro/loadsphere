from pathlib import Path
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

PLANNER_TEMPLATE_DIR = os.path.join(BASE_DIR, 'planner/templates')


def _resolve_frontend_dist_path() -> str:
    candidate_paths = []

    env_path = os.getenv('FRONTEND_DIST_PATH')
    if env_path:
        candidate_paths.append(env_path)

    candidate_paths.extend(
        [
            os.path.join(BASE_DIR, 'dist'),
            os.path.join(BASE_DIR.parent, 'React', 'dist'),
            os.path.join(BASE_DIR.parent, 'frontend', 'dist'),
        ]
    )

    for path in candidate_paths:
        if path and os.path.exists(path):
            return os.path.abspath(path)

    return os.path.abspath(candidate_paths[0]) if candidate_paths else os.path.join(BASE_DIR, 'dist')


FRONTEND_DIST_PATH = _resolve_frontend_dist_path()
FRONTEND_ASSETS_PATH = os.path.join(FRONTEND_DIST_PATH, 'assets')

template_dirs = [PLANNER_TEMPLATE_DIR]
if os.path.exists(FRONTEND_DIST_PATH):
    template_dirs.append(FRONTEND_DIST_PATH)

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-very-secret-key-change-in-production')


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


DEBUG = _get_bool_env('DEBUG', True)


def _split_env_list(value, default=None):
    if value:
        return [item.strip() for item in value.split(',') if item.strip()]
    return default[:] if default else []


if DEBUG:
    ALLOWED_HOSTS = _split_env_list(os.getenv('ALLOWED_HOSTS'), ['*'])
else:
    ALLOWED_HOSTS = _split_env_list(os.getenv('ALLOWED_HOSTS')) or ['routeplanner.local']

DEFAULT_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0'}
for host in DEFAULT_HOSTS:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'graphene_django',
    'corsheaders',
    'planner',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'route_planner.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': template_dirs,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'route_planner.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'route_planner'),
        'USER': os.getenv('DB_USER', 'user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'password'),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'TEST': {
            'NAME': os.getenv('DB_TEST_NAME', 'route_planner_test'),
        }
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'planner/static'),
]

# Add frontend dist path to serve React build files
if os.path.exists(FRONTEND_DIST_PATH):
    STATICFILES_DIRS.insert(0, FRONTEND_DIST_PATH)  # Insert at beginning for priority

if os.path.exists(FRONTEND_ASSETS_PATH):
    STATICFILES_DIRS.append(FRONTEND_ASSETS_PATH)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# GraphQL Configuration
GRAPHENE = {
    'SCHEMA': 'planner.schema.schema',
    'MIDDLEWARE': [
        'graphql_jwt.middleware.JSONWebTokenMiddleware',
    ],
}

AUTHENTICATION_BACKENDS = [
    'planner.auth_backend.EmailOrUsernameModelBackend',
    'graphql_jwt.backends.JSONWebTokenBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# JWT Settings
GRAPHQL_JWT = {
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=7),
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=30),
    'JWT_AUTH_HEADER_PREFIX': 'Bearer',
    'JWT_ALGORITHM': 'HS256',
    'JWT_ALLOW_ANY_HANDLER': 'planner.schema.auth.jwt_custom_allow_any',
    'JWT_PAYLOAD_HANDLER': 'planner.schema.auth.jwt_custom_payload',
}

# Custom user model
AUTH_USER_MODEL = 'planner.User'

# CORS / CSRF / Session Security
DEFAULT_CORS_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

CORS_ALLOWED_ORIGINS = _split_env_list(os.getenv('CORS_ALLOWED_ORIGINS'))
if not CORS_ALLOWED_ORIGINS and DEBUG:
    CORS_ALLOWED_ORIGINS = DEFAULT_CORS_ORIGINS

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = _split_env_list(os.getenv('CSRF_TRUSTED_ORIGINS'))
if not CSRF_TRUSTED_ORIGINS and CORS_ALLOWED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [origin for origin in CORS_ALLOWED_ORIGINS if origin.startswith(('http://', 'https://'))]

SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'None' if not DEBUG else 'Lax')

CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'None' if not DEBUG else 'Lax')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG


# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            '()': 'planner.logging.StructuredJsonFormatter',
        },
        'console_simple': {
            'format': '%(levelname)s:%(name)s:%(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured' if not DEBUG else 'console_simple',
        },
    },
    'loggers': {
        'planner.services.openroute': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'planner.services.hos': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'planner.services.trip_planner': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
        },
    },
}
