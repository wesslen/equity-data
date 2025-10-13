#!/usr/bin/env python3
# scripts/generate_options_heuristic.py

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pandas_market_calendars as mcal

def is_trading_day():
    """Check if today is a US trading day"""
    nyse = mcal.get_calendar('NYSE')
    today = datetime.now().date()
    schedule = nyse.schedule(start_date=today, end_date=today)
    return len(schedule) > 0

def load_stock_symbols():
    """Load stock symbols from file"""
    with open('data/stock_symbols.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]

def load_historical_data():
    """Load historical price data"""
    file_path = 'data/historical_prices.json'
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def save_historical_data(data):
    """Save historical price data"""
    os.makedirs('data', exist_ok=True)
    with open('data/historical_prices.json', 'w') as f:
        json.dump(data, f, indent=2)

def get_previous_close(symbol):
    """Get yesterday's closing price"""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period='5d')
    if len(hist) < 2:
        raise ValueError(f"Insufficient data for {symbol}")
    return hist['Close'].iloc[-2]  # Yesterday's close

def update_historical_prices(symbol, price):
    """Update historical price database"""
    hist_data = load_historical_data()
    
    if symbol not in hist_data:
        hist_data[symbol] = []
    
    hist_data[symbol].append({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'price': float(price)
    })
    
    # Keep only last 252 days (1 trading year)
    hist_data[symbol] = hist_data[symbol][-252:]
    
    save_historical_data(hist_data)

def round_strike(price, strike_value):
    """Round strike to nearest standard increment"""
    if price < 25:
        increment = 0.5
    elif price < 200:
        increment = 1.0
    else:
        increment = 5.0
    
    return round(strike_value / increment) * increment

def get_option_expiration(days_target):
    """Get closest monthly expiration to target days"""
    nyse = mcal.get_calendar('NYSE')
    today = datetime.now().date()
    
    # Get third Friday of each month for next 12 months
    expirations = []
    for month_offset in range(12):
        target_month = today + timedelta(days=30*month_offset)
        year = target_month.year
        month = target_month.month
        
        # Find third Friday
        first_day = datetime(year, month, 1).date()
        first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
        third_friday = first_friday + timedelta(days=14)
        
        expirations.append(third_friday)
    
    # Find closest to target
    target_date = today + timedelta(days=days_target)
    closest = min(expirations, key=lambda x: abs((x - target_date).days))
    
    return closest.strftime('%Y-%m-%d')

def generate_options_for_stock(symbol, price):
    """Generate 8-option heuristic for a stock"""
    options = []
    
    # Phase 1: Structured Exploitation (5 options)
    exp_3m = get_option_expiration(90)
    exp_6m = get_option_expiration(180)
    
    # Option 1: 3-month ATM
    options.append({
        'Symbol': symbol,
        'Option_Num': 1,
        'Expiration': exp_3m,
        'Strike': round_strike(price, price),
        'Type': 'Put',
        'Description': '3mo ATM - Anchor',
        'Bid': '',
        'Ask': '',
        'Mid': '',
        'Notes': ''
    })
    
    # Option 2: 3-month 15% OTM
    options.append({
        'Symbol': symbol,
        'Option_Num': 2,
        'Expiration': exp_3m,
        'Strike': round_strike(price, price * 0.85),
        'Type': 'Put',
        'Description': '3mo 15% OTM - Fear Premium',
        'Bid': '',
        'Ask': '',
        'Mid': '',
        'Notes': ''
    })
    
    # Option 3: 3-month 30% OTM
    options.append({
        'Symbol': symbol,
        'Option_Num': 3,
        'Expiration': exp_3m,
        'Strike': round_strike(price, price * 0.70),
        'Type': 'Put',
        'Description': '3mo 30% OTM - Lottery',
        'Bid': '',
        'Ask': '',
        'Mid': '',
        'Notes': ''
    })
    
    # Option 4: 6-month 15% OTM (Sweet Spot)
    options.append({
        'Symbol': symbol,
        'Option_Num': 4,
        'Expiration': exp_6m,
        'Strike': round_strike(price, price * 0.85),
        'Type': 'Put',
        'Description': '6mo 15% OTM - Sweet Spot',
        'Bid': '',
        'Ask': '',
        'Mid': '',
        'Notes': ''
    })
    
    # Option 5: 6-month ATM
    options.append({
        'Symbol': symbol,
        'Option_Num': 5,
        'Expiration': exp_6m,
        'Strike': round_strike(price, price),
        'Type': 'Put',
        'Description': '6mo ATM - Arb Check',
        'Bid': '',
        'Ask': '',
        'Mid': '',
        'Notes': ''
    })
    
    # Phase 2: Simplified Exploration (2 options)
    exp_4_5m = get_option_expiration(135)
    
    # Option 6: 4.5-month 20% OTM
    options.append({
        'Symbol': symbol,
        'Option_Num': 6,
        'Expiration': exp_4_5m,
        'Strike': round_strike(price, price * 0.80),
        'Type': 'Put',
        'Description': '4.5mo 20% OTM - Explore',
        'Bid': '',
        'Ask': '',
        'Mid': '',
        'Notes': ''
    })
    
    # Option 7: 3-month 40% OTM
    options.append({
        'Symbol': symbol,
        'Option_Num': 7,
        'Expiration': exp_3m,
        'Strike': round_strike(price, price * 0.60),
        'Type': 'Put',
        'Description': '3mo 40% OTM - Deep Explore',
        'Bid': '',
        'Ask': '',
        'Mid': '',
        'Notes': ''
    })
    
    # Phase 3: Wild Card (1 option)
    day_of_year = datetime.now().timetuple().tm_yday
    ticker_sum = sum(ord(c) for c in symbol)
    seed = (day_of_year * ticker_sum) % 6
    
    otm_levels = [0.95, 0.90, 0.82, 0.75, 0.65, 0.55]
    days_options = [60, 90, 120, 150, 180, 210]
    
    random_otm = otm_levels[seed]
    random_days = days_options[(day_of_year * ticker_sum) % len(days_options)]
    random_exp = get_option_expiration(random_days)
    
    options.append({
        'Symbol': symbol,
        'Option_Num': 8,
        'Expiration': random_exp,
        'Strike': round_strike(price, price * random_otm),
        'Type': 'Put',
        'Description': f'Random - {int((1-random_otm)*100)}% OTM',
        'Bid': '',
        'Ask': '',
        'Mid': '',
        'Notes': ''
    })
    
    return options

def main():
    # Check if trading day
    if not is_trading_day():
        print("Not a trading day. Skipping.")
        return
    
    # Load symbols
    symbols = load_stock_symbols()
    print(f"Processing {len(symbols)} symbols: {', '.join(symbols)}")
    
    all_options = []
    
    for symbol in symbols:
        try:
            print(f"Fetching data for {symbol}...")
            price = get_previous_close(symbol)
            print(f"  Previous close: ${price:.2f}")
            
            # Update historical data
            update_historical_prices(symbol, price)
            
            # Generate options
            options = generate_options_for_stock(symbol, price)
            all_options.extend(options)
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    if not all_options:
        print("No options generated.")
        return
    
    # Create output DataFrame
    df = pd.DataFrame(all_options)
    
    # Save to CSV
    os.makedirs('output', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d')
    output_file = f'output/options_heuristic_{timestamp}.csv'
    df.to_csv(output_file, index=False)
    
    print(f"\nGenerated {len(all_options)} options")
    print(f"Output saved to: {output_file}")
    print("\nSample output:")
    print(df.head(10).to_string(index=False))

if __name__ == '__main__':
    main()
