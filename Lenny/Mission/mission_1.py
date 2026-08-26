
import requests
from Actions.communication_commands import buy, sell
from Actions.steering_commands import set_target, wait_until_in_reach
from config import BUY_STATION as AZURA, SELL_STATION as CORE, RESOURCE as ITEM


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
    try:
        buy_at_azura(amount)
    except requests.RequestException as e:
        print(f"Fehler beim Kaufen: {e}")
        break
    except TimeoutError as e:
        print(f"Timeout beim Warten auf Station vor dem Kaufen: {e}")
        break

    if i < len(amounts) - 1:
        try:
            sell_at_core(amount)
        except requests.RequestException as e:
            print(f"Fehler beim Verkaufen: {e}")
            break
        except TimeoutError as e:
            print(f"Timeout beim Warten auf Station vor dem Verkaufen: {e}")
            break

try:
    set_target({"x": 7000, "y": 7000})
except requests.RequestException as e:
    print(f"Fehler beim Setzen des Ziels: {e}")

