# Global Equity Valuation

## Objective
Estimation of the aggregate forward P/E ratio, trailing P/E ratio, and Price-to-Book (P/B) ratio of the global equity market using a simplified index structure.

## Research Question
How is the global stock market currently valued across different geographic regions (e.g., North America, Europe, Japan, Emerging Markets, Australia) based on a bottom-up aggregation of individual ETF constituents?

## Methodology
The project calculates the true weighted valuation metrics for a globally diversified ETF portfolio. To accurately aggregate valuation ratios on an index level, the **harmonic mean** is applied. Outlier clipping is used (P/E >= 5, P/B >= 0.1) to prevent extreme mathematical distortion from data errors.

The pipeline executes the following steps:
1. **Parsing (`01_parse_holdings.py`)**: Automatically detects and extracts holdings from various ETF provider CSV/Excel files, unifying them and resolving dual-listings.
2. **Data Fetching (`02_fetch_financials.py`)**: Uses asynchronous requests to pull live financial metrics for each mapped ticker.
3. **Aggregation (`03_calculate_welt_kgv.py`)**: Computes the harmonic mean of the valuations grouped by region, country, and specific ETF.
4. **Visualization (`04_generate_map.py`)**: Generates an interactive choropleth world map to visualize regional trailing P/E valuations.

## Data
- **Holdings**: Extracted from user-provided ETF composition files in `data/raw/`.
- **Data source**: Yahoo Finance / `yfinance` & `yahooquery` (used to pull live Market Cap, Trailing P/E, Forward P/E, and Price/Book).
- **Mapping**: An ISIN-to-Ticker dictionary (`cache_mapping.json`) serves to translate ETF constituents into Yahoo Finance compatible symbols.

## Results
The primary output is a detailed CSV dashboard (`results/welt_kgv_dashboard.csv`) providing a valuation breakdown across:
- **Global Aggregate (Gesamt: Welt)**
- **Regional Aggregates** (North America, Europe, Japan, Emerging Markets, Singapore, Australia)
- **Country-level Aggregates**

In addition, an interactive global heatmap (`results/welt_kgv_map.html`) visually reflects the trailing P/E ratio of each evaluated country.

## Limitations
- **Ticker Mapping**: Constituents lacking a mapped Yahoo Finance ticker in the cache are excluded from the final aggregation.
- **Data Accuracy**: Completely reliant on the accuracy of live Yahoo Finance metrics. Systemic errors in their data feeds can skew the results.
- **Coverage**: The representativeness of the "global" market depends entirely on the breadth of the ETF files supplied by the user.

## Technologies
- Python
- pandas
- NumPy
- yfinance / yahooquery
- plotly & pycountry (for spatial visualization)

---

## Setup & Usage (Quickstart)

**Prerequisites:**
```bash
pip install -r requirements.txt
```

**Run Pipeline:**
```bash
# 1. Parse your ETF holdings
python src/01_parse_holdings.py

# 2. Fetch live data from Yahoo Finance
python src/02_fetch_financials.py

# 3. Generate the valuation dashboard
python src/03_calculate_welt_kgv.py

# 4. Generate the global heatmap
python src/04_generate_map.py
```
