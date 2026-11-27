Данные обычно разложены по нескольким таблицам. Например, заказ хранит только `customer_id`, а название клиента лежит в таблице `customers`. `JOIN` соединяет строки разных таблиц по условию.

### INNER JOIN

Возвращает только пары строк, для которых выполнилось условие `ON`. Слово `INNER` можно не писать:

```sql
SELECT o.id, o.order_date, c.name AS customer
FROM orders o
JOIN customers c ON c.id = o.customer_id;
```

`o` и `c` — псевдонимы таблиц. Они сокращают запись и помогают различать одинаковые имена столбцов (`o.id` и `c.id`).

### LEFT JOIN

Сохраняет **все** строки левой таблицы. Если пары не нашлось, столбцы правой таблицы заполняются `NULL`:

```sql
SELECT c.name, COUNT(o.id) AS orders_count
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.id, c.name;
```

Клиент без заказов тоже попал в результат, и у него 0 заказов. `COUNT(o.id)` не считает `NULL`, а `COUNT(*)` дал бы 1.

Полезный приём: после `LEFT JOIN` условие `WHERE <столбец правой таблицы> IS NULL` оставляет только строки, для которых пары **не нашлось**.

Ещё бывают `RIGHT JOIN` (то же, но сохраняется правая таблица) и `FULL JOIN` (сохраняются обе). На практике чаще всего используют `JOIN` и `LEFT JOIN`.

### Несколько таблиц подряд

Соединения выстраиваются в цепочку:

```sql
SELECT o.id AS order_id, c.name AS customer, p.name AS product, oi.quantity
FROM orders o
JOIN customers c    ON c.id = o.customer_id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p     ON p.id = oi.product_id
WHERE o.id = 5;
```

### Соединение таблицы с самой собой

Если нужно сопоставить строки одной таблицы между собой, таблицу используют дважды под разными псевдонимами. Так работают и связи внутри таблицы: например, `employees.manager_id` ссылается на `employees.id`.

Пример: пары коллег из одного отдела с одинаковой зарплатой. Условие `a.id < b.id` убирает пары сотрудника с самим собой и повторы вида (А, Б) и (Б, А):

```sql
SELECT a.first_name, a.last_name, b.first_name, b.last_name, a.salary
FROM employees a
JOIN employees b
  ON  b.department_id = a.department_id
  AND b.salary = a.salary
  AND a.id < b.id;
```

### Частые ошибки

- **Забыли условие соединения.** Каждая строка одной таблицы соединится с каждой строкой другой (декартово произведение), и результат резко раздуется.
- **Условие на правую таблицу в WHERE после LEFT JOIN.** Строки с `NULL` отсеются, и LEFT JOIN фактически превратится в обычный JOIN. Такие условия переносят в `ON`.
