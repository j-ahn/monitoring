# -*- coding: utf-8 -*-
"""
Created on Sat Nov 26 12:56:22 2022

@author: ahnjiw
"""

import numpy as np

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default='browser'

import flask
from users import users_info
user_pwd, user_names = users_info()
_app_route = '/'
    
import pandas as pd
import pyproj
import geopandas as gpd
import shapely.geometry

# BNMA Colors
bmao = '#f7923a'
bmar = '#ee3b34'
bmab = '#004890'

# Convert Peak Downs co-ordinates to WGS84
def convert(x, y):
    mycrs = open(r"PDMG.prj", "r").read()
    
    inproj = pyproj.crs.CRS(mycrs)
    outproj = 4326
    
    #create transformation
    proj = pyproj.Transformer.from_crs(inproj, outproj, always_xy=True)
    
    # calculate new location
    x2,y2 = proj.transform(x, y)
    return x2, y2

def shapefiles(shapefile, label, color):
    # open a zipped shapefile with the zip:// pseudo-protocol
    geo_df = gpd.read_file(shapefile)
    
    lats = []
    lons = []
    
    for feature in geo_df.geometry:
        if isinstance(feature, shapely.geometry.linestring.LineString):
            linestrings = [feature]
        elif isinstance(feature, shapely.geometry.multilinestring.MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        for linestring in linestrings:
            x, y = linestring.xy
            lats = np.append(lats, y)
            lons = np.append(lons, x)
            lats = np.append(lats, None)
            lons = np.append(lons, None)
            
    trace = go.Scattermapbox(lat=lats, lon=lons, mode='lines', name=label, line=dict(width=1, color=color), hoverinfo='skip')
    return trace

def PlotlyFigures():
    # ________________________________________________________________________________________________________________________________________________________________
    # Figure 1
    # ________________________________________________________________________________________________________________________________________________________________
    
    MAPBOX_TOKEN = "pk.eyJ1Ijoiaml3b29haG45NyIsImEiOiJjbGF3M2U3ZTMwYm9hM3ZueDdhOTdxNG51In0.TY33vcqBrE1QfvEq6qDuCg"
    layout1 = go.Layout(title = 'GNSS Map', 
                        mapbox={'style':'basic', 
                                'accesstoken' : MAPBOX_TOKEN, 
                                'zoom' : 15})
    figure1 = go.Figure(layout=layout1)
            
    # Empty lists for appending
    SITES, LONGS, LATS, VS, TARPS = [], [], [], [], []


    # ________________________________________________________________________________________________________________________________________________________________
    # Figure 2
    # ________________________________________________________________________________________________________________________________________________________________
    
    # Create blank figure
    layout2 = go.Layout(title = 'GNSS Graph',
                       xaxis={'title' : 'Date'},
                       yaxis = {'title' : 'Average 7 Day Velocity (mm/d)'},
                       yaxis2 = {'title' : 'Peak Particle Velocity (mm/s)',
                                 'overlaying' : 'y',
                                 'side' : 'right'},
                       template='simple_white')
    figure2 = go.Figure(layout=layout2)
    
    
    # ________________________________________________________________________________________________________________________________________________________________
    # Data processing
    # ________________________________________________________________________________________________________________________________________________________________

    nums = ['00', '01', '02', '03', '04', '05', '06', '07', '09', '10', '11', '12', '13', '14']
    
    # GNSS Data
    for num in nums:
        site = 'SITE_' + num
        url = "http://gnssmonitoring.com.au/unitzero/peakdowns/processed_data/PD_UNITZERO_{0}/Download_12HRLY.csv".format(num)
        
        # read csv as dataframe
        df_temp = pd.read_csv(url, skipinitialspace=True)
        df_temp['ET'] = pd.to_datetime(df_temp['ET'], dayfirst=True)
        trace = go.Scatter(x=df_temp['ET'], y=df_temp['AVG_7DAY_3D_VELOCITY'],
                           name=site, mode='lines', yaxis='y1')
        figure2.add_trace(trace)

        # Pull out most recent data points
        x, y, v = df_temp.iloc[-1,1], df_temp.iloc[-1,2], df_temp.iloc[-1,16]
        long, lat = convert(x,y)
        
        SITES.append(site)
        LONGS.append(long)
        LATS.append(lat)
        VS.append(round(v,3))
        
        TARP = 'rgb(0, 255, 0)'
        for i, c in zip([1, 5, 10],['rgb(255, 165, 0)', 'rgb(255, 0, 0)', 'rgb(255, 0, 255)']):
            if v > i:
                TARP = c
        TARPS.append(TARP)
        trace1 = go.Scattermapbox(lat=[lat], lon=[long], name=site, text="{0:.3f} mm/s".format(v), mode='markers', marker=go.scattermapbox.Marker(size=20, color=TARP))
        figure1.add_trace(trace1)
    
    # BLAST MONITORING
    df_blast = pd.read_csv('https://raw.githubusercontent.com/j-ahn/monitoring/main/BlastVibrations.csv')
    df_blast['Date'] = pd.to_datetime(df_blast['Date'], dayfirst=True)
    for ew, c in zip(['1N Endwall', '1S Endwall'],['Blue', 'Red']):
        trace2 = go.Scatter(x=df_blast['Date'], y=df_blast[ew],
                            text=df_blast['Blast ID'], 
                            hovertemplate = "<br>".join([
                                "Date: %{x}",
                                "Blast: %{text}",
                                "PPV: %{y} mm/s"]),
                            name=ew, mode='markers', yaxis='y2', marker_color = c)
        figure2.add_trace(trace2)

    traceshp1 = shapefiles('https://github.com/j-ahn/monitoring/blob/eabb940a140e7a94aec373e0ddfc9a652bc37988/CONTOURS.zip?raw=true', 'Topographic Contours', 'rgb(200, 200, 200)')
    traceshp2 = shapefiles('https://github.com/j-ahn/monitoring/blob/main/FAULTS.zip?raw=true', '1S EW Faults', 'rgb(255, 0, 0)')
    figure1.add_trace(traceshp1)
    figure1.add_trace(traceshp2)
    
    figure1.update_mapboxes(center = {'lat' : np.mean(LATS), 'lon' : np.mean(LONGS)})
    
    figure1.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    figure2.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    
    return figure1, figure2
        
# Colors
bmao = '#f7923a'
bmar = '#ee3b34'
bmab = '#004890'
bkgr = '#f8f5f0'
    
# Initiate the app
external_stylesheets = [dbc.themes.SANDSTONE]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server
app.title = 'PDM Corridor Monitoring'

# Create a login route
@app.server.route('/login', methods=['POST'])
def route_login():
    data = flask.request.form
    username = data.get('username')
    password = data.get('password')

    if username not in user_pwd.keys() or  user_pwd[username] != password:
        return flask.redirect('/login')
    else:

        # Return a redirect with
        rep = flask.redirect(_app_route)

        # Here we just store the given username in a cookie.
        # Actual session cookies should be signed or use a JWT token.
        rep.set_cookie('custom-auth-session', username)
        return rep
    
# create a logout route
@app.server.route('/logout', methods=['POST'])
def route_logout():
    # Redirect back to the index and remove the session cookie.
    rep = flask.redirect('/login')
    rep.set_cookie('custom-auth-session', '', expires=0)
    return rep

# App HTML layout
styledict = {'display':'inline-block','vertical-align':'left', 'margin-top':'10px','margin-left':'20px','font-size':10,'font-family':'Verdana','textAlign':'center'}

htmlcent = {'text-align':'center'}
htmlright = {'text-align':'right'}

# Simple dash component login form.
login_form = html.Div(
    [
        html.Form(
            [
                dbc.Row(
                    [
                        dbc.Col(dcc.Input(placeholder="username", name="username", type="text",style={'height' : '35px', 'width': '100px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'middle'})),
                        dbc.Col(dcc.Input(placeholder="password", name="password",type="password",style={'height' : '35px', 'width': '100px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'middle'})),
                        dbc.Col(dbc.Button("Login", type="submit", color="success"))
                    ]
                    )
            ],
            action="/login",
            method="post",
        )
    ]
)

# Header
header = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(
                            id="logo",
                            src="https://raw.githubusercontent.com/j-ahn/misc/main/logo.png",
                            height="65px",
                        ),
                        md="auto",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.H3([
                                        html.Span("PDM ", style={'color':bmao}),
                                        html.Span("Corridor ", style={'color':bmar}),
                                        html.Span("Monitoring ", style={'color':bmab})
                                        ]),
                                    html.H5("BMA Geotechnical Services"),
                                ],
                                id="app-title"
                            )
                        ],
                        md='auto',
                        align="center",
                    ),
                    dbc.Col([html.Div([dbc.Button('Update Graph', id='update_button', n_clicks=0, color="primary", style={"margin": "5px"})], style=htmlcent)]),
                    dbc.Col(
                        [
                            html.Div(id='custom-auth-frame-1',
                                       style={
                                              'textAlign': 'center',
                                       }
                                       ),
                        ],
                        md='auto',
                        align='right'
                    )
                ],
                align="center",
            ),
        ],
        fluid=True,
    ),
    dark=False,
    sticky="top",
)

