# Debug yfinance data structure
import yfinance as yf
import pandas as pd

print("=== Testing yfinance data structure ===")

# Try different download approaches
try:
    # Method 1: Standard download
    print("\n1. Standard download (1mo):")
    data1 = yf.download("AAPL", period="1mo", progress=False)
    print(f"  Type: {type(data1)}")
    print(f"  Shape: {getattr(data1, 'shape', 'N/A')}")
    print(f"  Columns: {list(data1.columns) if hasattr(data1, 'columns') else 'No columns'}")
    print(f"  Has index: {hasattr(data1, 'index')}")
    if hasattr(data1, 'head'):
        print("  First 2 rows:")
        print(data1.head(2))

    # Method 2: Specific date range
    print("\n2. Specific date range:")
    import datetime
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=30)
    data2 = yf.download("AAPL", start=start, end=end, progress=False)
    print(f"  Type: {type(data2)}")
    print(f"  Shape: {getattr(data2, 'shape', 'N/A')}")
    print(f"  Columns: {list(data2.columns) if hasattr(data2, 'columns') else 'No columns'}")
    if hasattr(data2, 'head'):
        print("  First 2 rows:")
        print(data2.head(2))

except Exception as e:
    print(f"Error: {e}")

print("\n=== Testing synthetic data structure ===")
import numpy as np
import pandas as pd

# Create synthetic data matching what we expect
dates = pd.date_range(end=datetime.datetime.now(), periods=60, freq='B')
synthetic = pd.DataFrame({
    'Open': np.random.uniform(90, 110, len(dates)),
    'High': np.random.uniform(95, 115, len(dates)),
    'Low': np.random.uniform(85, 105, len(dates)),
    'Close': np.random.uniform(90, 110, len(dates)),
    'Volume': np.random.randint(100000, 500000, len(dates))
}, index=dates)

print(f"Synthetic data shape: {synthetic.shape}")
print(f"Synthetic columns: {list(synthetic.columns)}")
print("Sample:")
print(synthetic.head(2))