import pandas as pd
import plotly.express as px
import os
import pycountry

def get_iso3(country_name):
    # Some manual overrides for common Yahoo Finance names that might differ
    overrides = {
        'United States': 'USA',
        'United Kingdom': 'GBR',
        'South Korea': 'KOR',
        'Taiwan': 'TWN',
        'Russia': 'RUS',
        'Hong Kong': 'HKG',
        'Macau': 'MAC',
        'Vietnam': 'VNM'
    }
    if country_name in overrides:
        return overrides[country_name]
        
    try:
        res = pycountry.countries.search_fuzzy(country_name)
        if res:
            return res[0].alpha_3
    except:
        return None
    return None

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dashboard_path = os.path.join(base_dir, "results", "welt_kgv_dashboard.csv")
    map_path = os.path.join(base_dir, "results", "welt_kgv_map.html")
    
    if not os.path.exists(dashboard_path):
        print(f"File not found: {dashboard_path}")
        return
        
    df = pd.read_csv(dashboard_path, sep=';', decimal=',')
    
    # Filter only country rows
    country_df = df[df['Kategorie'].str.startswith('Country: ')].copy()
    if country_df.empty:
        print("No country data found in dashboard.")
        return
        
    country_df['CountryName'] = country_df['Kategorie'].str.replace('Country: ', '')
    
    # Get ISO alpha 3 codes for plotly
    country_df['iso_alpha'] = country_df['CountryName'].apply(get_iso3)
    
    # Filter valid countries and valid KGV
    country_df = country_df.dropna(subset=['Trailing KGV'])
    
    # Optional: We could cap very high P/E values for better color scale
    # But for an interactive map, it's nice to see the actual values.
    # To prevent extreme outliers from skewing the color map, we can use color_continuous_midpoint
    # or limit the color range.
    
    # Format strings for better readability in hover
    country_df['Trailing KGV '] = country_df['Trailing KGV'].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) else "-")
    country_df['Forward KGV '] = country_df['Forward KGV'].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) else "-")
    country_df['KBV '] = country_df['KBV'].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notna(x) else "-")
    country_df['Market Cap (Mrd. €)'] = country_df['Extrapoliertes Market Cap (Mrd. EUR)'].apply(lambda x: f"{x:,.0f}".replace(',', '.') if pd.notna(x) else "-")
    
    median_pe = country_df['Trailing KGV'].median()
    vmax = country_df['Trailing KGV'].quantile(0.95) # 95th percentile to cut off extreme outliers
    
    # Create the choropleth map
    fig = px.choropleth(
        country_df, 
        locations="iso_alpha",
        color="Trailing KGV",
        hover_name="CountryName",
        hover_data={
            'iso_alpha': False,
            'Trailing KGV': False,
            'Trailing KGV ': True,
            'Forward KGV ': True,
            'KBV ': True,
            'Market Cap (Mrd. €)': True
        },
        color_continuous_scale=px.colors.sequential.YlOrRd,
        range_color=(0, vmax),
        title="Weltweite Bewertung: Trailing KGV nach Land<br><sup><i>ℹ️ Interaktive Karte: Fahre mit der Maus über die Länder, um Details zu sehen. Zoomen und Verschieben ist möglich.</i></sup>",
        labels={'Trailing KGV': 'Trailing KGV Skala'}
    )
    
    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'),
        margin=dict(t=80) # Add a bit more margin at the top for the subtitle
    )
    
    fig.write_html(map_path)
    print(f"Map successfully generated and saved to {map_path}")

if __name__ == '__main__':
    main()
