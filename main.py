from bitflyer_actions import (
    get_balance,
    get_open_ifd_orders,
    get_current_market_price,
    ifd_order,
    has_funds_for_order,
)

LIVE = True

# Initialise variables
TEST_PRICE = None
MIN_PRICE = 8900000
MAX_PRICE = 10700000
PRICE_INTERVAL = 200000


def grid_intervals(min=MIN_PRICE, max=MAX_PRICE, interval=PRICE_INTERVAL):
    return [num for num in range(min, max, interval)]


def find_closest_interval(market_price, intervals):
    closest_interval = min(intervals, key=lambda x: abs(x - market_price))
    return closest_interval


def is_open_order(amt, open_orders):
    return amt in open_orders


if __name__ == "__main__":
    print("Starting Main script...")
    if not LIVE:
        TEST_PRICE = 11500000
        ifd_orders = get_open_ifd_orders()
        print(f"ifd orders: {ifd_orders}")

    grid_interval = PRICE_INTERVAL
    intervals = grid_intervals()

    # TODO: Get high and low for past 90 days to determine Min and Max price
    # Min price should be at least 1 interval above the lowest price
    # Max price should be at least 1 interval below the highest price

    market_price = TEST_PRICE or get_current_market_price()

    buy_order_amt = find_closest_interval(market_price, intervals)
    print(f"intervals: {intervals}")
    print(f"market price: {market_price}")
    print(f"buy amt: {buy_order_amt}")

    if LIVE:
        if MIN_PRICE <= market_price <= MAX_PRICE:
            buy_order_amt = find_closest_interval(market_price, intervals)
            ifd_orders = get_open_ifd_orders()
            print(f"IFD Orders: {ifd_orders}")

            if not is_open_order(buy_order_amt, ifd_orders):
                if has_funds_for_order(market_price, get_balance("JPY")):
                    ifd_order(buy_order_amt, grid_interval)
                else:
                    print("INSUFFICIENT FUNDS")
            else:
                print(f"Order:{buy_order_amt} exists \n EXITING...")
        else:
            print("PRICE IS OUT OF RANGE")

    print("DONE")
