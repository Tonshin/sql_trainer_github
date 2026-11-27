import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engine  # noqa: E402

TOPICS = engine.load_topics()
ALL_TASKS = [t for topic in TOPICS for t in topic.tasks]


def test_task_ids_unique():
    ids = [t.id for t in ALL_TASKS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("task", ALL_TASKS, ids=lambda t: t.id)
def test_solution_runs_and_passes(task):
    res = engine.run_query(task.solution)
    assert res.ok, res.error
    assert res.rows, "эталон вернул пустой результат"
    assert engine.check(task, task.solution).ok


@pytest.mark.parametrize("task", [t for t in ALL_TASKS if t.ordered], ids=lambda t: t.id)
def test_ordered_solution_has_no_ties(task):
    # В задачах на порядок результат должен быть однозначным.
    res = engine.run_query(task.solution)
    assert len(set(res.rows)) == len(res.rows)


def _task(tid):
    return next(t for t in ALL_TASKS if t.id == tid)


def test_wrong_order_detected():
    r = engine.check(_task("order_top3_products"),
                     "SELECT name, price FROM products ORDER BY price DESC LIMIT 3")
    assert r.ok
    r = engine.check(_task("order_by_hire_date"),
                     "SELECT first_name, last_name, hire_date FROM employees ORDER BY hire_date")
    assert not r.ok and "порядок" in r.message


def test_unordered_task_ignores_order():
    r = engine.check(_task("where_high_salary"),
                     "SELECT first_name, last_name, salary FROM employees "
                     "WHERE salary > 100000 ORDER BY salary")
    assert r.ok


def test_column_count_mismatch():
    r = engine.check(_task("select_employee_names"), "SELECT first_name FROM employees")
    assert not r.ok and "столбцов" in r.message


def test_row_count_mismatch():
    r = engine.check(_task("where_high_salary"),
                     "SELECT first_name, last_name, salary FROM employees WHERE salary >= 100000 AND 0")
    assert not r.ok and "строк" in r.message


def test_float_tolerance():
    r = engine.check(_task("agg_salary_stats"),
                     "SELECT AVG(salary), MIN(salary), MAX(salary) FROM employees")
    assert r.ok


def test_writes_blocked():
    assert not engine.run_query("DELETE FROM employees").ok
    assert not engine.run_query("DROP TABLE employees").ok
    res = engine.run_query("WITH x AS (SELECT 1) DELETE FROM employees")
    assert not res.ok


def test_attach_blocked():
    assert not engine.run_query("ATTACH DATABASE 'x.db' AS x").ok


def test_multiple_statements():
    res = engine.run_query("SELECT 1; SELECT 2;")
    assert not res.ok and "один запрос" in res.error


def test_empty_and_comments():
    assert not engine.run_query("   ").ok
    assert not engine.run_query("-- просто комментарий").ok
    assert engine.run_query("-- комментарий\nSELECT 1;").ok


def test_timeout():
    res = engine.run_query(
        "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) "
        "SELECT count(*) FROM r", timeout=0.3)
    assert not res.ok and "остановлен" in res.error


def test_too_many_rows():
    res = engine.run_query(
        "SELECT * FROM order_items a, order_items b, order_items c")
    assert not res.ok and "строк" in res.error


def test_db_is_fresh_each_time():
    engine.run_query("DELETE FROM employees")
    assert engine.run_query("SELECT COUNT(*) FROM employees").rows == [(14,)]


def test_schema_info():
    info = engine.schema_info()
    assert set(info) == {"departments", "employees", "customers",
                         "products", "orders", "order_items"}
