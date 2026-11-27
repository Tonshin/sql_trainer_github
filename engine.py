"""Движок тренажёра: загрузка задач, выполнение SQL и проверка ответов.

Каждый запрос выполняется на свежей копии учебной базы в памяти,
поэтому пользователь не может её испортить. Дополнительно база
открывается только для чтения, а запросы ограничены по времени.
"""

from __future__ import annotations

import re
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
TASKS_PATH = BASE_DIR / "tasks.yaml"

TIMEOUT_SECONDS = 2.0      # максимальное время выполнения запроса
MAX_ROWS = 5000            # больше строк не читаем
FLOAT_PRECISION = 2        # до скольких знаков округлять дробные числа при сравнении

ALLOWED_FIRST_WORDS = {"SELECT", "WITH", "VALUES"}


# ---------------------------------------------------------------- данные

@dataclass
class Task:
    id: str
    title: str
    text: str
    solution: str
    hints: list[str] = field(default_factory=list)   # от лёгкого намёка к подробному
    template: str = ""                               # заготовка с пропусками ___
    ordered: bool = False
    topic: str = ""
    topic_id: str = ""

    @property
    def hint_levels(self) -> int:
        """Сколько всего уровней подсказки, включая заготовку."""
        return len(self.hints) + (1 if self.template else 0)


@dataclass
class Topic:
    name: str
    id: str = ""
    theory: str = ""          # текст теории в Markdown
    tasks: list[Task] = field(default_factory=list)


@dataclass
class QueryResult:
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    error: str | None = None
    elapsed_ms: float = 0.0

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class CheckResult:
    ok: bool
    message: str
    user: QueryResult
    expected: QueryResult


# ---------------------------------------------------------------- загрузка

_schema_cache: str | None = None


def load_schema_sql() -> str:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = SCHEMA_PATH.read_text(encoding="utf-8")
    return _schema_cache


def load_topics(path: Path = TASKS_PATH) -> list[Topic]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    topics: list[Topic] = []
    for n, t in enumerate(data["topics"], start=1):
        theory = ""
        if t.get("theory"):
            theory = (path.parent / t["theory"]).read_text(encoding="utf-8")
        topic = Topic(name=t["name"], id=t.get("id") or f"topic{n}", theory=theory)
        for raw in t["tasks"]:
            hints = raw.get("hints") or []
            if raw.get("hint"):              # старый формат: одна подсказка строкой
                hints = [raw["hint"], *hints]
            topic.tasks.append(Task(
                id=raw["id"],
                title=raw["title"],
                text=raw["text"],
                solution=raw["solution"].strip(),
                hints=[str(h) for h in hints],
                template=(raw.get("template") or "").strip(),
                ordered=bool(raw.get("ordered", False)),
                topic=topic.name,
                topic_id=topic.id,
            ))
        topics.append(topic)
    return topics


_SQL_BLOCK_RE = re.compile(r"```sql[ \t]*\n(.*?)```", re.S)


def split_theory(md: str) -> list[tuple[str, str]]:
    """Делит теорию на части: ("md", текст) и ("sql", запрос).

    Запускаемыми считаются только блоки ```sql; блоки без языка остаются текстом.
    """
    parts: list[tuple[str, str]] = []
    pos = 0
    for m in _SQL_BLOCK_RE.finditer(md):
        text = md[pos:m.start()].strip()
        if text:
            parts.append(("md", text))
        parts.append(("sql", m.group(1).strip()))
        pos = m.end()
    tail = md[pos:].strip()
    if tail:
        parts.append(("md", tail))
    return parts


# ---------------------------------------------------------------- база

