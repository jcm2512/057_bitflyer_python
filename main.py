from bitflyer_actions import (
    get_balance,
    get_open_ifd_orders,
    get_current_market_price,
    ifd_order,
    has_funds_for_order,
    cancel_parent_order,
)

LIVE = True

# Initialise variables
TEST_PRICE = None
MIN_PRICE = 7500000
MAX_PRICE = 10700000
PRICE_INTERVAL = 200000


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
    print("Starting Main script...")
    print("")

    grid_interval = PRICE_INTERVAL
    intervals = grid_intervals()
    ifd_orders = get_open_ifd_orders()
    # print(f"ACTIVE Orders: {ifd_orders}")

    # TODO: Get high and low for past 90 days to determine Min and Max price
    # Min price should be at least 1 interval above the lowest price
    # Max price should be at least 1 interval below the highest price

    market_price = TEST_PRICE or get_current_market_price()

    buy_order_amt = find_closest_interval(market_price, intervals)

    print(f"market price: {market_price}")
    print(f"buy amt: {buy_order_amt}")

    # Remove IFD orders that are out of current range
    # -----------------------------------------------
    bottom_range = buy_order_amt - PRICE_INTERVAL
    print(f"bottom range: {bottom_range}")
    print("")
    open_order = [
        {
            "parent_order_acceptance_id": order["parent_order_acceptance_id"],
            "price": order["price"],
        }
        for order in ifd_orders
        if order["price"] == bottom_range
    ]
    for order in open_order:
        print(f"CANCELING ORDER")
        print("----------")
        print(f"price: {int(order["price"])}")
        print(f"id: {order["parent_order_acceptance_id"]}")
        cancel_parent_order(order["parent_order_acceptance_id"])
        print("----------")


    if LIVE:
        # Check if price band is within range
        if (MIN_PRICE - PRICE_INTERVAL) <= market_price <= MAX_PRICE:
            buy_order_amt = find_closest_interval(market_price, intervals)

            # Check if current price band is a vacant order
            if not is_open_order(buy_order_amt, ifd_orders):

                # Check balance and create IFD order
                if has_funds_for_order(market_price, get_balance("JPY")):
                    ifd_order(buy_order_amt, grid_interval)

                else:
                    print("INSUFFICIENT FUNDS")
            else:
                print(f"Order:{buy_order_amt} exists \n EXITING...")
        else:
            print("PRICE IS OUT OF RANGE")

    print("DONE")
