Оконная функция считает значение по группе строк («окну»), но, в отличие от `GROUP BY`, **не схлопывает** строки: каждая строка остаётся в результате и получает своё значение.

```
функция() OVER (
    PARTITION BY <на какие группы делить>   -- необязательно
    ORDER BY <в каком порядке внутри группы>  -- необязательно
)
```

### Агрегаты как оконные функции

`SUM`, `AVG`, `COUNT`, `MIN`, `MAX` работают и как оконные. Например, рядом с каждым товаром можно показать максимальную цену в его категории:

```sql
SELECT name, category, price,
       MAX(price) OVER (PARTITION BY category) AS max_in_category
FROM products;
```

С `GROUP BY` осталось бы по одной строке на категорию, а здесь все товары на месте.

### Нумерация и ранжирование

| Функция | Одинаковые значения | Пример нумерации |
|---|---|---|
| `ROW_NUMBER()` | получают разные номера | 1, 2, 3, 4 |
| `RANK()` | одинаковый номер, следующий пропускается | 1, 2, 2, 4 |
| `DENSE_RANK()` | одинаковый номер без пропусков | 1, 2, 2, 3 |

В отделе разработки двое сотрудников с одинаковой зарплатой. Посмотрите, как по-разному их пронумеруют три функции:

```sql
SELECT first_name, salary,
       ROW_NUMBER() OVER (ORDER BY salary DESC) AS row_num,
       RANK()       OVER (ORDER BY salary DESC) AS rnk,
       DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rnk
FROM employees
WHERE department_id = 3;
```

### Нарастающий итог

Если в `OVER` есть `ORDER BY`, агрегат считается «с начала окна до текущей строки». Так получается накопительная сумма:

```sql
SELECT id, order_date,
       COUNT(*) OVER (ORDER BY order_date) AS orders_so_far
FROM orders;
```

### Предыдущая и следующая строка: LAG и LEAD

`LAG(столбец)` берёт значение из предыдущей строки окна, `LEAD(столбец)` — из следующей:

```sql
SELECT id, order_date,
       LAG(order_date) OVER (ORDER BY order_date) AS previous_order
FROM orders
WHERE customer_id = 1;
```

### Фильтр по оконной функции

Оконные функции вычисляются после `WHERE`, поэтому фильтровать по ним напрямую нельзя. Запрос оборачивают в CTE или подзапрос. Классическая задача — «самый дорогой товар в каждой категории»:

```sql
WITH ranked AS (
    SELECT name, category, price,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY price DESC) AS rn
    FROM products
)
SELECT category, name, price
FROM ranked
WHERE rn = 1;
```
