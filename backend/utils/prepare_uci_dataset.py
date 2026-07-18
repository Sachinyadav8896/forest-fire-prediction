import pandas as pd

# Read the original UCI dataset
df = pd.read_csv("../dataset/raw/fire_data.csv")

# Create binary target column
df["fire_occurred"] = (df["area"] > 0).astype(int)

# Rename columns to match the ML project
df.rename(columns={
    "temp": "temperature",
    "RH": "humidity",
    "wind": "wind_speed",
    "rain": "rainfall"
}, inplace=True)

# Save processed dataset
df.to_csv("../dataset/processed/fire_data_processed.csv", index=False)

print("Dataset prepared successfully!")
print(df.head())