# АИС «Электронная библиотека»

Flask-приложение для ведения реестра книг с рецензиями и подборками (Вариант 2).

## Установка

```bash
pip install -r requirements.txt
mysql -u root -p library < schema.sql
python seed_books.py
python app.py
```

## Тестовые пользователи

| Логин | Пароль | Роль |
|-------|--------|------|
| admin | admin | Администратор |
| moderator | moderator | Модератор |
| user | user123 | Пользователь |
