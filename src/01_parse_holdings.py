import pandas as pd
import os
import glob
import re

def clean_name(name):
    if pd.isna(name): return ""
    name = str(name).lower()
    name = re.sub(r'\b(co|ltd|inc|corp|group|corporation|company|limited|a|h|registered|shares|class|cl|o\.n\.|yc 1|plc|nv|ag|sa|ab|se)\b', '', name)
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    return ' '.join(name.split())

def is_header_row(row_list):
    has_identifier = False
    has_descriptive = False
    for raw_x in row_list:
        x = str(raw_x).lower().strip()
        if x == 'unnamed' or 'unnamed:' in x or x == 'nan' or x == '': continue
        if len(x) > 30: continue
        
        if 'ticker' in x or 'isin' in x or 'sedol' in x:
            has_identifier = True
        elif 'gewichtung' in x or 'weight' in x or '% of funds' in x or '% of net assets' in x:
            has_descriptive = True
        elif 'name' in x or 'holdings' in x or 'unternehmen' in x:
            if ' as of' in x or 'details' in x:
                continue
            has_descriptive = True
        elif 'sector' in x or 'sektor' in x:
            has_descriptive = True
            
    return has_identifier and has_descriptive

def find_header_row_csv(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for i in range(30):
            line = f.readline()
            if not line: break
            parts = [p.strip() for p in line.lower().split(',')]
            if is_header_row(parts): return i
            parts_semi = [p.strip() for p in line.lower().split(';')]
            if is_header_row(parts_semi): return i
    return 0

def find_header_row_excel(path):
    for engine in ['openpyxl', 'calamine']:
        for i in range(30):
            try:
                df = pd.read_excel(path, skiprows=i, nrows=1, header=None, engine=engine)
                row = df.iloc[0].tolist()
                if is_header_row(row):
                    return i
            except Exception:
                pass
    return 0

def normalize_columns(df):
    col_map = {}
    for col in df.columns:
        c = str(col).lower().strip()
        if 'ticker' in c and 'emittent' not in c:
            col_map[col] = 'Ticker'
        if 'emittententicker' in c:
            col_map[col] = 'Ticker'
        if c == 'name' or c == 'holding name' or c == 'unternehmen' or c == 'holdings' or c == 'asset name':
            col_map[col] = 'Name'
        if 'isin' in c:
            col_map[col] = 'ISIN'
        if 'sedol' in c:
            col_map[col] = 'SEDOL'
        if 'gewichtung' in c or 'weight' in c or '% of funds' in c or '% of net assets' in c:
            col_map[col] = 'Weight'
        if 'sector' in c or 'sektor' in c or 'sub-industry' in c:
            col_map[col] = 'Sector'
            
    return df.rename(columns=col_map)

def process_files(folder):
    all_data = []
    
    for file in os.listdir(folder):
        if not file.endswith(('.csv', '.xlsx')):
            continue
        if file in ['unified_holdings.csv', 'valuation_raw_data.csv', 'welt_kgv_dashboard.csv']:
            continue
            
        path = os.path.join(folder, file)
        df = None
        print(f"Processing {file}...")
        
        try:
            if file.endswith('.csv'):
                skip = find_header_row_csv(path)
                try:
                    df = pd.read_csv(path, skiprows=skip)
                except:
                    df = pd.read_csv(path, skiprows=skip, sep=';', decimal=',')
            else:
                skip = find_header_row_excel(path)
                try:
                    df = pd.read_excel(path, skiprows=skip)
                except:
                    df = pd.read_excel(path, skiprows=skip, engine='calamine')
                        
            if df is not None:
                df = normalize_columns(df)
                
                # Special cases:
                if 'Name' not in df.columns:
                    for col in df.columns:
                        c = str(col).lower()
                        if c == 'titel' or c == 'asset name' or c == 'company':
                            df.rename(columns={col: 'Name'}, inplace=True)
                            break
                            
                required = ['Name']
                if not all(r in df.columns for r in required):
                    print(f"  Skipping {file}, couldn't find required columns. Found: {df.columns.tolist()}")
                    continue
                    
                if 'Weight' in df.columns:
                    df['Weight'] = df['Weight'].astype(str).str.replace('%', '').str.replace(',', '.').str.replace('"', '').str.strip()
                    df['Weight'] = df['Weight'].str.replace('<', '').str.replace('-', '0')
                    df['Weight'] = pd.to_numeric(df['Weight'], errors='coerce')
                    if df['Weight'].sum() > 0 and df['Weight'].sum() < 2.0:
                        df['Weight'] *= 100
                else:
                    df['Weight'] = 0.0

                df['ETF'] = file.split('.')[0]
                df['Clean_Name'] = df['Name'].apply(clean_name)
                df['Is_Stoxx'] = 'EXSA' in file.upper()

                for col in ['Ticker', 'ISIN', 'SEDOL', 'Sector']:
                    if col not in df.columns:
                        df[col] = None
                        
                df = df.dropna(subset=['Name', 'Weight'])
                df = df[df['Weight'] >= 0]
                
                # Drop duplicate columns if any (caused pandas concat error earlier)
                df = df.loc[:, ~df.columns.duplicated()]
                
                all_data.append(df[['ETF', 'Is_Stoxx', 'Ticker', 'ISIN', 'SEDOL', 'Name', 'Clean_Name', 'Sector', 'Weight']])
                print(f"  Loaded {len(df)} holdings.")
                
        except Exception as e:
            print(f"  Error processing {file}: {e}")
            
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        stoxx = final_df[final_df['Is_Stoxx']].copy()
        other = final_df[~final_df['Is_Stoxx']].copy()
        
        if not stoxx.empty:
            grouped = stoxx.groupby('Clean_Name', as_index=False).agg({
                'ETF': 'first',
                'Is_Stoxx': 'first',
                'Ticker': 'first',
                'ISIN': 'first',
                'SEDOL': 'first',
                'Name': 'first',
                'Sector': 'first',
                'Weight': 'sum'
            })
            final_df = pd.concat([grouped, other], ignore_index=True)
            print(f"  Aggregated STOXX dual listings. Total rows now: {len(final_df)}")
            
        out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "unified_holdings.csv")
        final_df.to_csv(out_path, index=False)
        print(f"\nSuccessfully unified {len(final_df)} holdings into data/processed/unified_holdings.csv")
    else:
        print("\nNo data processed.")

if __name__ == "__main__":
    # Get current script dir, then point to data/raw
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder = os.path.join(base_dir, "data", "raw")
    process_files(folder)
