import krakenex
from pykrakenapi import KrakenAPI
import time
import decimal
import json

# Initialize Kraken API
k = krakenex.API()
k.load_key('kraken.key')  # Load your API key

def now():
    return decimal.Decimal(time.time())

def get_balance():
    with open('balance.json', 'r') as f:
        try:
            return json.load(f)
        except:
            # change this for the actual query to the database once the script is working
            return {'ZUSD': '1000.0', 'EUR.HOLD': '0.0000'}

def update_balance(amount, name, price, sold):
    balance = get_balance()
    if sold:
        balance.pop(name[:-4], None)
        balance['ZUSD'] = str(float(balance['ZUSD']) + amount * price)
    else:
        balance['ZUSD'] = str(float(balance['ZUSD']) - (amount * price))
        balance[name[:-4]] = str(amount)
    save_balance(balance)
    return balance

def save_balance(data):
    with open('balance.json', 'w') as f:
        json.dump(data, f, indent=4)

def get_crypto_data(pair, since):
    ret = k.query_public('OHLC', data={'pair': pair, 'since': since})
    return ret['result'][pair]

def get_purchasing_price(name):
    trades = load_trades()
    return trades[name][-1]['price_usd']

def load_trades():
    trades = {}
    with open('trades.json', 'r') as f:
        try:
            trades = json.load(f)
        except:
            for crypto in pairs:
                trades[crypto] = []
        return trades

def save_crypto_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)

def load_crypto_data_from_file():
    data = {}
    with open('data.json', 'r') as f:
        try:
            data = json.load(f)
        except:
            data = make_crypto_data(data)
            save_crypto_data(data)
        return data

def make_crypto_data(data):
    for name in get_pairs():
        data[name] = {
            'high': [],
            'low': [],
            'close': [],
            'prices': []
        }
    return data

def save_trade(close, name, bought, sold, amount):
    trade = {
        'time_stamp': str(int(time.time())),
        'price_usd': close,
        'bought': bought,
        'sold': sold,
        'amount': amount
    }
    print('TRADE:')
    print(json.dumps(trade, indent=4))
    trades = load_trades()
    trades[name].append(trade)
    with open('trades.json', 'w') as f:
        json.dump(trades, f, indent=4)

def buy_crypto(crypto_data, name):
    # execute trade
    analysis_data = clear_crypto_data(name)
    # find what we can buy for
    price = float(crypto_data[-1][4])
    funds = get_available_funds()
    amount = funds * (1 / price)
    balance = update_balance(amount, name, price, False)
    save_trade(price, name, True, False, amount)
    print('buy')

def sell_crypto(crypto_data, name):
    balance = get_balance()
    analysis_data = clear_crypto_data(name)
    price = float(crypto_data[-1][4])
    amount = float(balance[name[:-4]])
    balance = update_balance(amount, name, price, True)
    save_trade(price, name, False, True, amount)
    print('sell')

def clear_crypto_data(name):
    data = load_crypto_data_from_file()
    for key in data[name]:
        data[name][key] = delete_entries(data[name], key)
    save_crypto_data(data)
    return data

def delete_entries(data, key):
    clean_array = []
    for entry in data[key][-10:]:
        clean_array.append(entry)
    return clean_array

def get_available_funds():
    balance = get_balance()
    money = float(balance['ZUSD'])
    cryptos_not_owned = 6 - (len(balance) - 2)
    funds = money / cryptos_not_owned
    return funds

def bot(since, k, pairs):
    while True:
        for pair in pairs:
            trades = load_trades()
            if len(trades[pair]) > 0:
                crypto_data = get_crypto_data(pair, since)
                if trades[pair][-1]['sold'] or trades[pair][-1] is None:
                    # check if we should buy
                    check_data(pair, crypto_data, True)
                if trades[pair][-1]['bought']:
                    # check if we should sell
                    check_data(pair, crypto_data, False)
            else:
                crypto_data = get_crypto_data(pair, since)
                check_data(pair, crypto_data, True)
            time.sleep(20)

def check_data(name, crypto_data, should_buy):
    high, low, close = 0, 0, 0
    for b in crypto_data[-100:]:
        if b not in ma[name]['prices']:
            mva[name]['prices'].append(b)
            high += float(b[2])
            low += float(b[3])
            close += float(b[4])
    mva[name]['high'].append(high / 100)
    mva[name]['low'].append(low / 100)
    mva[name]['close'].append(close / 100)
    save_crypto_data(mva)
    if should_buy:
        try_buy(mva[name], name, crypto_data)
    else:
        try_sell(mva[name], name, crypto_data)

def try_buy(data, name, crypto_data):
    make_trade = check_opportunity(data, name, False, True)
    if make_trade:
        buy_crypto(crypto_data, name)

def check_opportunity(data, name, sell, buy):
    count = 0
    previous_value = 0
    trends = []
    for mva in data['close'][-10:]:
        if previous_value == 0:
            previous_value = mva
        else:
            if mva / previous_value > 1:
                if count < 1:
                    count = 1
                else:
                    count += 1
                trends.append("UPTREND")
            elif mva / previous_value < 1:
                trends.append("DOWNTREND")
                if count > 0:
                    count = -1
                else:
                    count -= 1
            else:
                trends.append("NOTREND")
            previous_value = mva
    areas = []
    for mva in reversed(data['close'][-5:]):
        area = 0
        price = float(data['prices'][-1][3])
        if sell:
            purchase_price = float(get_purchasing_price(name))
            if price >= (purchase_price * 1.02):
                print('Should sell with 10% profit')
                return True
            if price < purchase_price:
                print('Selling at a loss')
                return True
        areas.append(mva / price)
        if buy:
            counter = 0
            if count >= 5:
                for area in areas:
                    counter += area
                if counter / 3 >= 1.05:
                    return True
    return False

def try_sell(data, name, crypto_data):
    make_trade = check_opportunity(data, name, True, False)
    if make_trade:
        sell_crypto(crypto_data, name)

def get_pairs():
    return ['XETHZUSD', 'XXBTZUSD', 'MANAUSD', 'GRTUSD', 'LSKUSD', 'SCUSD']

if __name__ == '__main__':
    pairs = get_pairs()
    since = str(int(time.time() - 43200))
    mva = load_crypto_data_from_file()
    bot(since, k, pairs)
