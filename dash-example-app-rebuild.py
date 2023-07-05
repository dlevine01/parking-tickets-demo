import pandas as pd
import geopandas as gpd
import plotly.express as px  
import plotly.graph_objects as go
from dash import Dash, Patch, dcc, html, Input, Output  # Dash > 2.9
import numpy as np
import json

external_stylesheets = [
    "https://codepen.io/chriddyp/pen/bWLwgP.css",
    'https://fonts.googleapis.com/css?family=Montserrat%3A700%7COpen+Sans%3A400%2C700&ver=6.1.1',
    'https://comptroller.nyc.gov/wp-content/themes/comptroller_theme_2021/css/customColor.css?ver=1647888886',
    'https://comptroller.nyc.gov/wp-content/themes/comptroller_theme_2021/css/custom2021.css?ver=1665673425'
]

FIG_DISPLAY_CONFIG = {'displaylogo': False}
INITIAL_VIOLATION_TYPE = 'Street cleaning'

# create app
app = Dash(__name__, external_stylesheets=external_stylesheets)

print('initiate app')

# to serve online
server = app.server

# ---------- read in data and create initial state

#----- load data

tracts = pd.read_csv(
    'processed data/tracts_data.csv',
    dtype={'GEOID':'str'}
).set_index('GEOID')

with open('processed data/tract geometry - simplified.json', 'r') as geojson_file:
    tracts_geometry = json.load(geojson_file)
# TODO read this geojson directly into the fontend, without passing it through this laoyout object. not simple to do, though.

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

#----- summarize initial data
# sum by month for timeline
total_tickets_by_month = (
    tickets
    .loc[:,:,INITIAL_VIOLATION_TYPE]
    .groupby('Issue Date')
    .sum()
    .rolling(3,1,center=True).mean()
    .reset_index()
)

# sum by tract for map
total_tickets_by_tract = (
    tickets
    .loc[:,:,INITIAL_VIOLATION_TYPE]
    .groupby('GEOID')
    .sum()
    .reindex_like(tracts)
    .fillna(0)
    .astype(int)
    .reset_index()
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

# generate empty race columns
no_selection_race_pct = pd.DataFrame(index=['White','Black','Asian','Hispanic'],columns=['Selected area'],data=[0,0,0,0])

race_bars_data = total_race_pct.join(no_selection_race_pct)

NO_SELECTION_RACE_BARS_TITLE = 'Race and ethnicity citywide (select area on map to compare)'
race_bars_title = NO_SELECTION_RACE_BARS_TITLE


#----- initiate figures

# create and configure map fig
map_fig = px.choropleth_mapbox(
    data_frame=total_tickets_by_tract, # can this be blank and filled by first fire of the callback?
    color='tickets count',
    geojson=tracts_geometry,
    locations='GEOID',
    featureidkey='properties.GEOID',
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
map_fig.update_layout(
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
map_fig.update_traces(
    marker_opacity=0.75,
    marker_line=dict(
        width=0,
        color='rgba(255,255,255,0)'
    )
)

# create and configure timeline fig

timeline_fig = px.line(
    total_tickets_by_month,
    x='Issue Date',
    y='tickets count',
    title='',
    height=350,
    template='plotly_white',
    hover_data={
        'Issue Date':False,
        'tickets count':'.0f'
    }
)

timeline_fig.update_traces(
    hovertemplate=None
)

timeline_fig.update_layout(
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
    modebar_remove=['zoom_in', 'zoom_out','autoscale']
)

timeline_fig.update_xaxes(rangeslider_thickness = 0)



# create and configure race bars fig

race_bars_fig = px.bar(
    race_bars_data,
    barmode='group',
    title=race_bars_title,
    height=250,
    template='plotly_white'
)

race_bars_fig.update_layout(
    margin=dict(l=20, r=20, t=100, b=10),
    yaxis_title='Percent of population',
    xaxis_title=None,
    yaxis_tickformat='.0%',
    legend_title='Area',
    font_family="'Open Sans', Helvetica, Arial, sans-serif"
)


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
                value=[INITIAL_VIOLATION_TYPE],
            )
        ]),

        html.Div(id='components_container', children=[

            html.Div(id='map_container', children=[
            
                dcc.Loading(id='map_loading', type='circle', children = [

                    # initiates title; first callback will overwrite this title
                    html.H6(children=['map loading...'], id='map_title'),

                    # container and configuration for map figure
                    dcc.Graph(
                        id='map', 
                        figure=map_fig,
                        config=FIG_DISPLAY_CONFIG
                    ),

                    html.P(children=[''], id='double_click')
                ])
            ]),

            html.Div(id='timeline_and_bars_container', children=[

                dcc.Loading(id="timeline_and_bars_loading", type='default', children=[

                    # container and configuration for timeline
                    dcc.Graph(
                        id='timeline',
                        figure=timeline_fig,
                        config=FIG_DISPLAY_CONFIG
                    ),

                    # container and configuration for race bars
                    dcc.Graph(
                        id='race_bar_plot', 
                        figure=race_bars_fig,
                        config=FIG_DISPLAY_CONFIG 
                    )
                ])

            ])  

        ])
        
    ])

