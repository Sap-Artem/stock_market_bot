from database.db import get_connection


def add_transaction(order_buy_id, order_sell_id, asset_id, quantity, price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (
            id_orders_buy,
            id_orders_sell,
            id_assets,
            quantity,
            price,
            transaction_date
        )
        VALUES (%s, %s, %s, %s, %s, now())
    """, (order_buy_id, order_sell_id, asset_id, quantity, price))
    conn.commit()
    conn.close()
