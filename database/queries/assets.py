from database.db import get_connection

def get_all_assets():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id_assets, asset_name, current_price 
        FROM assets 
        ORDER BY asset_name
    """)
    assets = cur.fetchall()
    cur.close()
    conn.close()
    return assets

def get_asset_by_id(asset_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT asset_name, current_price 
        FROM assets 
        WHERE id_assets = %s
    """, (asset_id,))
    asset = cur.fetchone()
    cur.close()
    conn.close()
    return asset

def get_asset_order_book(asset_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT price, SUM(quantity - executed_quantity) as volume, direction
        FROM orders o
        JOIN orders_type ot ON o.id_order_type = ot.id_order_type
        WHERE id_assets = %s AND is_active = TRUE
        GROUP BY price, direction
        ORDER BY direction, price
    """, (asset_id,))
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result

def get_asset_name_by_id(asset_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT asset_name FROM assets WHERE id_assets = %s", (asset_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else "неизвестно"
