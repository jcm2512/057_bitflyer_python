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

from settings import LIVE, TEST_PRICE, MIN_PRICE, MAX_PRICE, PRICE_INTERVAL


def grid_intervals(min=MIN_PRICE, max=MAX_PRICE, interval=PRICE_INTERVAL):
    return [num for num in range(min, max, interval)]


def find_closest_interval(market_price, intervals):
    closest_interval = min(intervals, key=lambda x: abs(x - market_price))
    return closest_interval


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
    buy_order_amt = find_closest_interval(market_price, intervals)
    bottom_range = buy_order_amt - (2 * PRICE_INTERVAL)

    print(f"MARKET PRICE: {market_price}")
    print(f"BUY ORDER: {buy_order_amt}")
    print("")

    print(f"RANGE: \n{MIN_PRICE} - {MAX_PRICE - PRICE_INTERVAL}")
    print(f"BOTTOM: \n{bottom_range}")
    print("")
    print(
        f"ACTIVE SELL Orders: \n{[order['price'] for order in open_limit_sell_orders]}"
    )
    print("")

    # TODO: Get high and low for past 90 days to determine Min and Max price
    # Min price should be at least 1 interval above the lowest price
    # Max price should be at least 1 interval below the highest price

    if LIVE:
        # Check if price band is within range
        if (MIN_PRICE - PRICE_INTERVAL) <= market_price <= MAX_PRICE:
            buy_order_amt = find_closest_interval(market_price, intervals)

            # Check if BUY price PLUS interval == any open SELL order
            if not is_open_order(
                buy_order_amt + PRICE_INTERVAL, open_limit_sell_orders
            ):
                print(f"buy amt: {buy_order_amt}")

                # Check balance and create IFD order
                if has_funds_for_order(market_price, get_balance("JPY")):
                    if LIVE:
                        ifd_order(buy_order_amt, grid_interval)
                    else:
                        print(f"TEST: IFD ORDER FOR {buy_order_amt}")

                else:
                    print("INSUFFICIENT FUNDS")
            else:
                print(f"Existing Order:{buy_order_amt} \nEXITING...")
        else:
            print("PRICE IS OUT OF RANGE")

        # Cancel BUY orders that are below cuttoff
        # ----------------------------------------

        bottom_range = buy_order_amt - PRICE_INTERVAL
        out_of_current_range = [
            {
                "price": order["price"],
                "parent_order_acceptance_id": order["parent_order_acceptance_id"],
            }
            for order in open_parent_buy_orders
            if order["price"] <= bottom_range
        ]
        if out_of_current_range:
            print("\n----------")
            print(f"CANCELING ORDERS")

            for order in out_of_current_range:
                print("----------")
                print(f"bottom: {bottom_range}")
                print(f"price: {int(order['price'])}")
                id = order["parent_order_acceptance_id"]
                print(f"id: {id}")
                cancel_parent_order(id)


print("\n>>> End of script")
