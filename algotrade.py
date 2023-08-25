import requests
import time
import decimal
import json
import random

COINGECKO_API_ENDPOINT = "https://api.coingecko.com/api/v3"

def now():
    return decimal.Decimal(time.time())

def get_balance():
    with open('balance.json', 'r') as f:
        try:
            return json.load(f)
        except:
            return {'zusd': '1000.0', 'eth': '0.0'}

def update_balance(amount, name, price, sold):
    balance = get_balance()
    if sold:
        balance.pop(name.lower(), None)
        balance['zusd'] = str(float(balance.get('zusd', 0)) + amount * price)
    else:
        balance['zusd'] = str(float(balance.get('zusd', 0)) - (amount * price))
        balance[name.lower()] = str(amount)
    save_balance(balance)
    return balance

def save_balance(data):
    with open('balance.json', 'w') as f:
        json.dump(data, f, indent=4)

def get_crypto_data(coin_id):
    response = requests.get(f"{COINGECKO_API_ENDPOINT}/coins/{coin_id}/market_chart?vs_currency=usd&days=1")
    print(response.text)  # Print the API response

    if response.status_code == 200:
        data = response.json()
        prices = data.get('prices', [])
        print("Prices fetched:", prices)
        
        # Update the prices list in the data dictionary for the specific cryptocurrency pair
        data = load_crypto_data_from_file()
        data[coin_id]['prices'] = prices
        save_crypto_data(data)
        
        return [{'time': int(price[0] / 1000), 'price': price[1]} for price in prices]
    else:
        return []



def get_purchasing_price(name):
    trades = load_trades()
    return trades[name][-1]['price_usd']

def load_trades():
    with open('trades.json', 'r') as f:
        try:
            return json.load(f)
        except:
            return {pair: [] for pair in get_pairs()}

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
    analysis_data = clear_crypto_data(name)
    price = float(crypto_data[-1]['price'])
    funds = get_available_funds()
    amount = funds * (1 / price)
    balance = update_balance(amount, name, price, False)
    save_trade(price, name, True, False, amount)
    print('buy')

def sell_crypto(crypto_data, name):
    balance = get_balance()
    analysis_data = clear_crypto_data(name)
    price = float(crypto_data[-1]['price'])
    amount = float(balance[name.lower()])
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
    print("Balance:", balance)
    money = float(balance['zusd'])
    cryptos_not_owned = 6 - len([crypto for crypto in balance if crypto != 'zusd'])
    print("Cryptos not owned:", cryptos_not_owned)
    funds = money / cryptos_not_owned
    return funds



def bot(since, pairs):
    while True:
        for pair in pairs:
            trades = load_trades()
            print("Pairs:", pairs)
            print("Trades keys:", trades.keys())
            
            if len(trades.get(pair, [])) > 0:
                crypto_data = get_crypto_data(pair)
                if trades[pair][-1]['sold'] or trades[pair][-1] is None:
                    # check if we should buy
                    check_data(pair, crypto_data, True)
                if trades[pair][-1]['bought']:
                    # check if we should sell
                    check_data(pair, crypto_data, False)
            else:
                crypto_data = get_crypto_data(pair)
                check_data(pair, crypto_data, True)
            time.sleep(20)


def check_data(name, crypto_data, should_buy):
    high, low, close = 0, 0, 0
    for price in crypto_data[-100:]:
        high += float(price['price'])
        low += float(price['price'])
        close += float(price['price'])
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
        price = 0  # Initialize 'price' variable
        if 'prices' in data and len(data['prices']) > 0:
            price = float(data['prices'][-1]['price_usd'])
        if price != 0:  # Check if price is not zero
            areas.append(mva / price)  # Now 'price' is initialized properly

        if sell:
            purchase_price = float(get_purchasing_price(name))
            if price >= (purchase_price * 1.02):
                print('Should sell with 10% profit')
                return True
            if price < purchase_price:
                print('Selling at a loss')
                return True
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
    return ['ethereum', 'bitcoin', 'decentraland', 'the-graph', 'lisk', 'siacoin']

# ... (other parts of the code above)

def simulate_price_fluctuation(data):
    for name in get_pairs():
        if len(data[name]['prices']) > 0:
            last_price = data[name]['prices'][-1]['price']
        else:
            last_price = 100.0  # Replace this with an initial price if needed
        new_price = last_price * (1 + random.uniform(-0.01, 0.01))
        data[name]['prices'].append({'time': int(time.time()), 'price': new_price})
    save_crypto_data(data)


def simulate_trading(data):
    for name in get_pairs():
        if random.random() < 0.5:
            if random.random() < 0.5:
                buy_crypto(data[name]['prices'], name)
            else:
                sell_crypto(data[name]['prices'], name)
        time.sleep(random.randint(1, 5))

if __name__ == '__main__':
    pairs = get_pairs()
    since = int(time.time()) - 43200
    mva = load_crypto_data_from_file()
    
    while True:
        simulate_price_fluctuation(mva)
        simulate_trading(mva)
        time.sleep(20)
