"""SQL-тренажёр на Streamlit. Запуск: streamlit run app.py"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import engine

SANDBOX = "__sandbox__"
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


# ---------------------------------------------------------------- состояние

ss = st.session_state
ss.setdefault("current", TASKS[0].id)
ss.setdefault("solved", set())
ss.setdefault("attempts", {})        # id -> число неудачных проверок
ss.setdefault("results", {})         # id -> dict с последним результатом
ss.setdefault("show_hint", set())
ss.setdefault("show_solution", set())


def select(task_id: str) -> None:
    ss.current = task_id


def next_task_id(current: str) -> str | None:
    ids = [t.id for t in TASKS]
    i = ids.index(current)
    rest = ids[i + 1:] + ids[:i]
    for tid in rest:                 # сначала ближайшая нерешённая
        if tid not in ss.solved:
            return tid
    return ids[i + 1] if i + 1 < len(ids) else None


def reset_progress() -> None:
    for key in ("solved", "attempts", "results", "show_hint", "show_solution"):
        del ss[key]
    for key in list(ss.keys()):
        if str(key).startswith("sql_"):
            del ss[key]
    ss.current = TASKS[0].id


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
        has_current = any(t.id == ss.current for t in topic.tasks)
        with st.expander(f"{topic.name}  ·  {done}/{len(topic.tasks)}", expanded=has_current):
            for t in topic.tasks:
                mark = "✅" if t.id in ss.solved else "▫️"
                st.button(f"{mark} {t.title}", key=f"nav_{t.id}", use_container_width=True,
                          on_click=select, args=(t.id,),
                          type="primary" if t.id == ss.current else "secondary")

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


# ---------------------------------------------------------------- задача

task = TASK_BY_ID[ss.current]
attempts = ss.attempts.get(task.id, 0)
is_solved = task.id in ss.solved

st.caption(task.topic)
st.header(("✅ " if is_solved else "") + task.title)
st.markdown(task.text)
if task.ordered:
    st.caption("↕️ В этой задаче важен порядок строк.")

schema_panel()

sql = st.text_area("Ваш запрос", key=f"sql_{task.id}", height=180,
                   placeholder="SELECT ...")

c1, c2, c3, c4 = st.columns(4)
run_clicked = c1.button("▶ Выполнить", use_container_width=True)
check_clicked = c2.button("✔ Проверить", type="primary", use_container_width=True)
if c3.button("💡 Подсказка", use_container_width=True):
    ss.show_hint.symmetric_difference_update({task.id})
can_show_solution = is_solved or attempts >= SOLUTION_AFTER_ATTEMPTS
if c4.button("👀 Решение", use_container_width=True, disabled=not can_show_solution,
             help=None if can_show_solution else
             f"Станет доступно после {SOLUTION_AFTER_ATTEMPTS} неудачных проверок"):
    ss.show_solution.symmetric_difference_update({task.id})

if run_clicked:
    ss.results[task.id] = {"kind": "run", "res": engine.run_query(sql)}

if check_clicked:
    result = engine.check(task, sql)
    ss.results[task.id] = {"kind": "check", "check": result}
    if result.ok:
        ss.solved.add(task.id)
    else:
        ss.attempts[task.id] = attempts + 1
    st.rerun()   # чтобы сразу обновились отметки в боковой панели

if task.id in ss.show_hint and task.hint:
    st.info(f"💡 {task.hint}")

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
        st.success(result.message)
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
