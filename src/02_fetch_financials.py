import pandas as pd
from yahooquery import Ticker
import json
import os
import time

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_MAPPING_FILE = os.path.join(base_dir, "data", "processed", "cache_mapping.json")
CACHE_FINANCIALS_FILE = os.path.join(base_dir, "data", "processed", "cache_financials.json")
FX_CACHE_FILE = os.path.join(base_dir, "data", "processed", "fx_cache.json")
UNIFIED_FILE = os.path.join(base_dir, "data", "processed", "unified_holdings.csv")
RAW_DATA_FILE = os.path.join(base_dir, "data", "processed", "valuation_raw_data.csv")

def get_fx_rate(currency, fx_cache):
    if not currency or pd.isna(currency): return 1.0
    currency = str(currency).upper()
    if currency == 'EUR': return 1.0
    
    currency_map = {
        'ZAC': 'ZAR',
        'ILA': 'ILS',
        'IEP': 'EUR',
        'GBP': 'GBP'
    }
    fx_symbol = currency_map.get(currency, currency)
    if fx_symbol == 'EUR': return 1.0
    
    if fx_symbol in fx_cache: return fx_cache[fx_symbol]
    
    try:
        t = Ticker(f"{fx_symbol}EUR=X")
        rate = t.price[f"{fx_symbol}EUR=X"].get('regularMarketPrice', 1.0)
        fx_cache[fx_symbol] = rate
        return rate
    except:
        return 1.0

def main():
    print("Loading unified holdings...")
    df = pd.read_csv(UNIFIED_FILE)
    
    mapping_cache = {}
    if os.path.exists(CACHE_MAPPING_FILE):
        with open(CACHE_MAPPING_FILE, 'r') as f:
            mapping_cache = json.load(f)
            
    df['YF_Ticker'] = df.apply(lambda row: mapping_cache.get(row['ISIN'] if pd.notna(row['ISIN']) else f"{row['ETF']}_{row['Name']}"), axis=1)
    valid_df = df.dropna(subset=['YF_Ticker']).copy()
    unique_tickers = valid_df['YF_Ticker'].unique().tolist()
    
    print(f"Total unique tickers mapped: {len(unique_tickers)}")
    
    financials_cache = {}
    if os.path.exists(CACHE_FINANCIALS_FILE):
        with open(CACHE_FINANCIALS_FILE, 'r') as f:
            financials_cache = json.load(f)
            
    fx_cache = {'EUR': 1.0}
    if os.path.exists(FX_CACHE_FILE):
        with open(FX_CACHE_FILE, 'r') as f:
            fx_cache = json.load(f)
            
    to_fetch = [t for t in unique_tickers if t not in financials_cache]
    print(f"Need to fetch financials for {len(to_fetch)} items.")
    
    chunk_size = 20
    max_retries = 3
    for i in range(0, len(to_fetch), chunk_size):
        chunk = to_fetch[i:i+chunk_size]
        print(f"Fetching chunk {i} to {i+len(chunk)} of {len(to_fetch)}...")
        
        for attempt in range(max_retries):
            try:
                t = Ticker(chunk, asynchronous=True, max_workers=1)
                summary_detail = t.summary_detail
                asset_profile = t.asset_profile
                key_stats = t.key_stats
                
                for sym in chunk:
                    # Handle cases where dict might return a string error instead of dict
                    sd = summary_detail.get(sym, {}) if isinstance(summary_detail, dict) else {}
                    ap = asset_profile.get(sym, {}) if isinstance(asset_profile, dict) else {}
                    ks = key_stats.get(sym, {}) if isinstance(key_stats, dict) else {}
                    
                    if isinstance(sd, str): sd = {}
                    if isinstance(ap, str): ap = {}
                    if isinstance(ks, str): ks = {}
                    
                    curr = sd.get('currency', 'EUR')
                    fx = get_fx_rate(curr, fx_cache)
                    
                    mcap = sd.get('marketCap')
                    if mcap: mcap = mcap * fx
                    
                    fwd_pe = ks.get('forwardPE') or sd.get('forwardPE')
                    trl_pe = ks.get('trailingPE') or sd.get('trailingPE')
                    pb = ks.get('priceToBook')
                    country = ap.get('country', 'Unknown')
                    if curr in ['GBp', 'ZAc', 'ILA', 'IEp']:
                        if fwd_pe: fwd_pe /= 100.0
                        if pb: pb /= 100.0

                    res = {
                        'YF_Ticker': sym,
                        'Country': country,
                        'Currency': curr,
                        'MarketCap_EUR': mcap,
                        'Forward_KGV': fwd_pe,
                        'Trailing_KGV': trl_pe,
                        'KBV': pb
                    }
                    
                    # Nur zwischenspeichern, wenn echte Daten vorhanden sind, 
                    # um leere Caches durch Rate-Limits zu verhindern
                    if mcap or fwd_pe or trl_pe or pb:
                        financials_cache[sym] = res
                    else:
                        print(f"  Warning: No valid data for {sym}, not caching to allow retry.")
                        
                # Save progress
                with open(CACHE_FINANCIALS_FILE, 'w') as f:
                    json.dump(financials_cache, f)
                with open(FX_CACHE_FILE, 'w') as f:
                    json.dump(fx_cache, f)
                    
                time.sleep(3) # Längere Pause zwischen den Chunks (Rate-Limit Vermeidung)
                break # Success, break retry loop
                
            except Exception as e:
                print(f"Error on chunk {i} (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(15 * (attempt + 1))
        else:
            print(f"Failed to fetch chunk {i} after {max_retries} attempts. Skipping.")
            
    # Merge and save
    final_rows = []
    for _, row in valid_df.iterrows():
        sym = row['YF_Ticker']
        data = financials_cache.get(sym)
        if data:
            row_dict = row.to_dict()
            row_dict.update(data)
            final_rows.append(row_dict)
            
    final_df = pd.DataFrame(final_rows)
    final_df.to_csv(RAW_DATA_FILE, index=False)
    print(f"Saved {len(final_df)} records to data/processed/valuation_raw_data.csv")

if __name__ == "__main__":
    main()
