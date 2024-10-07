import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV data into a DataFrame
df = pd.read_csv('waste_data.csv')

# Convert timestamp column to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Extract date only (no time) for aggregation
df['date'] = df['timestamp'].dt.date

# Group by date and waste type, then count occurrences
daily_data = df.groupby(['date', 'waste_type_id']).size().reset_index(name='count')

# Pivot the data for plotting
pivot_data = daily_data.pivot(index='date', columns='waste_type_id', values='count').fillna(0)

# Plotting
plt.figure(figsize=(12, 6))

# Plot each waste type
for waste_type in pivot_data.columns:
    plt.plot(pivot_data.index, pivot_data[waste_type], label=f'Waste Type {waste_type}')

# Formatting
plt.title('Daily Waste Segregation')
plt.xlabel('Date')
plt.ylabel('Count')
plt.legend(title='Waste Type')
plt.grid(True)
plt.xticks(rotation=45)  # Rotate date labels for better readability
plt.tight_layout()

# Show plot
plt.show()
