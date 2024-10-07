from .database import Database
import json

db = Database(
    'localhost',
    'root',
    'EDscMIJndts4lAo8',
    'monitoring_system'
)


def fetch_waste_bin_levels():
    global db
    sql = "SELECT * FROM waste_bins"
    rows = db.fetch(sql)
    if rows:
        return rows
    