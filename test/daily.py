import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV data into a DataFrame
df = pd.read_csv('waste_data.csv')

# Convert timestamp column to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Define the specific day you're interested in
specific_day = '2024-09-03'  # Format: 'YYYY-MM-DD'

# Filter the data for the specific day
daily_data = df[df['timestamp'].dt.date == pd.to_datetime(specific_day).date()]

# Extract hour from the timestamp
daily_data['hour'] = daily_data['timestamp'].dt.hour

# Group by hour and waste type, then count occurrences
hourly_data = daily_data.groupby(['hour', 'waste_type_id']).size().reset_index(name='count')

# Pivot the data for plotting
pivot_data = hourly_data.pivot(index='hour', columns='waste_type_id', values='count').fillna(0)

# Plotting
plt.figure(figsize=(12, 6))

# Plot each waste type
for waste_type in pivot_data.columns:
    plt.plot(pivot_data.index, pivot_data[waste_type], label=f'Waste Type {waste_type}')

# Formatting
plt.title(f'Waste Segregation on {specific_day}')
plt.xlabel('Hour of the Day')
plt.ylabel('Count')
plt.legend(title='Waste Type')
plt.grid(True)
plt.xticks(range(24))  # Ensure all hours are shown on the x-axis
plt.tight_layout()

# Show plot
plt.show()
