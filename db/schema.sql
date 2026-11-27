-- Учебная база «Компания»: отделы, сотрудники, клиенты, товары, заказы.

CREATE TABLE departments (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL,
    city  TEXT NOT NULL
);

CREATE TABLE employees (
    id             INTEGER PRIMARY KEY,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    department_id  INTEGER REFERENCES departments(id),
    manager_id     INTEGER REFERENCES employees(id),
    position       TEXT NOT NULL,
    salary         INTEGER NOT NULL,
    hire_date      TEXT NOT NULL,          -- формат YYYY-MM-DD
    email          TEXT
);

CREATE TABLE customers (
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    city           TEXT NOT NULL,
    registered_at  TEXT NOT NULL
);

CREATE TABLE products (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    category  TEXT NOT NULL,
    price     INTEGER NOT NULL
);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id),
    employee_id  INTEGER NOT NULL REFERENCES employees(id),
    order_date   TEXT NOT NULL,
    status       TEXT NOT NULL             -- new / paid / shipped / cancelled
);

CREATE TABLE order_items (
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    unit_price  INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id)
);

INSERT INTO departments VALUES
    (1, 'Продажи',     'Москва'),
    (2, 'Маркетинг',   'Москва'),
    (3, 'Разработка',  'Санкт-Петербург'),
    (4, 'Бухгалтерия', 'Москва'),
    (5, 'Логистика',   'Казань');

INSERT INTO employees VALUES
    (1,  'Анна',     'Смирнова', 3,    NULL, 'Технический директор',       250000, '2018-03-12', 'smirnova@company.ru'),
    (2,  'Игорь',    'Петров',   1,    NULL, 'Руководитель отдела продаж', 180000, '2019-01-15', 'petrov@company.ru'),
    (3,  'Мария',    'Иванова',  1,    2,    'Менеджер по продажам',        95000, '2020-06-01', 'ivanova@company.ru'),
    (4,  'Олег',     'Кузнецов', 1,    2,    'Менеджер по продажам',        87000, '2021-02-10', 'kuznetsov@company.ru'),
    (5,  'Елена',    'Соколова', 1,    2,    'Менеджер по продажам',       102000, '2019-11-20', 'sokolova@company.ru'),
    (6,  'Дмитрий',  'Попов',    3,    1,    'Разработчик',                160000, '2020-09-14', 'popov@company.ru'),
    (7,  'Светлана', 'Волкова',  3,    1,    'Разработчик',                175000, '2019-05-30', 'volkova@company.ru'),
    (8,  'Артём',    'Новиков',  3,    1,    'Тестировщик',                110000, '2022-04-04', 'novikov@company.ru'),
    (9,  'Ольга',    'Морозова', 2,    NULL, 'Маркетолог',                 120000, '2021-07-19', 'morozova@company.ru'),
    (10, 'Павел',    'Лебедев',  2,    9,    'Дизайнер',                    98000, '2023-01-09', NULL),
    (11, 'Наталья',  'Козлова',  4,    NULL, 'Главный бухгалтер',          140000, '2017-10-02', 'kozlova@company.ru'),
    (12, 'Сергей',   'Егоров',   4,    11,   'Бухгалтер',                   85000, '2022-08-22', 'egorov@company.ru'),
    (13, 'Татьяна',  'Павлова',  NULL, NULL, 'Стажёр',                      45000, '2024-02-01', NULL),
    (14, 'Алексей',  'Семёнов',  3,    1,    'Разработчик',                160000, '2023-03-15', 'semenov@company.ru');

INSERT INTO customers VALUES
    (1, 'ООО Ромашка', 'Москва',          '2023-01-10'),
    (2, 'ИП Сидоров',  'Казань',          '2023-02-14'),
    (3, 'АО Вектор',   'Санкт-Петербург', '2023-03-01'),
    (4, 'ООО Альфа',   'Москва',          '2023-04-18'),
    (5, 'ООО Бета',    'Новосибирск',     '2023-05-22'),
    (6, 'ИП Орлова',   'Москва',          '2023-07-07'),
    (7, 'ООО Гамма',   'Казань',          '2023-09-30'),
    (8, 'АО Север',    'Санкт-Петербург', '2024-01-15');

INSERT INTO products VALUES
    (1, 'Ноутбук Pro 14',          'Ноутбуки',  120000),
    (2, 'Ноутбук Air 13',          'Ноутбуки',   95000),
    (3, 'Монитор 27"',             'Мониторы',   32000),
    (4, 'Монитор 24"',             'Мониторы',   21000),
    (5, 'Клавиатура механическая', 'Периферия',   7500),
    (6, 'Мышь беспроводная',       'Периферия',   2500),
    (7, 'Веб-камера',              'Периферия',   5500),
    (8, 'Док-станция',             'Периферия',  15000),
    (9, 'Монитор 32" 4K',          'Мониторы',   54000);

INSERT INTO orders VALUES
    (1,  1, 3, '2024-01-15', 'shipped'),
    (2,  2, 4, '2024-01-20', 'shipped'),
    (3,  1, 3, '2024-02-03', 'shipped'),
    (4,  3, 5, '2024-02-11', 'paid'),
    (5,  4, 5, '2024-02-25', 'shipped'),
    (6,  5, 4, '2024-03-05', 'cancelled'),
    (7,  6, 3, '2024-03-18', 'shipped'),
    (8,  1, 5, '2024-04-02', 'paid'),
    (9,  7, 4, '2024-04-10', 'shipped'),
    (10, 3, 3, '2024-04-22', 'new'),
    (11, 4, 5, '2024-05-06', 'shipped'),
    (12, 2, 4, '2024-05-19', 'paid'),
    (13, 6, 5, '2024-06-01', 'new'),
    (14, 1, 3, '2024-06-12', 'shipped'),
    (15, 7, 4, '2024-06-25', 'cancelled');

INSERT INTO order_items VALUES
    (1,  1, 2, 120000), (1,  6, 2, 2500),
    (2,  4, 3, 21000),  (2,  5, 3, 7500),
    (3,  8, 5, 15000),
    (4,  2, 1, 95000),  (4,  3, 1, 32000),
    (5,  1, 1, 120000), (5,  3, 2, 32000), (5, 6, 1, 2500),
    (6,  2, 2, 95000),
    (7,  7, 4, 5500),   (7,  6, 4, 2500),
    (8,  1, 3, 120000),
    (9,  4, 2, 21000),
    (10, 5, 10, 7500),  (10, 6, 10, 2500),
    (11, 2, 2, 95000),  (11, 8, 2, 15000),
    (12, 3, 1, 32000),
    (13, 7, 1, 5500),
    (14, 1, 1, 120000), (14, 4, 1, 21000), (14, 5, 1, 7500),
    (15, 3, 3, 32000);
