import os

SECRET_KEY = 'production'

MYSQL_HOST     = 'localhost'
MYSQL_USER     = 'root'
MYSQL_PASSWORD = 'admin'
MYSQL_DB       = 'library'

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'static', 'uploads', 'covers')

MAX_CONTENT_LENGTH = 16 * 1024 * 1024