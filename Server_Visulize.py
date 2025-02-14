from flask import Flask, request, jsonify
from flask_socketio import SocketIO
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import collections

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store latest system stats (keeping last 100 records)
history = collections.deque(maxlen=100)

@app.route("/data", methods=["POST"])
def receive_data():
    data = request.json
    history.append(data)
    socketio.emit("update", data)  # Send data to frontend
    return jsonify({"status": "received"}), 200

# Dash app setup
dash_app = dash.Dash(__name__, server=app, routes_pathname_prefix="/dashboard/")

dash_app.layout = html.Div([
    html.H1("🚀 Raspberry Pi Monitoring Dashboard", style={"textAlign": "center"}),
    
    # CPU Graph
    dcc.Graph(id="cpu-graph"),
    
    # Memory Graph
    dcc.Graph(id="memory-graph"),
    
    # Disk Usage Graph
    dcc.Graph(id="disk-graph"),
    
    # Network Graph (Bytes Sent & Received)
    dcc.Graph(id="network-graph"),
    
    # Malicious Activity Bar
    html.Div([
        html.H3("🔴 Malicious Activity Detector", style={"textAlign": "center"}),
        dcc.Graph(id="malicious-activity-bar")
    ], style={"width": "50%", "margin": "auto"}),

    dcc.Interval(id="interval", interval=1000, n_intervals=0)  # Updates every 1 sec
])

# Update all graphs dynamically
@dash_app.callback(
    [
        Output("cpu-graph", "figure"),
        Output("memory-graph", "figure"),
        Output("disk-graph", "figure"),
        Output("network-graph", "figure"),
        Output("malicious-activity-bar", "figure"),
    ],
    Input("interval", "n_intervals")
)
def update_graphs(n):
    if not history:
        return [{} for _ in range(5)]

    x_data = list(range(len(history)))

    # Extracting data for each graph
    cpu_usage = [d["cpu_usage"] for d in history]
    memory_usage = [d["memory_usage"] for d in history]
    disk_usage = [d["disk_usage"] for d in history]
    network_sent = [d["network_sent"] for d in history]
    network_received = [d["network_received"] for d in history]
    last_cpu = history[-1]["cpu_usage"]

    return [
        {
            "data": [go.Scatter(x=x_data, y=cpu_usage, mode="lines+markers", name="CPU Usage", line=dict(color="red"))],
            "layout": go.Layout(title="🖥 CPU Usage", xaxis={"title": "Time"}, yaxis={"title": "CPU %"}, template="plotly_dark")
        },
        {
            "data": [go.Scatter(x=x_data, y=memory_usage, mode="lines+markers", name="Memory Usage", line=dict(color="blue"))],
            "layout": go.Layout(title="💾 Memory Usage", xaxis={"title": "Time"}, yaxis={"title": "Memory %"}, template="plotly_dark")
        },
        {
            "data": [go.Scatter(x=x_data, y=disk_usage, mode="lines+markers", name="Disk Usage", line=dict(color="green"))],
            "layout": go.Layout(title="📀 Disk Usage", xaxis={"title": "Time"}, yaxis={"title": "Disk %"}, template="plotly_dark")
        },
        {
            "data": [
                go.Scatter(x=x_data, y=network_sent, mode="lines", name="Bytes Sent", line=dict(color="purple")),
                go.Scatter(x=x_data, y=network_received, mode="lines", name="Bytes Received", line=dict(color="orange"))
            ],
            "layout": go.Layout(title="📡 Network Traffic", xaxis={"title": "Time"}, yaxis={"title": "Bytes"}, template="plotly_dark")
        },
        {
            "data": [go.Bar(x=["Malicious Activity"], y=[1 if last_cpu > 60 else 0], marker=dict(color="red" if last_cpu > 60 else "green"))],
            "layout": go.Layout(title="⚠️ Malicious Activity Indicator", xaxis={"title": ""}, yaxis={"title": "Risk Level"}, template="plotly_dark")
        }
    ]

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
