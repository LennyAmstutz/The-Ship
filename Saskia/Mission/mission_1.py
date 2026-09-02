from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Saskia.Actions.communication_commands import buy, sell
from Saskia.Actions.steering_commands import set_target, wait_until_in_reach
from Saskia.config import BUY_STATION as AZURA, SELL_STATION as CORE, RESOURCE as ITEM


def buy_at_azura(amount):
    set_target(AZURA)
    wait_until_in_reach(AZURA)
    return buy(AZURA, ITEM, amount)


def sell_at_core(amount):
    set_target(CORE)
    wait_until_in_reach(CORE)
    return sell(CORE, ITEM, amount)


def run():
    amounts = [4, 8, 12]
    for i, amount in enumerate(amounts):
        buy_at_azura(amount)
        if i < len(amounts) - 1:
            sell_at_core(amount)
    set_target({"x": 7000, "y": 7000})

if __name__ == "__main__":
    run()