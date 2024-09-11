from bitflyer_actions import (
    get_balance,
    get_open_limit_orders,
    get_current_market_price,
    get_parent_orders,
    get_parent_order,
    ifd_order,
    has_funds_for_order,
    cancel_parent_order,
)

from settings import (
    LIVE,
    TEST_PRICE,
    MIN_PRICE,
    MAX_PRICE,
    PRICE_INTERVAL,
    PLACE_ORDERS,
    CANCEL_ORDERS,
)


def grid_intervals(min=MIN_PRICE, max=MAX_PRICE, interval=PRICE_INTERVAL):
    return [num for num in range(min, max, interval)]


def find_interval(market_price, intervals, floor=False):
    if floor:
        lower_intervals = [x for x in intervals if x <= market_price]

        if not lower_intervals:
            print(f"ERROR: No intervals found below {market_price}")
            return None

        out = max(lower_intervals)
    else:
        out = min(intervals, key=lambda x: abs(x - market_price))

    return out


def is_open_order(amt, open_orders):
    if open_orders is None:
        return False
    return any(order["price"] == amt for order in open_orders)


if __name__ == "__main__":
    print(">>> Starting Main script")
    print("")

    grid_interval = PRICE_INTERVAL
    intervals = grid_intervals()
    parent_buy_orders = get_parent_orders()
    open_parent_buy_orders = [
        order
        for order in parent_buy_orders
        # if order["executed_size"] == 0
    ]
    open_limit_sell_orders = get_open_limit_orders("SELL")

    market_price = TEST_PRICE or get_current_market_price()

    buy_order_amt = find_interval(market_price, intervals)

    print(f"MARKET PRICE: {market_price}")
    print(f"BUY ORDER: {buy_order_amt}")
    print("")

    print(f"RANGE: \n{MIN_PRICE} - {MAX_PRICE - PRICE_INTERVAL}")
    print("")
    print(
        f"ACTIVE SELL Orders: \n{[order['price'] for order in open_limit_sell_orders]}"
    )
    print("")

    # TODO: Get high and low for past 90 days to determine Min and Max price
    # Min price should be at least 1 interval above the lowest price
    # Max price should be at least 1 interval below the highest price

    if LIVE:
        if not (MIN_PRICE - PRICE_INTERVAL) <= market_price <= MAX_PRICE:
            print("PRICE IS OUT OF RANGE")

        elif is_open_order(buy_order_amt + PRICE_INTERVAL, open_limit_sell_orders):
            print(f"Existing Order:{buy_order_amt} \nEXITING...")

        # Check Balance
        elif not has_funds_for_order(market_price, get_balance("JPY")):
            print("INSUFFICIENT FUNDS")

        else:
            print(f"buy amt: {buy_order_amt}")
            if PLACE_ORDERS:
                ifd_order(buy_order_amt, grid_interval)
            else:
                print(f"TEST: IFD ORDER FOR {buy_order_amt}")

print("\n>>> End of script")
