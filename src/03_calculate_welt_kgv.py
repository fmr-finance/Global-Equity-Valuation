import pandas as pd
import numpy as np
import os

REGION_MAPPING = {
    'Holdings_details_Morningstar_Total_Stock_Market_ETF': 'Nordamerika',
    'XIC_holdings': 'Nordamerika',
    'EXSA_holdings': 'Europa',
    'Fondszusammensetzung_Amundi Japan TOPIX II UCITS ETF JPY Dist_FR0010377028_16_09_2026': 'Japan',
    'IS3N_holdings': 'Entwicklungsländer',
    'Constituent_LU0659578842': 'Singapore',
    'Holding details_19': 'Australien'
}

def calculate_harmonic_mean(df, metric_col, weight_col='Weight'):
    valid_df = df.dropna(subset=[metric_col, weight_col]).copy()
    if valid_df.empty: return np.nan
    valid_df[metric_col] = pd.to_numeric(valid_df[metric_col], errors='coerce')
    valid_df = valid_df[valid_df[metric_col] > 0]
    
    if 'KGV' in metric_col:
        valid_df[metric_col] = valid_df[metric_col].clip(lower=5.0)
    elif 'KBV' in metric_col:
        valid_df[metric_col] = valid_df[metric_col].clip(lower=0.1)
        
    if valid_df.empty: return np.nan
    total_weight = valid_df[weight_col].sum()
    if total_weight == 0: return np.nan
    valid_df['Normalized_Weight'] = valid_df[weight_col] / total_weight
    denominator = (valid_df['Normalized_Weight'] / valid_df[metric_col]).sum()
    return 1 / denominator if denominator > 0 else np.nan

def calculate_coverage(df, metric_col, weight_col='Weight'):
    valid_df = df.dropna(subset=[metric_col]).copy()
    valid_df[metric_col] = pd.to_numeric(valid_df[metric_col], errors='coerce')
    valid_df = valid_df[valid_df[metric_col] > 0]
    total_weight = df[weight_col].sum()
    if total_weight == 0: return 0
    return (valid_df[weight_col].sum() / total_weight) * 100

def compute_metrics(sub, name_prefix, weight_col='Weight', drop_duplicates=False):
    if drop_duplicates and 'Clean_Name' in sub.columns:
        sub = sub.drop_duplicates(subset=['Clean_Name']).copy()
        
    fwd_pe = calculate_harmonic_mean(sub, 'Forward_KGV', weight_col)
    fwd_cov = calculate_coverage(sub, 'Forward_KGV', weight_col)
    
    trl_pe = calculate_harmonic_mean(sub, 'Trailing_KGV', weight_col)
    trl_cov = calculate_coverage(sub, 'Trailing_KGV', weight_col)
    
    kbv = calculate_harmonic_mean(sub, 'KBV', weight_col)
    kbv_cov = calculate_coverage(sub, 'KBV', weight_col)
    
    # Coverage of market cap data within the ETF allocation
    mcap_cov = calculate_coverage(sub, 'MarketCap_EUR', 'Weight')
    if mcap_cov > 0:
        total_mcap = sub['MarketCap_EUR'].sum()
        extra_mcap = total_mcap / (mcap_cov / 100)
    else:
        extra_mcap = np.nan
        
    return {
        'Kategorie': name_prefix,
        'Trailing KGV': trl_pe,
        'Abdeckung Trailing KGV (%)': trl_cov,
        'Forward KGV': fwd_pe,
        'Abdeckung Forward KGV (%)': fwd_cov,
        'KBV': kbv,
        'Abdeckung KBV (%)': kbv_cov,
        'Extrapoliertes Market Cap (Mrd. EUR)': extra_mcap / 1e9 if pd.notna(extra_mcap) else np.nan
    }

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_data_path = os.path.join(base_dir, "data", "processed", "valuation_raw_data.csv")
    dashboard_path = os.path.join(base_dir, "results", "welt_kgv_dashboard.csv")

    try:
        # 1. Load the fetched raw data
        df = pd.read_csv(raw_data_path)
    except:
        print("valuation_raw_data.csv not found!")
        return
        
    # Map regions
    df['Region'] = df['ETF'].map(REGION_MAPPING).fillna('Unbekannt')
        
    results = []
    
    # 1. Gesamtwerte für die Welt
    results.append(compute_metrics(df, 'Gesamt: Welt', weight_col='MarketCap_EUR', drop_duplicates=True))
    
    # 2. Breakdown by Region
    for region in ['Nordamerika', 'Europa', 'Japan', 'Entwicklungsländer', 'Singapore', 'Australien']:
        sub = df[df['Region'] == region]
        if not sub.empty:
            results.append(compute_metrics(sub, f'Region: {region}', weight_col='MarketCap_EUR', drop_duplicates=True))

    # 3. Breakdown by ETF
    for etf in df['ETF'].unique():
        sub = df[df['ETF'] == etf]
        results.append(compute_metrics(sub, f'ETF: {etf}', weight_col='Weight', drop_duplicates=False))

    # 4. Breakdown by Country
    df['Country'] = df['Country'].fillna('Unknown')
    for country in sorted(df['Country'].unique()):
        sub = df[df['Country'] == country]
        if sub.empty: continue
        results.append(compute_metrics(sub, f'Country: {country}', weight_col='MarketCap_EUR', drop_duplicates=True))

    out_df = pd.DataFrame(results)
    print(out_df.to_string(index=False))
    try:
        out_df.to_csv(dashboard_path, index=False, sep=';', decimal=',')
        print(f"\nDashboard saved to {dashboard_path}")
    except PermissionError:
        fallback_path = dashboard_path.replace('.csv', '_neu.csv')
        out_df.to_csv(fallback_path, index=False, sep=';', decimal=',')
        print(f"\nDatei war geöffnet. Dashboard saved to {fallback_path} stattdessen.")

if __name__ == "__main__":
    main()
