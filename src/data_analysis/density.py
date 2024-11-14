import pandas as pd
from src.data_quality.vn_boundaries import exec as boundaries
from src.data_quality.vn_population import exec as population
import duckdb

query_init = f"""
INSTALL spatial; 
LOAD spatial;
"""
duckdb.default_connection.sql(query_init)

"""
To utilize all available data, I need to create a key id to map all datasets. I'm using GADM's IDs for this purpose.
Please note that GADM doesn't have boundaries of Trường Sa(Khánh Hòa)-3 wards and Côn Đảo (BRVT)-1 ward
"""

def set_wardID(df, boundary):
    boundary_sql = boundary.drop(["geometry","city_centroid"], axis=1)
    query = f"""
    SELECT DISTINCT
        IFNULL(IFNULL(IFNULL(gadm.ward_id, gadm_ward.ward_id), gadm_full.ward_id), gadm_en.ward_id) AS ward_id,
        df.*
    FROM df
    LEFT JOIN boundary_sql gadm
    ON df.city = gadm.city AND df.district = gadm.district AND df.ward = gadm.ward
    LEFT JOIN boundary_sql gadm_ward
    ON df.city = gadm_ward.city AND df.district = gadm_ward.district AND REPLACE(df.ward_org,' ','') = gadm_ward.ward
    LEFT JOIN boundary_sql gadm_full
    ON df.city = gadm_full.city AND REPLACE(df.district_org,' ','') = gadm_full.district AND REPLACE(df.ward_org,' ','') = gadm_full.ward
    LEFT JOIN boundary_sql gadm_en
    ON df.city = gadm_en.city AND df.dist_en = gadm_en.dist_en AND df.ward_en = gadm_en.ward_en
    """
    df_with_id = duckdb.default_connection.sql(query).df()
    # Rearrange columns and remove unnecessary ones
    cols = df_with_id.columns.tolist()
    cols = cols[0:2] + cols[-6:-4] + cols[2:-6]
    return df_with_id[cols]

def set_distID(df, boundary):
    boundary_sql = boundary.drop(["geometry","city_centroid"], axis=1)
    query = f"""
    SELECT DISTINCT
        IFNULL(IFNULL(gadm.dist_id, gadm_full.dist_id), gadm_en.dist_id) AS dist_id,
        pop.*
    FROM df pop
    LEFT JOIN boundary_sql gadm
    ON pop.city = gadm.city AND pop.district = gadm.district
    LEFT JOIN boundary_sql gadm_full
    ON pop.city = gadm_full.city AND REPLACE(pop.district_org,' ','') = gadm_full.district
    LEFT JOIN boundary_sql gadm_en
    ON pop.city = gadm_en.city AND pop.dist_en = gadm_en.dist_en
    """
    df_with_id = duckdb.default_connection.sql(query).df()
    # Rearrange columns and remove unnecessary ones
    cols = df_with_id.columns.tolist()
    cols = cols[0:2] + cols[-3:-2] + cols[2:-3]
    return df_with_id[cols]

def exec(admin_level):
    # Get population enhanced data
    df_allpop = population(population_size="all")
    df_householdpop = population(population_size="household")
    df_youngpop = population(population_size="young")
    # Get GADM enhanced data
    ward_boundaries = boundaries(admin_level="ward")
    dist_boundaries = boundaries(admin_level="district")
    # Population by Ward
    df_allpop_with_id = set_wardID(df_allpop, ward_boundaries)
    # Population by Ward
    df_householdpop_with_id = set_wardID(df_householdpop, ward_boundaries)
    df_demographic_ward = pd.merge(df_allpop_with_id, df_householdpop_with_id, how="inner", on=["ward_id","city","district_org","ward_org","district","ward"])
    # Young population by District
    df_youngpop_with_id = set_distID(df_youngpop, dist_boundaries)
    df_demographic_dist = df_youngpop_with_id.copy()
    return df_demographic_ward if admin_level=="ward" else df_demographic_dist
