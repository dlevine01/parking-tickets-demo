import pandas as pd
import geopandas as gpd
import plotly.express as px  # (version 4.7.0 or higher)
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output  # pip install dash (version 2.0.0 or higher)

external_stylesheets = [
    "https://codepen.io/chriddyp/pen/bWLwgP.css",
    'https://fonts.googleapis.com/css?family=Montserrat%3A700%7COpen+Sans%3A400%2C700&ver=6.1.1',
    'https://comptroller.nyc.gov/wp-content/themes/comptroller_theme_2021/css/customColor.css?ver=1647888886',
    'https://comptroller.nyc.gov/wp-content/themes/comptroller_theme_2021/css/custom2021.css?ver=1665673425'
]

# create app
app = Dash(__name__, external_stylesheets=external_stylesheets)

# to serve online
server = app.server

# ---------- read in data and create initial state



# TODO spinner






# could this be read directly as geojson, not through geodataframe?
tracts = (
    gpd.read_file(
        'processed data/tracts_4326_w_pcts_simplified.json',
        dtype={'GEOID':'str'}
        )
    .set_index('GEOID')
)

tickets = (
    pd.read_csv(
        'processed data/tickets_by_tract_by_month_by_category.csv', 
        parse_dates=['year-month'],
        dtype={'GEOID':'str'}
        )
    .rename(columns={
        'year-month':'Issue Date',
        'category':'Violation Type'
        })
    .set_index(['GEOID','Issue Date','Violation Type'])
    ['tickets count']
    .sort_index()
)

violation_types = tickets.index.get_level_values('Violation Type').unique()

# sum by month for timeline
total_tickets_by_month = (
    tickets
    .groupby('Issue Date')
    .sum()
    .rolling(3,1,center=True).mean()
    .to_frame()
)

# total race pcts for citywide bars
total_race_pct = (
    (
        (tracts[['White','Black','Asian','Hispanic']].sum())
        /
        (tracts['Total population'].sum())
    )
    .rename('Citywide')
    .to_frame()
)

# initiate (empty) map with basemap base
# (replace with spinner?)
initial_map_fig = px.choropleth_mapbox(
    mapbox_style='carto-positron',
    zoom=9, 
    center = {"lat": 40.7, "lon": -74}
)

# initial_timeline = px.line(
#     total_tickets_by_month,
#     title=''
# )

# initial_timeline.update_layout(
#     xaxis=dict(
#         rangeslider=dict(
#             visible=True
#         ),
#         type="date"
#     )
# )

# initiate blank timeline; first callback call will fill it in
# (do I need this?)
initial_timeline = dict()


# ------------------------------------------------------------------------------
# App layout
app.layout = html.Div(id='app', children=[

    html.H1("Explore parking tickets by type"),

    html.Div(id='selector_container', children=[
    
        html.P('Select violation types:'),

        dcc.Dropdown(
            id='violation_type_selection',
            options=violation_types,
            multi=True,
            value=['Street cleaning'],
        )

    ]),

    html.Div(id='components_container', children=[

        html.Div(id='map_container', children=[

            # initiates title; first callback will overwrite this title
            # (replace with spinnner?)
            html.H6(children=['map loading...'], id='map_title'),

            # container and configuration for map figure
            dcc.Graph(
                id='map', 
                figure=initial_map_fig,
                config={
                    'displaylogo': False
                },
                style={'height':'70vh'}
            ),
        ], 
        
        # set flex 5 width (could move to external stylesheet by id)
        style={'flex':5}
        
        ),

        html.Div(id='timeline_and_bars_container', children=[

            # container and configuration for timeline
            dcc.Graph(
                id='timeline',
                figure=initial_timeline,
                config={
                    'modeBarButtonsToRemove': ['zoom_in', 'zoom_out','autoscale'],
                    'displaylogo': False
                }
            ),

            # container and configuration for race bars
            dcc.Graph(
                id='race_bar_plot', 
                figure={},
                config={
                    'displayModeBar': False,
                    'displaylogo': False
                }
            )
        ],style={'flex':3}
        )

    ],style={'display': 'flex', 'flex-direction': 'row'}
    )

])

# ------------------------------------------------------------------------------
# callbacks
# Connect the Plotly graphs with Dash Components

# to update map on selection of timeline or violation type
@app.callback(
    [Output(component_id='map_title', component_property='children'),
     Output(component_id='map', component_property='figure'),],
     #Output(component_id='map', component_property='selectedData')],
    [Input(component_id='timeline',component_property='relayoutData'),
    Input(component_id='violation_type_selection', component_property='value')]
)
def update_map(selected_timeline_area,selected_violation):
    
    # log what it's doing
    # (werkzeug might be more useful but here's a summary )
    print("called 'update_map'")
    print(f" with 'selected_violation' = {selected_violation}")
    print(f" with 'selected_timeline_area' = {selected_timeline_area}")

    # get time range from timeline, if the timeline has been selected
    # (this selects highly granular timestamps; could amke this quantum; and also slightly delay the action until mouseup)
    if selected_timeline_area is None:
        selected_timeline_area = dict()

    if 'xaxis.range[0]' in selected_timeline_area:
        selected_dates = [
            selected_timeline_area['xaxis.range[0]'], 
            selected_timeline_area['xaxis.range[1]']
        ]
    else:
        selected_dates = [
            tickets.index.get_level_values('Issue Date').min(),
            tickets.index.get_level_values('Issue Date').max()
            ]

    print(f" and 'selected_dates = {selected_dates}")

    # display the selection
    display_dates = " - ".join([pd.to_datetime(date).strftime(r'%b %Y') for date in selected_dates])

    display_violation = ', '.join([violation.capitalize() for violation in selected_violation])

    title = f'Ticket type: {display_violation} & Date range: {display_dates}'

    # subset the data
    selected_tickets = (
        tickets
        .loc[:,slice(*selected_dates),selected_violation]
        .groupby('GEOID')
        .sum()
        .reset_index()
    )

    # create and configure map fig
    fig = px.choropleth_mapbox(
        data_frame=selected_tickets,
        color='tickets count',
        geojson=tracts.geometry,
        locations='GEOID',
        color_continuous_scale='burg',
        mapbox_style='carto-positron',
        hover_data={
            'GEOID':False,
            'tickets count':':.0f'
        },
        zoom=9, 
        center = {"lat": 40.7, "lon": -74},
    )

    # customize legend
    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Tickets",
            orientation='h',
            xanchor='left',
            x=0,
            yanchor='bottom',
            y=0,
            lenmode="fraction",
            len=0.5,
            thicknessmode='fraction',
            thickness=0.035,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
    )

    # customize tract geometry shapes (hide border lines)
    fig.update_traces(
        marker_opacity=0.75,
        marker_line=dict(
            width=0,
            color='rgba(255,255,255,0)'
        )
    )


    return title, fig

