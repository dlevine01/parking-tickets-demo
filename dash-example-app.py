# eample from https://github.com/Coding-with-Adam/Dash-by-Plotly/blob/master/Other/Dash_Introduction/intro.py

import pandas as pd
import geopandas as gpd
import plotly.express as px  # (version 4.7.0 or higher)
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output  # pip install dash (version 2.0.0 or higher)

# BOOTSTRAP_CSS = "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css"

STYLE = "https://codepen.io/chriddyp/pen/bWLwgP.css"

app = Dash(__name__, external_stylesheets=[STYLE])

# to serve 
server = app.server

# --- read in data and create initial state

tracts = (
    gpd.read_file(
        'processed data/tracts_4326_w_pcts.geojson',
        dtype={'GEOID':'str'}
        )
    .set_index('GEOID')
)

tickets = (
    pd.read_csv(
        'processed data/tickets_by_tract_by_month_by_type_from_geosupport_return.csv', 
        parse_dates=['year-month'],
        dtype={'GEOID':'str'}
        )
    .rename(columns={'year-month':'Issue Date'})
    .set_index(['GEOID','Issue Date','Violation Type'])
    ['tickets count']
    .sort_index()
)


# -- 

total_tickets_by_month = (
    tickets
    .groupby('Issue Date')
    .sum()
    .rolling(3,1,center=True).mean()
    .to_frame()
)

violation_types = tickets.index.get_level_values('Violation Type').unique()

total_race_pct = (
    (
        (tracts[['White','Black','Asian','Hispanic']].sum())
        /
        (tracts['Total population'].sum())
    )
    .rename('Citywide')
    .to_frame()
)

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

initial_timeline = dict()


# ------------------------------------------------------------------------------
# App layout
app.layout = html.Div(id='app', children=[

    html.H1("Explore parking tickets by type"),

    html.Div(id='components_container', children=[

        html.Div(id='map_container', children=[
            # html.H2('map'),

            html.H5(children=['map loading...'], id='map_title'),

            dcc.Graph(
                id='map', 
                figure=initial_map_fig
            ),
        ], style={'flex':5}
        ),

        html.Div(id='timeline_and_bars_container', children=[
            
            # html.H2('timeline'),

            dcc.Graph(
                id='timeline',
                figure=initial_timeline
            ),

            # html.H2('bars'),

            dcc.Graph(
                id='race_bar_plot', 
                figure={}
            )
        ],style={'flex':3}
        )

    ],style={'display': 'flex', 'flex-direction': 'row'}
    ),

    html.Div(id='selector_container', children=[
    
        html.P('Select violation types:'),

        dcc.Dropdown(
            id='violation_type_selection',
            options=violation_types,
            multi=True,
            value=['FIRE HYDRANT'],
            ),
    ])

])

# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components
@app.callback(
    [Output(component_id='map_title', component_property='children'),
     Output(component_id='map', component_property='figure'),
     Output(component_id='map', component_property='selectedData')],
    [Input(component_id='timeline',component_property='relayoutData'),
    Input(component_id='violation_type_selection', component_property='value')]
)
def update_map(selected_timeline_area,selected_violation):
    
    print("called 'update_map'")
    print(f" with 'selected_violation' = {selected_violation}")
    print(f" with 'selected_timeline_area' = {selected_timeline_area}")

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

    display_dates = " - ".join([pd.to_datetime(date).strftime('%b %Y') for date in selected_dates])

    display_violation = ', '.join([violation.capitalize() for violation in selected_violation])

    title = f'Ticket type: {display_violation} & Date range: {display_dates}'

    selected_tickets = (
        tickets
        .loc[:,slice(*selected_dates),selected_violation]
        .groupby('GEOID')
        .sum()
        .reset_index()
    )

    fig = px.choropleth_mapbox(
        data_frame=selected_tickets,
        color='tickets count',
        geojson=tracts.geometry,
        locations='GEOID',
        color_continuous_scale='burg',
        mapbox_style='carto-positron',
        hover_data={
            'GEOID':False,
            'tickets count':':.1f'
        },
        zoom=9, 
        center = {"lat": 40.7, "lon": -74},
        height=600
    )

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
            thickness=0.035
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        )


    fig = fig.update_traces(
        marker_line_width=0
        )

    # Plotly Express
    # fig = px.choropleth(
    #     data_frame=dff,
    #     locationmode='USA-states',
    #     locations='state_code',
    #     scope="usa",
    #     color='Pct of Colonies Impacted',
    #     hover_data=['State', 'Pct of Colonies Impacted'],
    #     color_continuous_scale=px.colors.sequential.YlOrRd,
    #     labels={'Pct of Colonies Impacted': '% of Bee Colonies'},
    #     template='plotly_dark'
    # )

    # Plotly Graph Objects (GO)
    # fig = go.Figure(
    #     data=[go.Choropleth(
    #         locationmode='USA-states',
    #         locations=dff['state_code'],
    #         z=dff["Pct of Colonies Impacted"].astype(float),
    #         colorscale='Reds',
    #     )]
    # )
    #
    # fig.update_layout(
    #     title_text="Bees Affected by Mites in the USA",
    #     title_xanchor="center",
    #     title_font=dict(size=24),
    #     title_x=0.5,
    #     geo=dict(scope='usa'),
    # )

    return title, fig, None

@app.callback(
    [Output(component_id='race_bar_plot', component_property='figure'),
     Output(component_id='timeline', component_property='figure')],
    [Input(component_id='map', component_property='selectedData'),
     Input(component_id='violation_type_selection', component_property='value')]
)
def update_race_bars_and_timeline_from_map_selection(selected_map_area,selected_violation):

    print("called 'update_race_bars_and_timeline_from_map_selection'")

    if bool(selected_map_area):

        selected_GEOIDs = [i['location'] for i in selected_map_area['points']]

        print(f" with 'tracts_selected' including {selected_GEOIDs[0] if selected_GEOIDs else 'none'}")

        tracts_selected = tracts.loc[selected_GEOIDs]

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

        selected_area_timeline_data = (
            tickets
            .loc[selected_GEOIDs,:,selected_violation]
            .groupby('Issue Date')
            .sum()
            .rolling(3,1,center=True).mean()
            .to_frame()
        )

        timeline_title = 'Selected area'
    
    else:
        
        print(" with no selection")

        no_selection_race_pct = pd.DataFrame(index=['White','Black','Asian','Hispanic'],columns=[''],data=[0,0,0,0])
        
        race_bars_data = total_race_pct.join(no_selection_race_pct)

        race_bars_title = 'Race and ethnicity citywide'

        selected_area_timeline_data = (
            tickets
            .loc[:,:,selected_violation]
            .groupby('Issue Date')
            .sum()
            .rolling(3,1,center=True).mean()
            .to_frame()
        )

        timeline_title = None



    race_bars = px.bar(
        race_bars_data,
        barmode='group',
        title=race_bars_title,
        height=250,
        template='plotly_white'
    )

    race_bars.update_layout(
        margin=dict(l=20, r=0, t=100, b=10),
        yaxis_title='Percent of population',
        xaxis_title=None,
        yaxis_tickformat='.0%',

    )

    timeline = px.line(
        selected_area_timeline_data,
        title= timeline_title,
        height=350,
        template='plotly_white'
    )

    timeline.update_layout(
        xaxis=dict(
            rangeslider=dict(
                visible=True
            ),
            type="date"
        ),
        yaxis_title="Tickets",
        showlegend=False,
        margin=dict(l=20, r=0, t=40, b=10),
    )

    timeline.update_xaxes(rangeslider_thickness = 0.08)

    return race_bars, timeline

# ------------------------------------------------------------------------------

# this only serves locally (?)

# if __name__ == '__main__':
#     app.run_server(host="0.0.0.0", port="8050", debug=True)