# ------------------------------------------------------------------------------
# callbacks
# Connect the Plotly graphs with Dash Components

# to update map on selection of timeline or violation type
@app.callback(
    [Output(component_id='map_title', component_property='children'),
     Output(component_id='map', component_property='figure'),],
    [Input(component_id='timeline',component_property='relayoutData'),
    Input(component_id='violation_type_selection', component_property='value')],
    prevent_initial_call=True
)
def update_map(selected_timeline_area,selected_violation):
    
    # # log what it's doing
    # # (werkzeug might be more useful but here's a summary )
    print("called 'update_map'")
    print(f" with 'selected_violation' = {selected_violation}")
    # print(f" with 'selected_timeline_area' = {selected_timeline_area}")

    # get time range from timeline, if the timeline has been selected
    # (this selects highly granular timestamps; could make this quantum; and also slightly delay the action until mouseup)
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
        .reindex_like(tracts)
        .fillna(0)
        .astype(int)
        .reset_index()
        .values
    )

    # print(f" updated data: {selected_tickets[:3]}")

    # patch the updated data into the data field of the fig
    patched_map_fig = Patch()
    patched_map_fig['data'][0]['locations'] = selected_tickets[:,0]
    patched_map_fig['data'][0]['z'] = selected_tickets[:,1]
    
    return title, patched_map_fig

# to update timeline and race bars on selection of map or violation type
@app.callback(
    [Output(component_id='race_bar_plot', component_property='figure'),
     Output(component_id='timeline', component_property='figure'),
     Output(component_id='double_click',component_property='children')],
    [Input(component_id='map', component_property='selectedData'),
    #  Input(component_id='map',component_property='clickData'),
     Input(component_id='violation_type_selection', component_property='value')]
)
def update_race_bars_and_timeline_from_map_selection(selected_map_area,selected_violation):

    print('called update_race_bars_and_timeline')
    # get the tracts that were selected on map
    
    # clear selection
    selected_GEOIDs = False
    double_click_text = ''

    # get GEOID value(s) from selected data dict passed back from map selection/click
    if bool(selected_map_area):
        selected_GEOIDs = [i['location'] for i in selected_map_area['points']]
        double_click_text = 'Double-click map to remove selection'

    # elif clicked_tract:
    #     selected_GEOIDs = [clicked_tract['points'][0]['location']]

    if selected_GEOIDs:

        # subset tracts to selection
        tracts_selected = tracts.loc[selected_GEOIDs]

        # recompute race pcts for selected tracts
        selection_race_pct = (
            (
                (tracts_selected[['White','Black','Asian','Hispanic']].sum())
                /
                (tracts_selected['Total population'].sum())
            )
            # .rename('Selected area')
            # .to_frame()
            .values
        )

        race_bars_title = 'Race and ethnicity citywide and selected area'

        # patch data and title to race bars fig
        patched_race_bars = Patch()
        patched_race_bars['data'][1]['y'] = selection_race_pct
        patched_race_bars['layout']['title']['text'] = 'Race and ethnicity citywide and selected area'

        # recompute timeline from selected area and selected type
        selected_area_timeline_data = (
            tickets
            .loc[selected_GEOIDs,:,selected_violation]
            .groupby('Issue Date')
            .sum()
            .rolling(3,1,center=True).mean()
            .reindex(
                timeline_fig['data'][0]['x']   # get the existing timeline x axis and reindex on this to align new y data with existing x ticks, because the filtered data can include months with no data
            )
            .values
        )

        timeline_title = 'Selected area'

        # patch data and title to timeline
        # ( could also _add_ the subset to the timeline to compare the selection to total .. )

        patched_timeline = Patch()
        patched_timeline['data'][0]['y'] = selected_area_timeline_data
        patched_timeline['layout']['title'] = timeline_title
    
    else:

        # patch zeros and title to race bars fig
        patched_race_bars = Patch()
        patched_race_bars['data'][1]['y'] = np.array([0,0,0,0])
        patched_race_bars['layout']['title']['text'] = NO_SELECTION_RACE_BARS_TITLE

        # compute timeline from all tracts
        selected_area_timeline_data = (
            tickets
            .loc[:,:,selected_violation]
            .groupby('Issue Date')
            .sum()
            .rolling(3,1,center=True).mean()
            .reindex(
                timeline_fig['data'][0]['x']   # get the existing timeline x axis and reindex on this to align new y data with existing x ticks, because the filtered data can include months with no data
            )
            .values
        )

        timeline_title = 'Total citywide'

        # patch data and title to timeline
        # ( could also _add_ the subset to the timeline to compare the selection to total .. )

        patched_timeline = Patch()
        patched_timeline['data'][0]['y'] = selected_area_timeline_data
        patched_timeline['layout']['title'] = timeline_title

    return patched_race_bars, patched_timeline, double_click_text


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


