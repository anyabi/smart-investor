import dash
from dash import dash_table, html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

# 假设这是你的 DataFrame


title = 'Smart Investor'
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


def app_setup(df):
    app.layout = dbc.Container([
        html.H1(f"{title}", className="text-center mt-4"),  # 标题
        html.Div(id='live-time', className="text-center mb-4"),  # 动态时间显示
        dcc.Interval(id='interval-component', interval=1 * 1000, n_intervals=0),  # 1秒钟更新一次

        dash_table.DataTable(
            id='table',
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            sort_action='native',

            style_table={
                'overflowX': 'auto',
                'border': '1px solid darkgrey'
            },
            style_cell={
                'textAlign': 'left',
                'border': '1px solid grey',
                'padding': '5px'
            },
            style_header={
                'fontWeight': 'bold',
                'border': '1px solid black',
                'backgroundColor': 'lightgrey'
            },
            page_size=50
        )
    ], className="mt-5", style={'backgroundColor': '#DFFFD9'})


@app.callback(
    dash.dependencies.Output('live-time', 'children'),
    [dash.dependencies.Input('interval-component', 'n_intervals')]
)
def update_time(n):
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    df = pd.DataFrame({
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Value': [15, -10, 25],
        'Salary': [50000, 60000, 70000]
    })
    app_setup(df)
    app.run_server(debug=True)
