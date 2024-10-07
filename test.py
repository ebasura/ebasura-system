from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

# Sample data
waste_data = [{"waste_data_id":2,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/139x100.png\/dddddd\/000000","timestamp":"2024-03-02 01:17:07","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":11,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/184x100.png\/ff4444\/ffffff","timestamp":"2024-04-27 13:54:59","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":21,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/187x100.png\/5fa2dd\/ffffff","timestamp":"2024-02-23 08:45:37","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":22,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/208x100.png\/dddddd\/000000","timestamp":"2024-01-25 03:29:14","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":27,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/217x100.png\/ff4444\/ffffff","timestamp":"2024-07-02 00:02:22","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":33,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/113x100.png\/ff4444\/ffffff","timestamp":"2023-10-02 02:28:47","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":34,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/101x100.png\/dddddd\/000000","timestamp":"2023-09-19 16:23:27","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":38,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/223x100.png\/ff4444\/ffffff","timestamp":"2023-11-29 22:08:49","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":43,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/195x100.png\/ff4444\/ffffff","timestamp":"2024-06-16 11:50:23","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"},{"waste_data_id":44,"bin_id":1,"waste_type_id":1,"image_url":"http:\/\/dummyimage.com\/115x100.png\/5fa2dd\/ffffff","timestamp":"2024-05-04 08:26:05","name":"Recyclable","bin_name":"Recyclable","capacity":"100.00","current_fill_level":"0.00","last_update":"2024-09-03 18:34:30"}]


def get_monthly_data(data):
    # Initialize data structure for months
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    recyclable_data = [0] * 12
    non_recyclable_data = [0] * 12

    for item in data:
        timestamp = datetime.strptime(item["timestamp"], "%Y-%m-%d %H:%M:%S")
        month_index = timestamp.month - 1
        if item["name"] == "Recyclable":
            recyclable_data[month_index] += 1
        else:
            non_recyclable_data[month_index] += 1

    return {
        "Recyclable": recyclable_data,
        "Non-Recyclable": non_recyclable_data
    }

@app.route('/monthly_waste_segregated', methods=['GET'])
def monthly_waste_segregated():
    data = get_monthly_data(waste_data)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
