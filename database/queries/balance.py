from database.db import get_connection

def get_user_balance(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT balance 
        FROM users 
        WHERE telegram_id = %s
    """, (telegram_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def update_user_balance(telegram_id, new_balance):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users 
        SET balance = %s 
        WHERE telegram_id = %s
    """, (new_balance, telegram_id))
    conn.commit()
    cur.close()
    conn.close()

def get_balance_by_user_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT balance 
        FROM users 
        WHERE id_users = %s
    """, (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result and result[0] is not None else 0

def update_user_balance_by_user_id(user_id, new_balance):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users 
        SET balance = %s 
        WHERE id_users = %s
    """, (new_balance, user_id))
    conn.commit()
    cur.close()
    conn.close()
