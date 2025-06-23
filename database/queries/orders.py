import psycopg2
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db import get_connection
from decimal import Decimal
from database.queries.balance import get_user_balance, update_user_balance, get_balance_by_user_id, \
    update_user_balance_by_user_id


def cancel_order(order_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id_orders = %s AND id_users = %s", (order_id, user_id))
    conn.commit()
    conn.close()


def get_orders_by_user_and_status(telegram_id, is_active, status_type_names):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT o.id_orders, o.quantity, o.executed_quantity, o.price, 
               ot.order_type_name, ot.direction, st.status_type_name,
               o.created_date, a.asset_name
        FROM orders o
        JOIN users u ON o.id_users = u.id_users
        JOIN assets a ON o.id_assets = a.id_assets
        JOIN orders_type ot ON o.id_order_type = ot.id_order_type
        JOIN status_type st ON o.id_status_type = st.id_status_type
        WHERE u.telegram_id = %s
          AND o.is_active = %s
          AND st.status_type_name = ANY(ARRAY[%s])
        ORDER BY o.created_date DESC
    """, (telegram_id, is_active, status_type_names))
    result = cur.fetchall()
    conn.close()
    return result


def get_active_orders_by_user(telegram_id):
    return get_orders_by_user_and_status(telegram_id, True, ["в ожидании", "частично исполнена"])


def get_completed_orders_by_user(telegram_id):
    return get_orders_by_user_and_status(telegram_id, False, "исполнена")


def get_user_id_by_telegram_id(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id_users FROM Users WHERE telegram_id = %s", (str(telegram_id),))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def create_order(user_id, asset_id, price, quantity, direction, order_type, is_active=True, executed_quantity=None):
    conn = get_connection()
    cur = conn.cursor()

    print(
        f"CREATE_ORDER CALLED: {user_id=}, {asset_id=}, {quantity=}, {price=}, {direction=}, {order_type=}, {is_active=}")

    try:
        cur.execute("SELECT id_order_type FROM orders_type WHERE order_type_name = %s AND direction = %s",
                    (order_type, direction))
        id_order_type = cur.fetchone()[0]

        status = "в ожидании" if is_active else "исполнена"
        cur.execute("SELECT id_status_type FROM status_type WHERE status_type_name = %s", (status,))
        id_status_type = cur.fetchone()[0]

        if executed_quantity is None:
            executed_quantity = 0 if is_active else quantity

        cur.execute("""
            INSERT INTO orders (id_users, id_assets, id_order_type, id_status_type,
                                quantity, executed_quantity, price, is_active, created_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
        """, (
            user_id, asset_id, id_order_type, id_status_type,
            quantity, executed_quantity, price, is_active
        ))

        conn.commit()
        return True


    except psycopg2.Error as e:
        msg = str(e)
        if "Insufficient balance" in msg:
            print("❌ Недостаточно средств — заявка не создана")
            return "insufficient_funds"
        elif "Портфель для пользователя" in msg or "Недостаточно акций" in msg:
            print("❌ Недостаточно акций — заявка не создана")
            return "insufficient_assets"
        raise

    finally:
        cur.close()
        conn.close()


def try_execute_order(telegram_id, asset_id, quantity, price, direction, order_type):
    from database.queries.transactions import add_transaction
    user_id = get_user_id_by_telegram_id(telegram_id)
    conn = get_connection()
    cur = conn.cursor()

    opposite = "sell" if direction == "buy" else "buy"

    cur.execute("""
        SELECT o.id_orders, o.price, o.quantity, o.id_users
        FROM orders o
        JOIN orders_type ot ON o.id_order_type = ot.id_order_type
        WHERE o.id_assets = %s
          AND ot.direction = %s
          AND o.is_active = TRUE
          AND ((%s = 'buy' AND o.price <= %s) OR (%s = 'sell' AND o.price >= %s))
        ORDER BY o.price ASC, o.created_date ASC
        LIMIT 1
    """, (asset_id, opposite, direction, price, direction, price))

    match = cur.fetchone()

    if match:
        matched_order_id, matched_price, matched_qty_total, counterparty_id = match

        cur.execute("SELECT executed_quantity FROM orders WHERE id_orders = %s", (matched_order_id,))
        executed_qty_so_far = cur.fetchone()[0]

        matched_qty_remaining = matched_qty_total - executed_qty_so_far
        if matched_qty_remaining <= 0:
            conn.commit()
            cur.close()
            conn.close()
            return False

        executed_qty = min(matched_qty_remaining, quantity)
        final_price = matched_price

        cur.execute("""
                UPDATE orders
                SET executed_quantity = executed_quantity + %s,
                    is_active = CASE WHEN quantity = executed_quantity + %s THEN FALSE ELSE TRUE END,
                    id_status_type = CASE WHEN quantity = executed_quantity + %s THEN 3 ELSE 2 END
                WHERE id_orders = %s
            """, (executed_qty, executed_qty, executed_qty, matched_order_id))

        cur.execute("""
                SELECT id_orders, quantity, executed_quantity FROM orders
                WHERE id_users = %s AND id_assets = %s AND is_active = TRUE
                ORDER BY created_date DESC LIMIT 1
            """, (user_id, asset_id))
        current_order = cur.fetchone()
        if not current_order:
            conn.rollback()
            cur.close()
            conn.close()
            raise Exception("Не найдена активная заявка пользователя")

        current_order_id, total_qty, exec_qty = current_order
        new_exec_qty = exec_qty + executed_qty

        cur.execute("""
                UPDATE orders
                SET executed_quantity = %s,
                    is_active = CASE WHEN %s = quantity THEN FALSE ELSE TRUE END,
                    id_status_type = CASE WHEN %s = quantity THEN 3 ELSE 2 END
                WHERE id_orders = %s
            """, (new_exec_qty, new_exec_qty, new_exec_qty, current_order_id))

        total_cost = final_price * executed_qty
        buyer_id = user_id if direction == "buy" else counterparty_id
        seller_id = counterparty_id if direction == "buy" else user_id

        update_user_balance_by_user_id(buyer_id, get_balance_by_user_id(buyer_id) - total_cost)
        update_user_balance_by_user_id(seller_id, get_balance_by_user_id(seller_id) + total_cost)

        add_to_portfolio(telegram_id, asset_id, executed_qty, direction, final_price)
        cur.execute("SELECT telegram_id FROM users WHERE id_users = %s", (counterparty_id,))
        counter_telegram_id = cur.fetchone()[0]
        counter_direction = "buy" if direction == "sell" else "sell"
        add_to_portfolio(counter_telegram_id, asset_id, executed_qty, counter_direction, final_price)
        if direction == "buy":
            add_transaction(order_buy_id=current_order_id, order_sell_id=matched_order_id,
                            asset_id=asset_id, quantity=executed_qty, price=final_price)
        else:
            add_transaction(order_buy_id=matched_order_id, order_sell_id=current_order_id,
                            asset_id=asset_id, quantity=executed_qty, price=final_price)

        update_price_after_trade(asset_id, executed_qty, direction)

        conn.commit()
        cur.close()
        conn.close()
        return True
    else:
        if order_type == "market":
            update_price_after_trade(asset_id, quantity, direction)

        conn.commit()
        cur.close()
        conn.close()
        return False


def update_price_after_trade(asset_id, quantity, direction):
    conn = get_connection()
    cur = conn.cursor()

    # Получаем текущую цену
    cur.execute("SELECT current_price FROM assets WHERE id_assets = %s", (asset_id,))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return

    current_price = Decimal(result[0])
    delta = (Decimal(quantity) / 100_000) * current_price
    max_delta = current_price * Decimal("0.05")
    delta = min(delta, max_delta)

    if direction == "buy":
        new_price = current_price + delta
    else:
        new_price = current_price - delta
        new_price = max(new_price, Decimal("0.01"))  # Цена не может быть меньше 0.01

    cur.execute("UPDATE assets SET current_price = %s WHERE id_assets = %s", (new_price, asset_id))
    conn.commit()
    cur.close()
    conn.close()


def add_order_to_completed(order_id, quantity):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE orders
        SET executed_quantity = %s,
            is_active = False
        WHERE id_orders = %s
    """, (quantity, order_id))

    conn.commit()
    conn.close()


def add_to_portfolio(telegram_id, asset_id, quantity, action, price):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id_users FROM users
        WHERE telegram_id = %s
    """, (telegram_id,))
    user_result = cursor.fetchone()

    if not user_result:
        conn.close()
        raise ValueError("Пользователь с таким telegram_id не найден")

    id_users = user_result[0]

    cursor.execute("""
        SELECT id_portfolios FROM portfolios
        WHERE id_users = %s
        ORDER BY created_at ASC LIMIT 1
    """, (id_users,))
    portfolio_result = cursor.fetchone()

    if not portfolio_result:
        conn.close()
        raise ValueError("У пользователя нет портфеля")

    id_portfolio = portfolio_result[0]

    cursor.execute("""
        SELECT id_positions, quantity_of_lots, price FROM positions
        WHERE id_portfolios = %s AND id_assets = %s
    """, (id_portfolio, asset_id))
    position = cursor.fetchone()

    if position:
        id_position, current_quantity, current_price = position

        if action == "buy":
            current_price = int(round(current_price, 2))
            total_cost = current_price * current_quantity + price * quantity
            new_quantity = current_quantity + quantity
            new_avg_price = total_cost / new_quantity
            cursor.execute("""
                UPDATE positions
                SET quantity_of_lots = %s,
                    price = %s
                WHERE id_positions = %s
            """, (new_quantity, new_avg_price, id_position))

        elif action == "sell":
            new_quantity = current_quantity - quantity
            if new_quantity > 0:
                cursor.execute("""
                    UPDATE positions
                    SET quantity_of_lots = %s
                    WHERE id_positions = %s
                """, (new_quantity, id_position))
            else:
                cursor.execute("""
                    DELETE FROM positions
                    WHERE id_positions = %s
                """, (id_position,))
    else:
        if action == "buy":
            cursor.execute("""
                INSERT INTO positions (id_portfolios, id_assets, quantity_of_lots, price)
                VALUES (%s, %s, %s, %s)
            """, (id_portfolio, asset_id, quantity, price))
        else:
            conn.close()
            raise ValueError("Нельзя продать актив, которого нет в портфеле")

    conn.commit()
    conn.close()

def get_active_orders_by_telegram_id(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT o.id_orders, ot.direction, o.id_assets
        FROM orders o
        JOIN users u ON o.id_users = u.id_users
        JOIN orders_type ot ON o.id_order_type = ot.id_order_type
        WHERE u.telegram_id = %s AND o.is_active = TRUE
    """, (telegram_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{"id_orders": row[0], "direction": row[1], "id_assets": row[2]} for row in rows]

def cancel_order_by_id(order_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE orders
        SET is_active = FALSE,
            id_status_type = 4  -- статус "отменена", убедись, что 4 — это нужный статус
        WHERE id_orders = %s AND is_active = TRUE
    """, (order_id,))
    updated = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return updated > 0

def get_order_by_id(order_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM orders WHERE id_orders = %s", (order_id,))
            result = cursor.fetchone()
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            return None