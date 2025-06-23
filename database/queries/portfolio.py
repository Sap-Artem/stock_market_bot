import psycopg2
from config import DB_CONFIG

def get_user_portfolio_by_telegram_id(telegram_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            a.asset_name,
            a.current_price,
            p.quantity_of_lots,
            p.price AS buy_price
        FROM Users u
        JOIN Portfolios pf ON pf.id_users = u.id_users
        JOIN Positions p ON p.id_portfolios = pf.id_portfolios
        JOIN Assets a ON a.id_assets = p.id_assets
        WHERE u.telegram_id = %s
        ORDER BY a.asset_name
    """, (str(telegram_id),))
    result = cur.fetchall()
    conn.close()
    return result
import psycopg2
from config import DB_CONFIG

def get_user_portfolio_by_telegram_id(telegram_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            a.asset_name,
            a.current_price,
            p.quantity_of_lots,
            p.price AS buy_price
        FROM Users u
        JOIN Portfolios pf ON pf.id_users = u.id_users
        JOIN Positions p ON p.id_portfolios = pf.id_portfolios
        JOIN Assets a ON a.id_assets = p.id_assets
        WHERE u.telegram_id = %s
        ORDER BY a.asset_name
    """, (str(telegram_id),))
    result = cur.fetchall()
    conn.close()
    return result
