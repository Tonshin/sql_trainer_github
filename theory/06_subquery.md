Подзапрос — это `SELECT` внутри другого запроса, в круглых скобках. Он позволяет сначала что-то вычислить, а затем использовать результат.

### Скалярный подзапрос

Возвращает ровно одно значение, и его можно использовать как обычное число или строку:

```sql
SELECT name, price
FROM products
WHERE price = (SELECT MAX(price) FROM products);
```

Подзапрос можно поставить и в `SELECT`, например чтобы показать отклонение от общего значения:

```sql
SELECT name, price,
       price - (SELECT MIN(price) FROM products) AS above_cheapest
FROM products;
```

### IN и NOT IN

Подзапрос, возвращающий один столбец, можно использовать как список:

```sql
SELECT first_name, last_name
FROM employees
WHERE department_id IN (SELECT id FROM departments WHERE city = 'Москва');
```

> Ловушка: если подзапрос внутри `NOT IN` вернёт хотя бы один `NULL`, весь результат будет пустым. Если в столбце возможны `NULL`, добавьте в подзапрос `WHERE столбец IS NOT NULL` или используйте `NOT EXISTS`.

### EXISTS и коррелированные подзапросы

`EXISTS (подзапрос)` истинно, если подзапрос вернул хотя бы одну строку. Обычно такой подзапрос ссылается на строку внешнего запроса — он **коррелированный** и выполняется для каждой строки заново:

```sql
SELECT c.name
FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.id AND o.status = 'cancelled'
);
```

Это клиенты, у которых есть хотя бы один отменённый заказ. `NOT EXISTS` даёт противоположное.

### Подзапрос во FROM и CTE

Результат подзапроса можно использовать как временную таблицу:

```sql
SELECT category, avg_price
FROM (
    SELECT category, AVG(price) AS avg_price
    FROM products
    GROUP BY category
) AS t
WHERE avg_price > 20000;
```

То же самое читается легче через **CTE** — именованный подзапрос в начале запроса, `WITH имя AS (...)`:

```sql
WITH category_prices AS (
    SELECT category, AVG(price) AS avg_price
    FROM products
    GROUP BY category
)
SELECT category, avg_price
FROM category_prices
WHERE avg_price > 20000;
```

В одном `WITH` можно объявить несколько CTE через запятую, и каждый следующий может использовать предыдущие.
