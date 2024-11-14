import pandas as pd
import geopandas as gpd
from unidecode import unidecode

"""
While analyzing all datasets, I found some issues in the boundaries provided by GADM:
- most polygons are not well defined - when visualized, they don't cover the whole neighborhood, like can cut residence areas or streets
- the administratives are not updated, i.e. old names, old governing territory, etc.

In an effort of looking for well refined boundaries, I found an public project City Scope which supported HCMC's city planning.
I haven't found any source for other cities yet.
For now, I'll replace the GADM's HCMC boundaries with CityScope's     
"""

def insert_space(word):
    result = ""
    num = "0123456789"
    # Iterate through each character in the word
    for i in word:
        # Check if the character is uppercase
        if i.isupper():
            # Concatenate a space and the uppercase version of the character to the result
            result = result + " " + i.upper()
        # Check if the character is number
        elif i in num:
            # Concatenate the character to the result if the previous character was also a number
            if result[-1] in num:
                result = result + i
            # Concatenate a space only if the previous character was not a number
            else:
                result = result + " " + i
        else:
            # Concatenate the character to the result
            result = result + i
    # Remove the leading space from the result and return
    return result[1:]

def reverse_bracket(word):
    word_no_bracket = ""
    if "(" in word:
        word_no_bracket = word.split("(")[1].replace(")","") + word.split("(")[0]
    else:
        word_no_bracket = word
    return word_no_bracket

def fix_admin_names(df):
    for col in ["city","district","ward"]:
        # Tackle districts like CaoLãnh(Thànhphố) or wards like AnChâu(Thịtrấn)
        df[col] = df[col].apply(lambda x: reverse_bracket(x).replace("Thànhphố","ThànhPhố").replace("Thịxã","ThịXã").replace("Thịtrấn","ThịTrấn"))
        # Rename mispelling districts & wards
        df["district"] = df["district"].apply(lambda x: x.replace("QuiNhơn","QuyNhơn").replace("TânThành","PhúMỹ"))
        df["ward"] = df["ward"].replace({"ViệtKhái":"NguyễnViệtKhái","TrựcPhú":"NinhCường","ChươngDươngĐộ":"ChươngDương",
                                       "PhiêngCôn":"PhiêngKôn","Trungtâmhuấnluyện":"TTHL","CưYang":"CưJang","Cầukho":"CầuKho"})
        df.loc[df[df.ward_id=="VNM.39.1.15_1"].index, "ward"] = "ThanhPhú"
    return df

def adminkeys_to_match(df):
    # Original administrative names - To show on dashboard
    for col in ["city","district","ward"]:
        df[col+"_org"] = df[col].apply(lambda x: insert_space(x))
    
    # Split administrative names into names and titles (e.g. Thị Xã Buôn Hồ)
    for i in range(len(df)):
        for c in ["ThànhPhố","Tỉnh"]:
            df.loc[i,"city"] = df.city[i].replace(c,"")
        for d in ["ThànhPhố","Quận","ThịXã","Huyện"]:
            df.loc[i,"district"] = df.district[i].replace(d,"")
        for w in ["Huyện","Phường","Thị Trấn","Xã"]:
            df.loc[i,"ward"] = df.ward[i].replace(w,"")
    
    # Some district just has title&number, thus need to insert the title "Quận" back to these districts
    df["district"] = df["district"].apply(lambda x: "Quận"+str(int(x)) if x.isnumeric() else x)
    # Some ward just has title&number, thus need to insert the title "Phường" back to these wards
    df["ward"] = df["ward"].apply(lambda x: "Phường"+str(int(x)) if x.isnumeric() else x)
    df.loc[df[df.dist_id=="VNM.24.7_1"].index, "ward"] = df[df.dist_id=="VNM.24.7_1"].ward.apply(lambda x: "Phường"+x if len(x) < 4 else x) ##phườngIV
    
    # After transformation, some districts/wards are duplicated, thus need to revert them back to their original names
    dup_dist = df.groupby(["city","district"])["dist_id"].transform('nunique').gt(1)
    df.loc[dup_dist,"district"] = df.loc[dup_dist,"district_org"].apply(lambda x: x.replace(" ",""))
    dup_ward = df.groupby(["city","district","ward"])["ward_id"].transform('nunique').gt(1)
    df.loc[dup_ward,"ward"] = df.loc[dup_ward,"ward_org"].apply(lambda x: x.replace(" ",""))
    
    # Buffer matching keys by removing all diacritics
    df["dist_en"] = df["district"].apply(lambda x: unidecode(x).lower())
    df["ward_en"] = df["ward"].apply(lambda x: unidecode(x).lower())
    return df

