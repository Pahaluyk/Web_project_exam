# АИС «Электронная библиотека»

Flask-приложение для ведения реестра книг с рецензиями и подборками (Вариант 2).

## Установка

```bash
pip install -r requirements.txt
mysql -u root -p
CREATE DATABASE library CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library;
SOURCE schema.sql;
EXIT;
python seed_books.py
python app.py
```

## Тестовые пользователи

| Логин | Пароль | Роль |
|-------|--------|------|
| admin | admin | Администратор |
| moderator | moderator | Модератор |
| user | user123 | Пользователь |
