import os

SECRET_KEY = os.environ.get('SECRET_KEY', 'production')

MYSQL_HOST     = os.environ.get('MYSQLHOST',      'localhost')
MYSQL_USER     = os.environ.get('MYSQLUSER',      'root')
MYSQL_PASSWORD = os.environ.get('MYSQLPASSWORD',  'admin')
MYSQL_DB       = os.environ.get('MYSQL_DATABASE', 'library')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'static', 'uploads', 'covers')

MAX_CONTENT_LENGTH = 16 * 1024 * 1024
