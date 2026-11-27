"""SQL-тренажёр на Streamlit. Запуск: streamlit run app.py"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import engine

SANDBOX = "__sandbox__"
THEORY = "theory:"            # префикс страницы теории: "theory:<id темы>"
SOLUTION_AFTER_ATTEMPTS = 2   # после скольких неудачных попыток можно открыть решение

st.set_page_config(page_title="SQL-тренажёр", page_icon="🗄️", layout="wide")


# ---------------------------------------------------------------- данные

@st.cache_resource
def get_topics() -> list[engine.Topic]:
    return engine.load_topics()


@st.cache_resource
def get_schema() -> dict[str, list[tuple[str, str]]]:
    return engine.schema_info()


TOPICS = get_topics()
TASKS = [t for topic in TOPICS for t in topic.tasks]
TASK_BY_ID = {t.id: t for t in TASKS}
TOPIC_BY_ID = {t.id: t for t in TOPICS}
START_PAGE = THEORY + TOPICS[0].id if TOPICS[0].theory else TASKS[0].id


# ---------------------------------------------------------------- состояние

ss = st.session_state
ss.setdefault("current", START_PAGE)
if ss.current not in TASK_BY_ID and ss.current != SANDBOX and \
        ss.current.removeprefix(THEORY) not in TOPIC_BY_ID:
    ss.current = START_PAGE          # например, задачу удалили из tasks.yaml
ss.setdefault("solved", set())
ss.setdefault("attempts", {})        # id -> число неудачных проверок
ss.setdefault("results", {})         # id -> dict с последним результатом
ss.setdefault("hint_level", {})      # id -> сколько уровней подсказки открыто
ss.setdefault("solved_hints", {})    # id -> сколько подсказок было открыто к моменту решения
ss.setdefault("show_solution", set())

STATE_KEYS = ("solved", "attempts", "results", "hint_level", "solved_hints", "show_solution")


def select(task_id: str) -> None:
    ss.current = task_id


def open_next_hint(task_id: str) -> None:
    ss.hint_level[task_id] = ss.hint_level.get(task_id, 0) + 1


def insert_template(task_id: str) -> None:
    ss[f"sql_{task_id}"] = TASK_BY_ID[task_id].template + "\n"


def task_mark(task_id: str) -> str:
    if task_id not in ss.solved:
        return "▫️"
    return "✅" if ss.solved_hints.get(task_id, 0) == 0 else "☑️"


def next_task_id(current: str) -> str | None:
    ids = [t.id for t in TASKS]
    i = ids.index(current)
    rest = ids[i + 1:] + ids[:i]
    for tid in rest:                 # сначала ближайшая нерешённая
        if tid not in ss.solved:
            return tid
    return ids[i + 1] if i + 1 < len(ids) else None


def reset_progress() -> None:
    for key in STATE_KEYS:
        del ss[key]
    for key in list(ss.keys()):
        if str(key).startswith("sql_"):
            del ss[key]
    ss.current = START_PAGE


# ---------------------------------------------------------------- вывод

def to_df(res: engine.QueryResult) -> pd.DataFrame:
    # Одинаковые имена столбцов (например, в self join) переименовываем.
    seen: dict[str, int] = {}
    cols = []
    for c in res.columns:
        seen[c] = seen.get(c, 0) + 1
        cols.append(c if seen[c] == 1 else f"{c} ({seen[c]})")
    return pd.DataFrame.from_records(res.rows, columns=cols)


def show_table(res: engine.QueryResult) -> None:
    if not res.rows:
        st.info("Запрос выполнен, но вернул 0 строк.")
        if res.columns:
            st.dataframe(to_df(res), hide_index=True, use_container_width=True)
        return
    st.dataframe(to_df(res), hide_index=True, use_container_width=True)
    st.caption(f"Строк: {len(res.rows)} · {res.elapsed_ms:.1f} мс")


def schema_panel() -> None:
    schema = get_schema()
    with st.expander("📋 Схема базы", expanded=False):
        cols = st.columns(3)
        for i, (table, columns) in enumerate(schema.items()):
            with cols[i % 3]:
                st.markdown(f"**{table}**")
                st.markdown("\n".join(f"- `{name}` · {typ.lower()}" for name, typ in columns))
        st.divider()
        table = st.selectbox("Посмотреть данные таблицы", list(schema), key="preview_table")
        show_table(engine.run_query(f"SELECT * FROM {table} LIMIT 50"))


# ---------------------------------------------------------------- боковая панель

with st.sidebar:
    st.title("🗄️ SQL-тренажёр")
    solved = len(ss.solved & TASK_BY_ID.keys())
    st.progress(solved / len(TASKS), text=f"Решено {solved} из {len(TASKS)}")

    st.button("🧪 Песочница", use_container_width=True, on_click=select, args=(SANDBOX,),
              type="primary" if ss.current == SANDBOX else "secondary")

    for topic in TOPICS:
        done = sum(t.id in ss.solved for t in topic.tasks)
        theory_page = THEORY + topic.id
        has_current = (ss.current == theory_page
                       or any(t.id == ss.current for t in topic.tasks))
        with st.expander(f"{topic.name}  ·  {done}/{len(topic.tasks)}", expanded=has_current):
            if topic.theory:
                st.button("📖 Теория", key=f"nav_{theory_page}", use_container_width=True,
                          on_click=select, args=(theory_page,),
                          type="primary" if ss.current == theory_page else "secondary")
            for t in topic.tasks:
                st.button(f"{task_mark(t.id)} {t.title}", key=f"nav_{t.id}", use_container_width=True,
                          on_click=select, args=(t.id,),
                          type="primary" if t.id == ss.current else "secondary")

    st.caption("✅ решено без подсказок · ☑️ решено с подсказками")
    st.divider()
    st.button("Сбросить прогресс", on_click=reset_progress, use_container_width=True)
    st.caption("Прогресс хранится только в текущей сессии браузера.")


# ---------------------------------------------------------------- песочница

if ss.current == SANDBOX:
    st.header("🧪 Песочница")
    st.write("Здесь можно выполнять любые запросы к учебной базе, без проверки.")
    schema_panel()
    sql = st.text_area("SQL", key="sql_sandbox", height=200,
                       placeholder="SELECT * FROM employees;")
    if st.button("▶ Выполнить", type="primary"):
        ss.results[SANDBOX] = {"kind": "run", "res": engine.run_query(sql)}
    last = ss.results.get(SANDBOX)
    if last:
        res = last["res"]
        if res.ok:
            show_table(res)
        else:
            st.error(res.error)
    st.stop()


# ---------------------------------------------------------------- теория

if ss.current.startswith(THEORY):
    topic = TOPIC_BY_ID[ss.current.removeprefix(THEORY)]
    st.caption("📖 Теория")
    st.header(topic.name)

    for i, (kind, content) in enumerate(engine.split_theory(topic.theory)):
        if kind == "md":
            st.markdown(content)
            continue
        st.code(content, language="sql")
        key = f"theory_{topic.id}_{i}"
        if st.button("▶ Выполнить пример", key=f"run_{key}"):
            ss.results[key] = engine.run_query(content)
        res = ss.results.get(key)
        if res is not None:
            if res.ok:
                show_table(res)
            else:
                st.error(res.error)

    st.divider()
    st.caption("Примеры можно менять и запускать в 🧪 Песочнице.")
    first = next((t for t in topic.tasks if t.id not in ss.solved), topic.tasks[0])
    st.button(f"К задачам темы: {first.title} →", type="primary",
              on_click=select, args=(first.id,))
    st.stop()


# ---------------------------------------------------------------- задача

task = TASK_BY_ID[ss.current]
attempts = ss.attempts.get(task.id, 0)
is_solved = task.id in ss.solved
hint_level = ss.hint_level.get(task.id, 0)
hints_left = task.hint_levels - hint_level

top_left, top_right = st.columns([4, 1])
top_left.caption(task.topic)
if TOPIC_BY_ID[task.topic_id].theory:
    top_right.button("📖 Теория по теме", key="to_theory", use_container_width=True,
                     on_click=select, args=(THEORY + task.topic_id,))
st.header((task_mark(task.id) + " " if is_solved else "") + task.title)
st.markdown(task.text)
if task.ordered:
    st.caption("↕️ В этой задаче важен порядок строк.")

schema_panel()

sql = st.text_area("Ваш запрос", key=f"sql_{task.id}", height=180,
                   placeholder="SELECT ...")

c1, c2, c3, c4 = st.columns(4)
run_clicked = c1.button("▶ Выполнить", use_container_width=True)
check_clicked = c2.button("✔ Проверить", type="primary", use_container_width=True)
c3.button(f"💡 Подсказка {min(hint_level + 1, task.hint_levels)}/{task.hint_levels}",
          use_container_width=True, disabled=hints_left <= 0,
          on_click=open_next_hint, args=(task.id,),
          help="Все подсказки открыты" if hints_left <= 0 else
          "Каждая следующая подсказка подробнее предыдущей")
can_show_solution = (is_solved or attempts >= SOLUTION_AFTER_ATTEMPTS
                     or hints_left <= 0)
if c4.button("👀 Решение", use_container_width=True, disabled=not can_show_solution,
             help=None if can_show_solution else
             f"Станет доступно после {SOLUTION_AFTER_ATTEMPTS} неудачных проверок "
             "или когда откроете все подсказки"):
    ss.show_solution.symmetric_difference_update({task.id})

if run_clicked:
    ss.results[task.id] = {"kind": "run", "res": engine.run_query(sql)}

if check_clicked:
    result = engine.check(task, sql)
    ss.results[task.id] = {"kind": "check", "check": result}
    if result.ok:
        if task.id not in ss.solved:     # учитываем подсказки на момент первого решения
            ss.solved_hints[task.id] = hint_level
        ss.solved.add(task.id)
    else:
        ss.attempts[task.id] = attempts + 1
    st.rerun()   # чтобы сразу обновились отметки в боковой панели

HINT_NAMES = ["Идея", "Структура"]
for i, hint in enumerate(task.hints[:hint_level]):
    name = HINT_NAMES[i] if i < len(HINT_NAMES) else f"Подсказка {i + 1}"
    st.info(f"💡 **{name}.** {hint}")
if task.template and hint_level > len(task.hints):
    st.markdown("💡 **Заготовка.** Замените `___` на нужное:")
    st.code(task.template, language="sql")
    st.button("📋 Вставить заготовку в редактор", on_click=insert_template, args=(task.id,),
              help="Текущий текст в редакторе будет заменён")

if task.id in ss.show_solution and can_show_solution:
    st.markdown("**Эталонное решение:**")
    st.code(task.solution, language="sql")

last = ss.results.get(task.id)
if last and last["kind"] == "run":
    res = last["res"]
    if res.ok:
        show_table(res)
    else:
        st.error(res.error)

elif last and last["kind"] == "check":
    result: engine.CheckResult = last["check"]
    if result.ok:
        used = ss.solved_hints.get(task.id, 0)
        st.success(result.message + (" Без подсказок 💪" if used == 0 else
                                     f" Подсказок использовано: {used} из {task.hint_levels}."))
        show_table(result.user)
        nxt = next_task_id(task.id)
        if nxt:
            st.button(f"Следующая задача: {TASK_BY_ID[nxt].title} →", type="primary",
                      on_click=select, args=(nxt,))
        else:
            st.balloons()
            st.success("Все задачи решены!")
    else:
        st.error(result.message)
        if result.user.ok:
            left, right = st.columns(2)
            with left:
                st.markdown("**Ваш результат**")
                show_table(result.user)
            with right:
                st.markdown("**Ожидаемый результат**")
                show_table(result.expected)