# to update timeline and race bars on selection of map or violation type
@app.callback(
    [Output(component_id='race_bar_plot', component_property='figure'),
     Output(component_id='timeline', component_property='figure')],
    [Input(component_id='map', component_property='selectedData'),
     Input(component_id='map',component_property='clickData'),
     Input(component_id='violation_type_selection', component_property='value')]
)
def update_race_bars_and_timeline_from_map_selection(selected_map_area,clicked_tract,selected_violation):

    # log function call
    print("called 'update_race_bars_and_timeline_from_map_selection'")

    # get the tracts that were selected or clicked on map
    # this handles a selection first, then a click if no selection. it's a little buggy; probably it whould use the last interaction to direct the control flow)
    
    # clear selection
    selected_GEOIDs = False

    # get GEOID value(s) from selected data dict passed back from map selection/click
    if bool(selected_map_area):
        selected_GEOIDs = [i['location'] for i in selected_map_area['points']]

    elif clicked_tract:
        selected_GEOIDs = [clicked_tract['points'][0]['location']]

    if selected_GEOIDs:

        print(f" with 'tracts_selected' including {selected_GEOIDs[0] if selected_GEOIDs else 'none'}")

        # subset tracts to selection
        tracts_selected = tracts.loc[selected_GEOIDs]

        # recompute race pcts for selected tracts
        selection_race_pct = (
            (
                (tracts_selected[['White','Black','Asian','Hispanic']].sum())
                /
                (tracts_selected['Total population'].sum())
            )
            .rename('Selected area')
            .to_frame()
        )

        race_bars_data = total_race_pct.join(selection_race_pct)

        race_bars_title = 'Race and ethnicity citywide and selected area'

        # recompute timeline from selected area and selected type
        selected_area_timeline_data = (
            tickets
            .loc[selected_GEOIDs,:,selected_violation]
            .groupby('Issue Date')
            .sum()
            .rolling(3,1,center=True).mean()
            .reset_index()
        )

        timeline_title = 'Selected area'
    
    else:
        
        print(" with no selection")

        # generate empty race columns
        no_selection_race_pct = pd.DataFrame(index=['White','Black','Asian','Hispanic'],columns=[''],data=[0,0,0,0])
        
        race_bars_data = total_race_pct.join(no_selection_race_pct)

        race_bars_title = 'Race and ethnicity citywide (select area on map to compare)'

        # compute timeline from all tracts
        selected_area_timeline_data = (
            tickets
            .loc[:,:,selected_violation]
            .groupby('Issue Date')
            .sum()
            .rolling(3,1,center=True).mean()
            .reset_index()
        )

        timeline_title = 'Total citywide'

    # generate race bars from whichever data created above
    race_bars = px.bar(
        race_bars_data,
        barmode='group',
        title=race_bars_title,
        height=250,
        template='plotly_white'
    )

    race_bars.update_layout(
        margin=dict(l=20, r=20, t=100, b=10),
        yaxis_title='Percent of population',
        xaxis_title=None,
        yaxis_tickformat='.0%',
        legend_title='Area',
        font_family="'Open Sans', Helvetica, Arial, sans-serif"
    )

    # generate timeline from whichever data selected above
    timeline = px.line(
        selected_area_timeline_data,
        x='Issue Date',
        y='tickets count',
        title= timeline_title,
        height=350,
        template='plotly_white',
        hover_data={
            'Issue Date':False,
            'tickets count':'.0f'
        }
    )

    timeline.update_traces(
        hovertemplate=None
    )

    timeline.update_layout(
        xaxis=dict(
            rangeselector=dict(
                visible=True
            ),
            type="date"
        ),
        yaxis_title="Tickets",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=10),
        font_family="'Open Sans', Helvetica, Arial, sans-serif",
        hovermode='x',
    )

    timeline.update_xaxes(rangeslider_thickness = 0.08)

    return race_bars, timeline

# ------------------------------------------------------------------------------

# this serves locally 

if __name__ == '__main__':

    import os
    from werkzeug.middleware.profiler import ProfilerMiddleware

    PROF_DIR = 'profiles'

    if os.getenv("PROFILER", None):
        app.server.config["PROFILE"] = True
        app.server.wsgi_app = ProfilerMiddleware(
            app.server.wsgi_app, 
            sort_by=["cumtime"], 
            restrictions=[50],
            stream=None,
            profile_dir=PROF_DIR
        )
    app.run_server(debug=True)


