from flask import Flask, render_template
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd

# Create the Flask app
server = Flask(__name__)


# Load data
df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')

# Create Dash app and associate it with the Flask app
app = Dash(__name__, server=server, url_base_pathname='/dash/')

# Define the layout of the Dash app
app.layout = html.Div([
    dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
    dcc.Graph(id='graph-content'),
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0),
])

# Define the callback to update the graph
years = df['year'].unique()

@app.callback(
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value'),
    Input('interval-component', 'n_intervals')
)
def update_graph(value, n):
    # Get the year based on the interval
    year = years[n % len(years)]  # Loop through years
    dff = df[(df.country == value) & (df.year <= year)]  # Filter data up to current year
    
    # Create a line chart that updates year by year
    fig = px.line(dff, x='year', y='pop', title=f'Population of {value} up to {year}')
    fig.update_layout(transition_duration=500)
    
    return fig

# Run the combined Flask and Dash app
if __name__ == '__main__':
    server.run(host='0.0.0.0', port=5000, debug=True)
