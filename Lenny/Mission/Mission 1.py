from Actions.communication_commands import buy, sell
from Actions.steering_commands import set_target, wait_until_in_reach

AZURA = "Azura Station"
CORE = "Core Station"
ITEM = "IRON"


def buy_at_azura(amount):
    set_target(AZURA)
    wait_until_in_reach(AZURA)
    return buy(AZURA, ITEM, amount)


def sell_at_core(amount):
    set_target(CORE)
    wait_until_in_reach(CORE)
    return sell(CORE, ITEM, amount)


amounts = [4, 8, 12]
for i, amount in enumerate(amounts):
    print(buy_at_azura(amount))
    if i < len(amounts) - 1:
        print(sell_at_core(amount))

set_target({"x": 7000, "y": 7000})