def _authorizer(action, arg1, arg2, dbname, source):
    # Запрещаем подключение внешних файлов базы.
    if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def new_connection() -> sqlite3.Connection:
    """Свежая база в памяти с учебными данными, открытая только для чтения."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(load_schema_sql())
    conn.execute("PRAGMA query_only = ON")
    conn.set_authorizer(_authorizer)
    return conn


def schema_info() -> dict[str, list[tuple[str, str]]]:
    """Таблицы и их столбцы: {таблица: [(столбец, тип), ...]}."""
    conn = new_connection()
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")]
        return {
            t: [(c[1], c[2]) for c in conn.execute(f"PRAGMA table_info({t})")]
            for t in tables
        }
    finally:
        conn.close()


@dataclass
class Column:
    name: str
    type: str
    pk: bool = False
    not_null: bool = False
    references: tuple[str, str] | None = None   # (таблица, столбец)


def schema_details() -> dict[str, list[Column]]:
    """Таблицы со столбцами, первичными и внешними ключами (по REFERENCES в schema.sql)."""
    conn = new_connection()
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")]
        result: dict[str, list[Column]] = {}
        for t in tables:
            fks = {row[3]: (row[2], row[4] or "id")
                   for row in conn.execute(f"PRAGMA foreign_key_list({t})")}
            result[t] = [
                Column(name=c[1], type=c[2].lower(), pk=c[5] > 0, not_null=bool(c[3]),
                       references=fks.get(c[1]))
                for c in conn.execute(f"PRAGMA table_info({t})")
            ]
        return result
    finally:
        conn.close()


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def er_diagram_dot() -> str:
    """ER-диаграмма учебной базы в формате Graphviz DOT."""
    schema = schema_details()
    lines = [
        "digraph ER {",
        '  graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.45, ranksep=0.9, '
        'fontname="Helvetica"];',
        '  node [shape=plain, fontname="Helvetica", fontsize=11];',
        '  edge [color="#94a3b8", penwidth=1.3, dir=both, arrowtail=teetee, '
        'arrowhead=crow, arrowsize=0.8];',
    ]
    for table, cols in schema.items():
        rows = [
            '<table border="1" cellborder="0" cellspacing="0" cellpadding="5" '
            'bgcolor="#ffffff" color="#cbd5e1" style="rounded">',
            f'<tr><td colspan="3" bgcolor="#334155" align="center">'
            f'<font color="#ffffff" point-size="12"><b> {_esc(table)} </b></font></td></tr>',
        ]
        for c in cols:
            marks = []
            if c.pk:
                marks.append('<font color="#b45309"><b>PK</b></font>')
            if c.references:
                marks.append('<font color="#2563eb"><b>FK</b></font>')
            key = " ".join(marks)
            name = f"<b>{_esc(c.name)}</b>" if c.pk else _esc(c.name)
            rows.append(
                f'<tr><td port="{c.name}_in" align="left" width="24">{key}</td>'
                f'<td align="left"><font color="#0f172a">{name}</font></td>'
                f'<td port="{c.name}_out" align="left">'
                f'<font color="#64748b" point-size="10">{_esc(c.type)}</font></td></tr>')
        rows.append("</table>")
        lines.append(f'  {table} [label=<{"".join(rows)}>];')

    for table, cols in schema.items():
        for c in cols:
            if not c.references:
                continue
            ref_table, ref_col = c.references
            # Ребро от «одного» (первичный ключ) ко «многим» (внешний ключ).
            lines.append(f'  {ref_table}:{ref_col}_out:e -> {table}:{c.name}_in:w;')
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------- выполнение

_COMMENT_RE = re.compile(r"(--[^\n]*)|(/\*.*?\*/)", re.S)


def _clean_sql(sql: str) -> str:
    sql = sql.strip()
    while sql.endswith(";"):
        sql = sql[:-1].rstrip()
    return sql


def _first_word(sql: str) -> str:
    stripped = _COMMENT_RE.sub(" ", sql).strip()
    m = re.match(r"[A-Za-z]+", stripped)
    return m.group(0).upper() if m else ""


def run_query(sql: str, timeout: float = TIMEOUT_SECONDS) -> QueryResult:
    sql = _clean_sql(sql)
    if not _COMMENT_RE.sub("", sql).strip():
        return QueryResult(error="Запрос пустой.")

    word = _first_word(sql)
    if word not in ALLOWED_FIRST_WORDS:
        return QueryResult(error=(
            "В тренажёре можно выполнять только запросы на чтение "
            "(SELECT или WITH ... SELECT)."))

    conn = new_connection()
    deadline = time.monotonic() + timeout
    timed_out = False

    def progress() -> int:
        nonlocal timed_out
        if time.monotonic() > deadline:
            timed_out = True
            return 1
        return 0

    conn.set_progress_handler(progress, 10_000)
    start = time.perf_counter()
    try:
        cur = conn.execute(sql)
        if cur.description is None:
            return QueryResult(error="Запрос не вернул данных.")
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS + 1)
        if len(rows) > MAX_ROWS:
            return QueryResult(columns=columns, error=(
                f"Запрос вернул больше {MAX_ROWS} строк. "
                "Скорее всего, где-то не хватает условия соединения."))
        return QueryResult(columns=columns, rows=rows,
                           elapsed_ms=(time.perf_counter() - start) * 1000)
    except sqlite3.ProgrammingError as e:
        if "one statement" in str(e):
            return QueryResult(error="За один раз можно выполнить только один запрос.")
        return QueryResult(error=f"Ошибка: {e}")
    except sqlite3.Error as e:
        if timed_out:
            return QueryResult(error=(
                f"Запрос выполнялся дольше {timeout:g} с и был остановлен."))
        return QueryResult(error=f"Ошибка SQL: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------- проверка

def _norm_value(v: Any) -> Any:
    if isinstance(v, float):
        r = round(v, FLOAT_PRECISION)
        return 0.0 if r == 0 else r       # чтобы -0.0 совпадал с 0.0
    return v


def _norm_rows(rows: list[tuple]) -> list[tuple]:
    return [tuple(_norm_value(v) for v in row) for row in rows]


def compare(user: QueryResult, expected: QueryResult, ordered: bool) -> tuple[bool, str]:
    if len(user.columns) != len(expected.columns):
        return False, (f"Неверное количество столбцов: у вас {len(user.columns)}, "
                       f"нужно {len(expected.columns)}.")

    u_rows, e_rows = _norm_rows(user.rows), _norm_rows(expected.rows)

    if len(u_rows) != len(e_rows):
        return False, (f"Неверное количество строк: у вас {len(u_rows)}, "
                       f"нужно {len(e_rows)}.")

    if Counter(u_rows) != Counter(e_rows):
        return False, ("Количество строк совпадает, но значения отличаются. "
                       "Проверьте условия, столбцы и их порядок.")

    if ordered and u_rows != e_rows:
        return False, "Данные верные, но порядок строк не тот. Проверьте ORDER BY."

    return True, "Верно! 🎉"


def check(task: Task, user_sql: str) -> CheckResult:
    expected = run_query(task.solution)
    if not expected.ok:   # ошибка в самой задаче, а не у пользователя
        raise RuntimeError(f"Эталон задачи {task.id} не выполняется: {expected.error}")

    user = run_query(user_sql)
    if not user.ok:
        return CheckResult(False, user.error or "", user, expected)

    ok, msg = compare(user, expected, task.ordered)
    return CheckResult(ok, msg, user, expected)
