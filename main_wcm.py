from src.data_analysis.density import exec as demographic
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import streamlit as st
from streamlit_folium import st_folium
from shapely.geometry import Point

@st.cache_data

# def load_data():
#     df_store = pd.read_excel(r"data\Winmart location.xlsx")
#     # Get population enhanced data
#     df_allpop = population(population_size="all")
#     df_householdpop = population(population_size="household")
#     # Get GADM enhanced data
#     ward_boundaries = boundaries(admin_level="ward")
#     return df_store, df_allpop, df_householdpop, ward_boundaries


# df_store, df_allpop, df_householdpop, ward_boundaries = load_data()
# df_allpop_with_id = demographic(df_allpop, ward_boundaries, "ward")
# df_householdpop_with_id = demographic(df_householdpop, ward_boundaries, "ward")
# df_demographic_ward = pd.merge(df_allpop_with_id, df_householdpop_with_id, how="inner", on=["ward_id","city","district_org","ward_org","district","ward"])

def load_data():
    df_store = pd.read_excel(r"data\Winmart location.xlsx")
test = demographic("ward")

st.write(test)