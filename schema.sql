CREATE DATABASE IF NOT EXISTS library
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS collection_books;
DROP TABLE IF EXISTS collections;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS book_genres;
DROP TABLE IF EXISTS covers;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE roles (
    id          INT         NOT NULL AUTO_INCREMENT,
    name        VARCHAR(50) NOT NULL,
    description TEXT        NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE users (
    id            INT          NOT NULL AUTO_INCREMENT,
    login         VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    last_name     VARCHAR(100) NOT NULL,
    first_name    VARCHAR(100) NOT NULL,
    middle_name   VARCHAR(100),
    role_id       INT          NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (role_id) REFERENCES roles (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE genres (
    id   INT         NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE books (
    id          INT          NOT NULL AUTO_INCREMENT,
    title       VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL,
    year        YEAR         NOT NULL,
    publisher   VARCHAR(255) NOT NULL,
    author      VARCHAR(255) NOT NULL,
    pages       INT          NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE covers (
    id        INT          NOT NULL AUTO_INCREMENT,
    filename  VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    md5_hash  VARCHAR(32)  NOT NULL,
    book_id   INT          NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE book_genres (
    book_id  INT NOT NULL,
    genre_id INT NOT NULL,
    PRIMARY KEY (book_id, genre_id),
    FOREIGN KEY (book_id)  REFERENCES books  (id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE reviews (
    id         INT       NOT NULL AUTO_INCREMENT,
    book_id    INT       NOT NULL,
    user_id    INT       NOT NULL,
    rating     INT       NOT NULL,
    text       TEXT      NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE collections (
    id      INT          NOT NULL AUTO_INCREMENT,
    name    VARCHAR(255) NOT NULL,
    user_id INT          NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE collection_books (
    collection_id INT NOT NULL,
    book_id       INT NOT NULL,
    PRIMARY KEY (collection_id, book_id),
    FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE,
    FOREIGN KEY (book_id)       REFERENCES books       (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



INSERT INTO roles (name, description) VALUES
('Администратор', 'Суперпользователь, имеет полный доступ к системе, в том числе к созданию и удалению книг'),
('Модератор',     'Может редактировать данные книг и производить модерацию рецензий'),
('Пользователь',  'Может оставлять рецензии');

-- Пользователи (пароли: admin / moderator / user123)

INSERT INTO users (login, password_hash, last_name, first_name, middle_name, role_id) VALUES
('admin',     '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Иванов',   'Иван',   'Иванович',  1),
('moderator', 'cfde2ca5188afb7bdd0691c7bef887baba78b709aadde8e8c535329d5751e6fe', 'Петров',   'Пётр',   NULL,        2),
('user',      'e606e38b0d8c19b24cf0ee3808183162ea7cd63ff7912dbb22b5e803286b4446', 'Сидоров',  'Сидор',  'Сидорович', 3);

INSERT INTO genres (name) VALUES
('Фантастика'),
('Детектив'),
('Роман');
