import travel as t

while t.hold()["credits"] < 500:
    t.travel_and_buy()
    t.travel_and_sell()

t.travel_and_buy()
t.travel_to_vesta()