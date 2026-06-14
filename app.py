import os
import hashlib
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, g, send_from_directory)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
import mysql.connector
import bleach
import markdown as md_lib

# ── Инициализация приложения ──────────────────────────────────────────────────

app = Flask(__name__)
app.config.from_pyfile('config.py')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

login_manager = LoginManager(app)


@login_manager.unauthorized_handler
def unauthorized():
    flash('Для выполнения данного действия необходимо пройти процедуру аутентификации',
          'warning')
    return redirect(url_for('login', next=request.full_path))


# ── База данных ───────────────────────────────────────────────────────────────

def get_db():
    """Возвращает соединение с БД, создавая его при первом обращении в рамках запроса."""
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=False,
            use_unicode=True
        )
    return g.db




@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ── Модель пользователя ───────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, id, login, last_name, first_name, middle_name,
                 role_id, role_name):
        self.id = id
        self.login = login
        self.last_name = last_name
        self.first_name = first_name
        self.middle_name = middle_name
        self.role_id = role_id
        self.role_name = role_name

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)

    @property
    def is_admin(self):
        return self.role_name == 'Администратор'

    @property
    def is_moderator(self):
        return self.role_name == 'Модератор'

    @property
    def is_regular_user(self):
        return self.role_name == 'Пользователь'


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(
        '''SELECT u.*, r.name AS role_name
           FROM users u JOIN roles r ON u.role_id = r.id
           WHERE u.id = %s''',
        (int(user_id),)
    )
    row = cur.fetchone()
    cur.close()
    if row:
        return User(row['id'], row['login'], row['last_name'],
                    row['first_name'], row['middle_name'],
                    row['role_id'], row['role_name'])
    return None


# ── Декораторы прав доступа ───────────────────────────────────────────────────

