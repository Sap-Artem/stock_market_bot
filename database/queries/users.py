from database.db import get_connection


def insert_user(telegram_id, name, phone, email):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (telegram_id, name, email, phone, status, balance)
        VALUES (%s, %s, %s, %s, FALSE, 10000.0)
        ON CONFLICT (telegram_id) DO NOTHING
    """, (telegram_id, name, email, phone))

    cur.execute("SELECT id_users FROM users WHERE telegram_id = %s", (telegram_id,))
    user_id = cur.fetchone()
    if user_id is None:
        conn.rollback()
        cur.close()
        conn.close()
        raise Exception("Не удалось получить id пользователя после вставки.")
    user_id = user_id[0]

    # 3. Проверяем, есть ли уже портфель
    cur.execute("SELECT 1 FROM portfolios WHERE id_users = %s", (user_id,))
    has_portfolio = cur.fetchone()
    if not has_portfolio:
        cur.execute("""
            INSERT INTO portfolios (id_users, created_at)
            VALUES (%s, NOW())
        """, (user_id,))
        print("Готово")

    conn.commit()
    cur.close()
    conn.close()

def user_exists(telegram_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE telegram_id = %s", (telegram_id,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists
