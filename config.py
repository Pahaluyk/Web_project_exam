import os

SECRET_KEY = os.environ.get('SECRET_KEY', 'production')

MYSQL_HOST     = os.environ.get('MYSQL_HOST',     'localhost')
MYSQL_USER     = os.environ.get('MYSQL_USER',     'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'admin')
MYSQL_DB       = os.environ.get('MYSQL_DB',       'library')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'static', 'uploads', 'covers')

MAX_CONTENT_LENGTH = 16 * 1024 * 1024