def admin_required(f):
    """Доступ только для Администратора."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Для выполнения данного действия необходимо пройти процедуру аутентификации',
                  'warning')
            return redirect(url_for('login', next=request.full_path))
        if not current_user.is_admin:
            flash('У вас недостаточно прав для выполнения данного действия', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def admin_or_moderator_required(f):
    """Доступ для Администратора или Модератора."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Для выполнения данного действия необходимо пройти процедуру аутентификации',
                  'warning')
            return redirect(url_for('login', next=request.full_path))
        if not (current_user.is_admin or current_user.is_moderator):
            flash('У вас недостаточно прав для выполнения данного действия', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def user_role_required(f):
    """Доступ только для роли «Пользователь»."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Для выполнения данного действия необходимо пройти процедуру аутентификации',
                  'warning')
            return redirect(url_for('login', next=request.full_path))
        if not current_user.is_regular_user:
            flash('У вас недостаточно прав для выполнения данного действия', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ── Вспомогательные функции ───────────────────────────────────────────────────

# Разрешённые HTML-теги при рендеринге Markdown
_MD_TAGS = [
    'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'del', 'em',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
    'li', 'ol', 'p', 'pre', 's', 'strong', 'table', 'tbody',
    'td', 'th', 'thead', 'tr', 'ul',
]
_MD_ATTRS = {
    'a':   ['href', 'title', 'rel'],
    'img': ['src', 'alt', 'title'],
}


def render_markdown(text: str) -> str:
    """Конвертирует Markdown в безопасный HTML."""
    html = md_lib.markdown(text or '', extensions=['extra', 'nl2br'])
    return bleach.clean(html, tags=_MD_TAGS, attributes=_MD_ATTRS)


def sanitize(text: str) -> str:
    """Экранирует все HTML-теги в тексте перед сохранением в БД."""
    return bleach.clean(text or '', tags=[], attributes={}, strip=False)


def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_all_genres(cur):
    cur.execute('SELECT id, name FROM genres ORDER BY name')
    return cur.fetchall()


# ── Авторизация ───────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        login_val = request.form.get('login', '').strip()
        password  = request.form.get('password', '')
        remember  = bool(request.form.get('remember'))

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute(
            '''SELECT u.*, r.name AS role_name
               FROM users u JOIN roles r ON u.role_id = r.id
               WHERE u.login = %s AND u.password_hash = %s''',
            (login_val, hash_password(password))
        )
        row = cur.fetchone()
        cur.close()

        if row:
            user = User(row['id'], row['login'], row['last_name'],
                        row['first_name'], row['middle_name'],
                        row['role_id'], row['role_name'])
            login_user(user, remember=remember)
            next_page = request.args.get('next', '')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))

        flash('Невозможно аутентифицироваться с указанными логином и паролем', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ── Главная страница ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    page     = max(1, request.args.get('page', 1, type=int))
    per_page = 10
    offset   = (page - 1) * per_page

    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute('SELECT COUNT(*) AS cnt FROM books')
    total       = cur.fetchone()['cnt']
    total_pages = max(1, (total + per_page - 1) // per_page)

    cur.execute('''
        SELECT b.id, b.title, b.year, b.author,
               COALESCE(AVG(r.rating), 0) AS avg_rating,
               COUNT(r.id)               AS review_count,
               c.filename                AS cover_filename
        FROM books b
        LEFT JOIN reviews r ON r.book_id = b.id
        LEFT JOIN covers  c ON c.book_id = b.id
        GROUP BY b.id, b.title, b.year, b.author, c.filename
        ORDER BY b.year DESC, b.id DESC
        LIMIT %s OFFSET %s
    ''', (per_page, offset))
    books = cur.fetchall()

    for book in books:
        cur.execute('''
            SELECT g.name FROM genres g
            JOIN book_genres bg ON bg.genre_id = g.id
            WHERE bg.book_id = %s ORDER BY g.name
        ''', (book['id'],))
        book['genres'] = [r['name'] for r in cur.fetchall()]

    cur.close()
    return render_template('index.html', books=books, page=page,
                           total_pages=total_pages)


# ── Просмотр книги ────────────────────────────────────────────────────────────

@app.route('/books/<int:book_id>')
def book_show(book_id):
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute('''
        SELECT b.*, c.filename AS cover_filename
        FROM books b LEFT JOIN covers c ON c.book_id = b.id
        WHERE b.id = %s
    ''', (book_id,))
    book = cur.fetchone()
    if not book:
        cur.close()
        return render_template('404.html'), 404

    cur.execute('''
        SELECT g.name FROM genres g
        JOIN book_genres bg ON bg.genre_id = g.id
        WHERE bg.book_id = %s ORDER BY g.name
    ''', (book_id,))
    book['genres'] = [r['name'] for r in cur.fetchall()]

    cur.execute('''
        SELECT r.*, u.last_name, u.first_name, u.middle_name
        FROM reviews r JOIN users u ON u.id = r.user_id
        WHERE r.book_id = %s ORDER BY r.created_at DESC
    ''', (book_id,))
    reviews = cur.fetchall()

    user_review     = None
    user_collections = []

    if current_user.is_authenticated:
        cur.execute(
            'SELECT * FROM reviews WHERE book_id = %s AND user_id = %s',
            (book_id, current_user.id)
        )
        user_review = cur.fetchone()

        if current_user.is_regular_user:
            cur.execute(
                'SELECT id, name FROM collections WHERE user_id = %s ORDER BY name',
                (current_user.id,)
            )
            user_collections = cur.fetchall()

    cur.close()

    book['description_html'] = render_markdown(book['description'])
    for rev in reviews:
        rev['text_html'] = render_markdown(rev['text'])

    return render_template('books/show.html', book=book, reviews=reviews,
                           user_review=user_review,
                           user_collections=user_collections)


# ── Добавление книги ──────────────────────────────────────────────────────────

@app.route('/books/create', methods=['GET', 'POST'])
@admin_required
def book_create():
    db  = get_db()
    cur = db.cursor(dictionary=True)
    genres = _get_all_genres(cur)

    if request.method == 'GET':
        cur.close()
        return render_template('books/create.html', genres=genres,
                               form_data={}, selected_genre_ids=[])

    # POST — обработка формы
    title       = request.form.get('title', '').strip()
    description = sanitize(request.form.get('description', ''))
    year        = request.form.get('year', '').strip()
    publisher   = request.form.get('publisher', '').strip()
    author      = request.form.get('author', '').strip()
    pages       = request.form.get('pages', '').strip()
    genre_ids   = request.form.getlist('genre_ids')
    cover_file  = request.files.get('cover')

    selected_genre_ids = genre_ids

    errors = []
    if not title:       errors.append('Укажите название книги')
    if not description: errors.append('Укажите описание книги')
    if not year:        errors.append('Укажите год издания')
    if not publisher:   errors.append('Укажите издательство')
    if not author:      errors.append('Укажите автора')
    if not pages:       errors.append('Укажите объём книги')
    if not genre_ids:   errors.append('Выберите хотя бы один жанр')
    if not cover_file or cover_file.filename == '':
        errors.append('Загрузите обложку книги')

    if errors:
        for e in errors:
            flash(e, 'danger')
        cur.close()
        return render_template('books/create.html', genres=genres,
                               form_data=request.form,
                               selected_genre_ids=selected_genre_ids)

    cover_data = cover_file.read()
    cover_hash = md5_hex(cover_data)
    cover_mime = cover_file.mimetype or 'application/octet-stream'

    need_save_file = False
    cover_filename = None

    try:
        # 1. Сохраняем книгу
        cur.execute('''
            INSERT INTO books (title, description, year, publisher, author, pages)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (title, description, int(year), publisher, author, int(pages)))
        book_id = cur.lastrowid

        # 2. Жанры
        for gid in genre_ids:
            cur.execute(
                'INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)',
                (book_id, int(gid))
            )

        # 3. Обложка — проверяем MD5-дубликат
        cur.execute(
            'SELECT id, filename FROM covers WHERE md5_hash = %s LIMIT 1',
            (cover_hash,)
        )
        existing = cur.fetchone()

        if existing:
            # Файл уже существует — переиспользуем имя файла
            cover_filename = existing['filename']
            cur.execute(
                'INSERT INTO covers (filename, mime_type, md5_hash, book_id) VALUES (%s,%s,%s,%s)',
                (cover_filename, cover_mime, cover_hash, book_id)
            )
        else:
            # Новый файл: вставляем запись, используем id как имя файла
            ext = os.path.splitext(cover_file.filename or '')[1].lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
                ext = '.jpg'

            cur.execute(
                'INSERT INTO covers (filename, mime_type, md5_hash, book_id) VALUES (%s,%s,%s,%s)',
                ('_placeholder_', cover_mime, cover_hash, book_id)
            )
            cover_id       = cur.lastrowid
            cover_filename = f'{cover_id}{ext}'
            cur.execute(
                'UPDATE covers SET filename = %s WHERE id = %s',
                (cover_filename, cover_id)
            )
            need_save_file = True

        db.commit()

        # 4. Сохраняем файл на диск ПОСЛЕ коммита
        if need_save_file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], cover_filename)
            with open(file_path, 'wb') as fp:
                fp.write(cover_data)

        flash('Книга успешно добавлена', 'success')
        cur.close()
        return redirect(url_for('book_show', book_id=book_id))

    except Exception as exc:
        db.rollback()
        app.logger.exception('Ошибка при создании книги: %s', exc)
        flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.',
              'danger')
        cur.close()
        return render_template('books/create.html', genres=genres,
                               form_data=request.form,
                               selected_genre_ids=selected_genre_ids)


# ── Редактирование книги ──────────────────────────────────────────────────────

@app.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@admin_or_moderator_required
def book_edit(book_id):
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cur.fetchone()
    if not book:
        cur.close()
        return render_template('404.html'), 404

    genres = _get_all_genres(cur)

    cur.execute(
        'SELECT genre_id FROM book_genres WHERE book_id = %s', (book_id,)
    )
    db_genre_ids = [str(r['genre_id']) for r in cur.fetchall()]

    if request.method == 'GET':
        cur.close()
        return render_template('books/edit.html', book=book, genres=genres,
                               form_data=book,
                               selected_genre_ids=db_genre_ids)

    # POST
    title       = request.form.get('title', '').strip()
    description = sanitize(request.form.get('description', ''))
    year        = request.form.get('year', '').strip()
    publisher   = request.form.get('publisher', '').strip()
    author      = request.form.get('author', '').strip()
    pages       = request.form.get('pages', '').strip()
    genre_ids   = request.form.getlist('genre_ids')

    selected_genre_ids = genre_ids

    errors = []
    if not title:       errors.append('Укажите название книги')
    if not description: errors.append('Укажите описание книги')
    if not year:        errors.append('Укажите год издания')
    if not publisher:   errors.append('Укажите издательство')
    if not author:      errors.append('Укажите автора')
    if not pages:       errors.append('Укажите объём книги')
    if not genre_ids:   errors.append('Выберите хотя бы один жанр')

    if errors:
        for e in errors:
            flash(e, 'danger')
        cur.close()
        return render_template('books/edit.html', book=book, genres=genres,
                               form_data=request.form,
                               selected_genre_ids=selected_genre_ids)

    try:
        cur.execute('''
            UPDATE books
            SET title=%s, description=%s, year=%s, publisher=%s, author=%s, pages=%s
            WHERE id=%s
        ''', (title, description, int(year), publisher, author, int(pages), book_id))

        cur.execute('DELETE FROM book_genres WHERE book_id = %s', (book_id,))
        for gid in genre_ids:
            cur.execute(
                'INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)',
                (book_id, int(gid))
            )

        db.commit()
        flash('Книга успешно обновлена', 'success')
        cur.close()
        return redirect(url_for('book_show', book_id=book_id))

    except Exception as exc:
        db.rollback()
        app.logger.exception('Ошибка при редактировании книги: %s', exc)
        flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.',
              'danger')
        cur.close()
        return render_template('books/edit.html', book=book, genres=genres,
                               form_data=request.form,
                               selected_genre_ids=selected_genre_ids)


# ── Удаление книги ────────────────────────────────────────────────────────────

@app.route('/books/<int:book_id>/delete', methods=['POST'])
@admin_required
def book_delete(book_id):
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute('SELECT id FROM books WHERE id = %s', (book_id,))
    if not cur.fetchone():
        cur.close()
        flash('Книга не найдена', 'danger')
        return redirect(url_for('index'))

    # Запоминаем имена файлов обложек ДО удаления (ON DELETE CASCADE удалит записи)
    cur.execute('SELECT DISTINCT filename FROM covers WHERE book_id = %s', (book_id,))
    cover_filenames = [r['filename'] for r in cur.fetchall()]

    try:
        cur.execute('DELETE FROM books WHERE id = %s', (book_id,))
        db.commit()

        # Удаляем файлы, на которые больше нет ссылок в таблице covers
        for fname in cover_filenames:
            cur.execute(
                'SELECT COUNT(*) AS cnt FROM covers WHERE filename = %s', (fname,)
            )
            if cur.fetchone()['cnt'] == 0:
                fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                try:
                    os.remove(fpath)
                except FileNotFoundError:
                    pass

        flash('Книга успешно удалена', 'success')

    except Exception as exc:
        db.rollback()
        app.logger.exception('Ошибка при удалении книги: %s', exc)
        flash('При удалении книги возникла ошибка', 'danger')
    finally:
        cur.close()

    return redirect(url_for('index'))


# ── Рецензии ──────────────────────────────────────────────────────────────────

@app.route('/books/<int:book_id>/reviews/create', methods=['GET', 'POST'])
@login_required
def review_create(book_id):
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute('SELECT id, title FROM books WHERE id = %s', (book_id,))
    book = cur.fetchone()
    if not book:
        cur.close()
        return render_template('404.html'), 404

    # Проверяем, не писал ли пользователь уже рецензию
    cur.execute(
        'SELECT id FROM reviews WHERE book_id = %s AND user_id = %s',
        (book_id, current_user.id)
    )
    if cur.fetchone():
        cur.close()
        flash('Вы уже оставляли рецензию на эту книгу', 'info')
        return redirect(url_for('book_show', book_id=book_id))

    cur.close()

    if request.method == 'GET':
        return render_template('reviews/create.html', book=book, form_data={})

    # POST
    rating_str = request.form.get('rating', '').strip()
    text       = sanitize(request.form.get('text', ''))

    if not rating_str or not text:
        flash('Пожалуйста, заполните все поля', 'danger')
        return render_template('reviews/create.html', book=book,
                               form_data=request.form)

    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            'INSERT INTO reviews (book_id, user_id, rating, text) VALUES (%s,%s,%s,%s)',
            (book_id, current_user.id, int(rating_str), text)
        )
        db.commit()
        flash('Рецензия успешно добавлена', 'success')
        cur.close()
        return redirect(url_for('book_show', book_id=book_id))

    except Exception as exc:
        db.rollback()
        app.logger.exception('Ошибка при создании рецензии: %s', exc)
        flash('При сохранении рецензии возникла ошибка', 'danger')
        cur.close()
        return render_template('reviews/create.html', book=book,
                               form_data=request.form)


# ── Подборки (Вариант 2) ──────────────────────────────────────────────────────

@app.route('/collections')
@user_role_required
def collections_index():
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute('''
        SELECT c.id, c.name, COUNT(cb.book_id) AS book_count
        FROM collections c
        LEFT JOIN collection_books cb ON cb.collection_id = c.id
        WHERE c.user_id = %s
        GROUP BY c.id, c.name
        ORDER BY c.name
    ''', (current_user.id,))
    collections = cur.fetchall()
    cur.close()
    return render_template('collections/index.html', collections=collections)


@app.route('/collections/<int:col_id>')
@user_role_required
def collections_show(col_id):
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        'SELECT id, name FROM collections WHERE id = %s AND user_id = %s',
        (col_id, current_user.id)
    )
    collection = cur.fetchone()
    if not collection:
        cur.close()
        flash('Подборка не найдена', 'danger')
        return redirect(url_for('collections_index'))

    cur.execute('''
        SELECT b.id, b.title, b.author, b.year,
               COALESCE(AVG(r.rating), 0) AS avg_rating,
               COUNT(r.id)               AS review_count,
               cov.filename              AS cover_filename
        FROM books b
        JOIN collection_books cb ON cb.book_id = b.id
        LEFT JOIN reviews r      ON r.book_id  = b.id
        LEFT JOIN covers  cov    ON cov.book_id = b.id
        WHERE cb.collection_id = %s
        GROUP BY b.id, b.title, b.author, b.year, cov.filename
        ORDER BY b.title
    ''', (col_id,))
    books = cur.fetchall()

    for book in books:
        cur.execute('''
            SELECT g.name FROM genres g
            JOIN book_genres bg ON bg.genre_id = g.id
            WHERE bg.book_id = %s ORDER BY g.name
        ''', (book['id'],))
        book['genres'] = [r['name'] for r in cur.fetchall()]

    cur.close()
    return render_template('collections/show.html',
                           collection=collection, books=books)


@app.route('/collections/create', methods=['POST'])
@user_role_required
def collections_create():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Название подборки не может быть пустым', 'danger')
        return redirect(url_for('collections_index'))

    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            'INSERT INTO collections (name, user_id) VALUES (%s, %s)',
            (name, current_user.id)
        )
        db.commit()
        flash(f'Подборка «{name}» успешно создана', 'success')
    except Exception as exc:
        db.rollback()
        app.logger.exception('Ошибка при создании подборки: %s', exc)
        flash('При создании подборки возникла ошибка', 'danger')
    finally:
        cur.close()
    return redirect(url_for('collections_index'))


@app.route('/books/<int:book_id>/add-to-collection', methods=['POST'])
@user_role_required
def book_add_to_collection(book_id):
    col_id = request.form.get('collection_id', type=int)
    if not col_id:
        flash('Выберите подборку', 'danger')
        return redirect(url_for('book_show', book_id=book_id))

    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        'SELECT id, name FROM collections WHERE id = %s AND user_id = %s',
        (col_id, current_user.id)
    )
    col = cur.fetchone()
    if not col:
        cur.close()
        flash('Подборка не найдена', 'danger')
        return redirect(url_for('book_show', book_id=book_id))

    cur.execute(
        'SELECT 1 FROM collection_books WHERE collection_id=%s AND book_id=%s',
        (col_id, book_id)
    )
    if cur.fetchone():
        cur.close()
        flash('Эта книга уже есть в выбранной подборке', 'info')
        return redirect(url_for('book_show', book_id=book_id))

    try:
        cur.execute(
            'INSERT INTO collection_books (collection_id, book_id) VALUES (%s, %s)',
            (col_id, book_id)
        )
        db.commit()
        flash(f'Книга успешно добавлена в подборку «{col["name"]}»', 'success')
    except Exception as exc:
        db.rollback()
        app.logger.exception('Ошибка при добавлении в подборку: %s', exc)
        flash('При добавлении книги в подборку возникла ошибка', 'danger')
    finally:
        cur.close()
    return redirect(url_for('book_show', book_id=book_id))


# ── Раздача обложек ───────────────────────────────────────────────────────────

@app.route('/covers/<path:filename>')
def serve_cover(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ── Запуск ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)
