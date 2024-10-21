import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
import streamlit as st
from streamlit_folium import st_folium
from shapely.geometry import Point

st.set_page_config(layout="wide")

def load_data():
    wcm_path = r'C:\Users\Admin\Desktop\Map_visualization_ver2\wcm_stores_with_info.xlsx'
    df_stores = pd.read_excel(wcm_path)

    population_path = r'C:\Users\Admin\Desktop\Map_visualization_ver2\population_withid.xlsx'
    df_population = pd.read_excel(population_path)

    geojson_file = r'C:\Users\Admin\Desktop\Map_visualization_ver2\Boundary.geojson'
    boundary = gpd.read_file(geojson_file)

    return df_stores, df_population, boundary

def create_map(location):
    return folium.Map(location=location, zoom_start=12)

def add_choropleth(m, boundary, df_population, selected_city):
    filtered_boundary = boundary[boundary['city'] == selected_city]
    folium.Choropleth(
        geo_data=filtered_boundary,
        data=df_population,
        columns=['ward_id', 'total'],
        key_on='feature.properties.ward_id',
        fill_color='Blues',
        fill_opacity=0.5,
        line_opacity=0.2,
        legend_name='Population',
        highlight=True
    ).add_to(m)

def add_markers(m, df_stores, filtered_boundary):
    marker_cluster = MarkerCluster().add_to(m)
    for _, store in df_stores.iterrows():
        point = Point(store['long'], store['lat'])
        if filtered_boundary['geometry'].contains(point).any():
            folium.Marker(location=[store['lat'], store['long']], popup=store['STORE_NAME']).add_to(marker_cluster)

def zoom_to_location(m, boundary, selected_city):
    filtered_boundary = boundary[boundary['city'] == selected_city]

    if not filtered_boundary.empty:
        filtered_boundary = filtered_boundary.to_crs(epsg=4326)  

        center_lat = filtered_boundary.geometry.centroid.y.mean()
        center_long = filtered_boundary.geometry.centroid.x.mean()
        m.location = [center_lat, center_long]
        m.zoom_start = 13 

def display_store_data_and_population_info(df_population, df_stores, boundary, lat, lon):
    point = Point(lon, lat)
    found = False
    population = 0
    store_count = 0
    filtered_stores = pd.DataFrame()
    ward_name = ""
    district_name = ""

    for _, feature in boundary.iterrows():
        if feature['geometry'].contains(point):
            ward_id = feature['ward_id']
            filtered_population = df_population[df_population['ward_id'] == ward_id]
            population = filtered_population['total'].values[0] if not filtered_population.empty else 0
            store_count = df_stores[df_stores['ward_id'] == ward_id].shape[0]
            filtered_stores = df_stores[df_stores['ward_id'] == ward_id]
            ward_name = feature['ward']
            district_name = feature['district'] 
            found = True
            break

    return found, filtered_stores, population, store_count, ward_name, district_name

df_stores, df_population, boundary = load_data()

city_options = boundary['city'].unique()
selected_city = st.sidebar.selectbox('City', city_options)

district_options = boundary[boundary['city'] == selected_city]['district'].unique()
selected_district = st.sidebar.selectbox('District', ['All'] + list(district_options))

ward_options = boundary[boundary['city'] == selected_city]['ward'].unique()
selected_ward = st.sidebar.selectbox('Ward', ['All'] + list(ward_options))

concept_options = df_stores['concept'].unique()
selected_concept = st.sidebar.selectbox('Chọn concept', ['All'] + list(concept_options))

filtered_boundary = boundary[boundary['city'] == selected_city]
if selected_district != 'All':
    filtered_boundary = filtered_boundary[filtered_boundary['district'] == selected_district]
if selected_ward != 'All':
    filtered_boundary = filtered_boundary[filtered_boundary['ward'] == selected_ward]
with st.container():
    col1, col2 = st.columns([3, 1])  

    with col1:
        m = create_map([10.762622, 106.660172])
        add_choropleth(m, boundary, df_population, selected_city)
        add_markers(m, df_stores, filtered_boundary)
        zoom_to_location(m, boundary, selected_city)

        map_container = st_folium(m, width=700, height=400)  

        
        found = False
        population = 0
        store_count = 0
        filtered_stores = pd.DataFrame()
        ward_name = ""
        district_name = ""

        if map_container and 'last_clicked' in map_container:
            last_clicked = map_container['last_clicked']
            if last_clicked:
                lat = last_clicked['lat']
                lon = last_clicked['lng']

                found, filtered_stores, population, store_count, ward_name, district_name = display_store_data_and_population_info(df_population, df_stores, boundary, lat, lon)

                if found:
                    st.markdown(f"**District:** {district_name}")
                    st.markdown(f"**Ward:** {ward_name}")

                    if not filtered_stores.empty:
                        st.markdown("### Stores information")
                        store_data = filtered_stores[['STORE_NAME', 'STORE_ID','concept', 'address']]
                        st.dataframe(store_data, use_container_width=True)
                    else:
                        st.write("No store in this ward")
            else:
                st.write("Click a ward")

    with col2:
        if found:
            st.markdown(
                f"""
                <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 5px; width: 100%; height: 80px; background-color: #f9f9f9; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);">
                    <h4 style="color: #4CAF50; text-align: center; font-size: 14px;">Population</h4>
                    <p style="text-align: center; font-size: 16px;">{population}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div style="border: 2px solid #2196F3; border-radius: 10px; padding: 5px; width: 100%; height: 80px; background-color: #f9f9f9; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); margin-top: 10px;">
                    <h4 style="color: #2196F3; text-align: center; font-size: 14px;">Stores count</h4>
                    <p style="text-align: center; font-size: 16px;">{store_count}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            ratio = population / store_count if store_count > 0 else 0

            st.markdown(
                f"""
                <div style="border: 2px solid #FF9800; border-radius: 10px; padding: 5px; width: 100%; height: 80px; background-color: #f9f9f9; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); margin-top: 10px;">
                    <h4 style="color: #FF9800; text-align: center; font-size: 14px;">Population/stores</h4>
                    <p style="text-align: center; font-size: 16px;">{ratio:.2f}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.write("Click a ward")