def read_json(filepath, cols, newcols):
    df = gpd.read_file(filepath)
    df = df[df.columns[cols]]
    df.columns = newcols
    df = fix_admin_names(df)
    # To match with Population
    df = adminkeys_to_match(df)
    return df

def read_shp(filepath, cols, newcols):
    df = gpd.read_file(filepath)
    df = gpd.GeoDataFrame(df, crs=32648)
    df = df.to_crs(4326)
    df = df[df.columns[cols]]
    df.columns = newcols
    # To match with GADM
    df["dist_en"] = df["dist_en"].apply(lambda x: x.replace("District","Quan").lower().replace(" ",""))
    df["ward_en"] = df["ward_en"].apply(lambda x: x.replace("Ward","Phuong").lower().replace(" ",""))
    return df

def measure_area(df):
    # convert CRS to equal-area projection -> the length unit is now `meter`
    df = df.df(epsg=6933)
    df["area_sqm"] = df.area.values #/10e6 for sqKm
    df = df.to_crs(epsg=4326)
    return df

def get_representative_loc(df, admin_level):
    df_admin = df[[admin_level,"geometry"]].dissolve(by=admin_level, as_index=False)
    df_admin["city_centroid"] = df_admin.representative_point()
    df = pd.merge(df, df_admin[[admin_level,"city_centroid"]], how="inner", on=[admin_level])
    return df

def exec(admin_level):
    # Source: https://gadm.org/download_country.html (level 3 = Ward)
    # Note: GADM administrative names don't have spaces
    gadm_boundaries = read_json(filepath=r"data\gadm41_VNM_3.json",
                                cols=[2,4,7,6,9,0,16],
                                newcols=["country","city","district","dist_id","ward","ward_id","geometry"],
                                )

    # Source: https://github.com/CityScope/CSL_HCMC/tree/main/Data/GIS/Population/population_HCMC/population_shapefile
    cityscope_boundaries = read_shp(filepath=r"data\CityScope_HCMC\Population_Ward_Level.shp",
                                    cols=[0,1,2,11],
                                    newcols=["ward_en","dist_en","cityscope_id","geometry"]
                                    )

    ## Merge 2 boundaries
    hcmc_boundaries = gadm_boundaries[gadm_boundaries.city=="HồChíMinh"].drop(["geometry"], axis=1)
    hcmc_boundaries = pd.merge(hcmc_boundaries, cityscope_boundaries, how="inner", on=["dist_en","ward_en"])
    hcmc_boundaries = gpd.GeoDataFrame(hcmc_boundaries)

    # Append modified HCMC boundaries to GADM
    ward_boundaries = pd.concat([gadm_boundaries[gadm_boundaries.city!="HồChíMinh"], hcmc_boundaries])
    ward_boundaries = gpd.GeoDataFrame(ward_boundaries.drop(["cityscope_id"], axis=1))

    # Measure area size to later calculate population density
    ward_boundaries = measure_area(ward_boundaries)
    # Get city central point to navigate map easily
    ward_boundaries = get_representative_loc(ward_boundaries, "city")
    
    dist_boundaries = ward_boundaries[[col for col in ward_boundaries.columns if "ward" not in col and "area" not in col]]
    dist_boundaries = dist_boundaries.dissolve(by=["country","city","district","dist_id","city_org","district_org","dist_en"], as_index=False)
    # Measure area size to later calculate population density
    dist_boundaries = measure_area(dist_boundaries)

    return ward_boundaries if admin_level=="ward" else dist_boundaries