card1 = dbc.Card(color='light',children=[dbc.CardHeader("Map", style={'font-weight':'bold'}),
                dcc.Graph('mapbox',style={'height': '80vh'},
                          config={'displayModeBar': True, 
                                  'displaylogo':False,
                                  'toImageButtonOptions': {'format': 'svg','filename': 'runout_calculator'},
                                  'modeBarButtonsToRemove':['hoverClosestPie']})])
        
card2 = dbc.Card(color='light',children=[dbc.CardHeader("Graph", style={'font-weight':'bold'}),
                        dcc.Graph('graph',style={'height': '80vh'},
                                  config={'displayModeBar': True, 
                                          'displaylogo':False,
                                          'toImageButtonOptions': {'format': 'svg','filename': 'runout_calculator'},
                                          'modeBarButtonsToRemove':['hoverClosestPie']})])

app.layout = dbc.Container(
    [
        header,
        
        html.Hr(),
        
        dbc.Row([
            dbc.Col(card1, md=6),
            dbc.Col(card2, md=6)
        ]),
        
        html.Hr(),
        
        html.Div(id='markdown-frame')
    ],
    fluid=True
)


@app.callback(
    Output('mapbox', 'figure'),
    Output('graph', 'figure'),
    Output('custom-auth-frame-1', 'children'),
    Input('update_button', 'n_clicks'),
)


def update_graph(n_clicks):
    
    session_cookie = flask.request.cookies.get('custom-auth-session')
    
    if not session_cookie:
        # If there's no cookie we need to login.
        # Initiate plotly figure
        fig1 = go.Figure()
        fig1.update_layout(template='simple_white', paper_bgcolor=bkgr)
        fig1.update_layout(
        title=dict(text='Please log in',x=0.5,y=0.95,
                   font=dict(family="Arial",size=20,color='#000000')
                   )
        )
        fig2 = go.Figure()
        fig2.update_layout(template='simple_white', paper_bgcolor=bkgr)
        fig2.update_layout(
        title=dict(text='Please log in',x=0.5,y=0.95,
                   font=dict(family="Arial",size=20,color='#000000')
                   )
        )
        
        return [fig1, fig2, login_form]
    else:
        
        logout_output = html.Form(
            [
                dbc.Row(
                    [
                        dbc.Col(dbc.Button("Logout", type="submit", color="danger"))
                    ]
                    )
            ],
            action="/logout",
            method="post",
        )                      

        if n_clicks >= 0:
            
            print(n_clicks)

            fig1, fig2 = PlotlyFigures()
                            
        return [fig1, fig2, logout_output]

if __name__ == '__main__':
    app.run_server()
