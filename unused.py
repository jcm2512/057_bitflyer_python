# bottom_range_amt = find_interval(market_price, intervals, floor=True) - PRICE_INTERVAL

# # Cancel BUY orders that are below cuttoff
# # ----------------------------------------

# out_of_current_range = [
#     {
#         "price": order["price"],
#         "parent_order_acceptance_id": order["parent_order_acceptance_id"],
#     }
#     for order in open_parent_buy_orders
#     # if order["price"] <= bottom_range_amt
# ]

# if out_of_current_range:
#     print("\n----------")
#     print(f"CANCELING ORDERS")

#     for order in out_of_current_range:
#         print("----------")
#         print(f"bottom: {bottom_range_amt}")
#         print(f"price: {int(order['price'])}")
#         id = order["parent_order_acceptance_id"]
#         print(f"id: {id}")
#         if CANCEL_ORDERS:
#             cancel_parent_order(id)
