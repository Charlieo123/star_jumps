CREATE DATABASE IF NOT EXISTS star_jump_lottery;

USE star_jump_lottery;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(50) UNIQUE NOT NULL,
    star_jump_count INTEGER DEFAULT 0
);

