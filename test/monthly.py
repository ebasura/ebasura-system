import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV data into a DataFrame
df = pd.read_csv('waste_data.csv')

# Convert timestamp column to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Extract month and year
df['month_year'] = df['timestamp'].dt.to_period('M')

# Group by month_year and waste type, then count occurrences
monthly_data = df.groupby(['month_year', 'waste_type_id']).size().reset_index(name='count')

# Pivot the data for plotting
pivot_data = monthly_data.pivot(index='month_year', columns='waste_type_id', values='count').fillna(0)

# Plotting
plt.figure(figsize=(12, 6))

# Plot each waste type
for waste_type in pivot_data.columns:
    plt.plot(pivot_data.index.astype(str), pivot_data[waste_type], label=f'Waste Type {waste_type}')

# Formatting
plt.title('Monthly Waste Segregation')
plt.xlabel('Month-Year')
plt.ylabel('Count')
plt.legend(title='Waste Type')
plt.grid(True)
plt.xticks(rotation=45)  # Rotate date labels for better readability
plt.tight_layout()

# Show plot
plt.show()
