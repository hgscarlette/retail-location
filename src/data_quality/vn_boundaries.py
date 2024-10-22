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

def only_latin_char(word):
    word_no_diacritic = unidecode(word).lower()
    word_no_space_specialchar = ''.join(e for e in word_no_diacritic if e.isalnum())
    return word_no_space_specialchar

def fix_admin_names(df):
    for col in ["city","district","ward"]:
        # Tackle districts like CaoLãnh(Thànhphố) or wards like AnChâu(Thịtrấn)
        df[col] = df[col].apply(lambda x: insert_space(reverse_bracket(x)).replace("Thànhphố","Thành Phố").replace("Thịxã","Thị Xã").replace("Thịtrấn","Thị Trấn"))
        # Rename mispelling districts & wards
        df["district"] = df["district"].apply(lambda x: x.replace('Qui Nhơn','Quy Nhơn').replace('Tân Thành','Phú Mỹ'))
        df["ward"] = df["ward"].apply(lambda x: x.replace("Cầukho","Cầu Kho").replace("Trực Phú","Ninh Cường").replace("Việt Khái","Nguyễn Việt Khái")
                                                 .replace('Chương Dương Độ','Chương Dương').replace("Phiêng Côn","Phiêng Kôn")
                                                 .replace('Trungtâmhuấnluyện','TTHL').replace("Cư Yang","Cư Jang"))
        # df["ward"][df.ward_id=="VNM.39.1.15_1"] = "Thanh Phú"
        df.loc[df[df.ward_id=="VNM.39.1.15_1"].index, "ward"] = "Thanh Phú"
    return df

def adminkeys_to_match(df):
    # Create matching keys between datasets by transforming administrative names
    df["dist_title"] = df["district"]
    df["dist_en"] = df["district"]
    df["ward_en"] = df["ward"]
    for i in range(len(df)):
        # Split administrative names into names and titles (e.g. Thị Xã Buôn Hồ)
        for d in ["Thành Phố","Quận","Thị Xã"]:
            df.loc[i, "dist_en"] = df.dist_en[i].replace(d,"")
            df.loc[i, "dist_title"] = df.dist_title[i].replace(df.dist_en[i],"")
        for w in ['Huyện','Phường','Thị Trấn','Xã']:
            df.loc[i, "ward_en"] = df.ward_en[i].replace(w,"")
    # Remove all diacritics, spaces and special characters
    for col in ["ward_title","ward_en","dist_title","dist_en"]:
        df[col] = df[col].apply(lambda x: only_latin_char(x))
    # Some district just has title&number, thus need to insert the title "Quận" back to these districts
    df["dist_en"] = df["dist_en"].apply(lambda x: "quan"+str(int(x)) if x.isnumeric() else only_latin_char(x))
    # Some ward just has title&number, thus need to insert the title "Phường" back to these wards
    df["ward_en"] = df["ward_en"].apply(lambda x: "phuong"+str(int(x)) if x.isnumeric() else only_latin_char(x))
    df.loc[df[df.dist_id=="VNM.24.7_1"].index, "ward_en"] = df[df.dist_id=="VNM.24.7_1"].ward_en.apply(lambda x: "phuong"+x if len(x) < 4 else x) ##phườngIV
    return df

def read_json(filepath, cols, newcols):
    df = gpd.read_file(filepath)
    df = df[df.columns[cols]]
    df = df.set_axis(newcols, axis=1)
    df = fix_admin_names(df)
    # To match with Population
    df = adminkeys_to_match(df)
    return df

def read_shp(filepath, cols, newcols):
    df = gpd.read_file(filepath)
    df = gpd.GeoDataFrame(df, crs=32648)
    df = df.to_crs(4326)
    df = df[df.columns[cols]]
    df = df.set_axis(newcols, axis=1)
    # To match with GADM
    df["dist_en"] = df["dist_en"].apply(lambda x: only_latin_char(x.replace("District","Quan")))
    df["ward_en"] = df["ward_en"].apply(lambda x: only_latin_char(x.replace("Ward","Phuong")))
    return df

def get_representative_loc(df, admin_level):
    df_admin = df[[admin_level,"geometry"]].dissolve(by=admin_level, as_index=False)
    df_admin["loc"] = df_admin.representative_point()
    df = pd.merge(df, df_admin[[admin_level,"loc"]], how="inner", on=[admin_level])
    return df

def exec_ward():
    # Source: https://gadm.org/download_country.html (level 3 = Ward)
    # Note: GADM administrative names don't have spaces
    gadm_boundaries = read_json(filepath=r"data\gadm41_VNM_3.json",
                                cols=[2,4,7,6,9,0,12,16],
                                newcols=["country","city","district","dist_id","ward","ward_id","ward_title","geometry"],
                                cols_to_fix=["city","district","ward","ward_title"]
                                )

    # Source: https://github.com/CityScope/CSL_HCMC/tree/main/Data/GIS/Population/population_HCMC/population_shapefile
    cityscope_boundaries = read_shp(filepath=r"data\CityScope_HCMC\Population_Ward_Level.shp",
                                    cols=[0,1,2,11],
                                    newcols=["ward_en","district_en","cityscope_id","geometry"]
                                    )

    ## Merge 2 boundaries
    hcmc_boundaries = gadm_boundaries[gadm_boundaries.city=="Hồ Chí Minh"].drop(["geometry"], axis=1)
    hcmc_boundaries = pd.merge(hcmc_boundaries, cityscope_boundaries, how="inner", on=["district_en", "ward_en"])
    hcmc_boundaries = gpd.GeoDataFrame(hcmc_boundaries)

    # Append modified HCMC boundaries to GADM
    ward_boundaries = pd.concat([gadm_boundaries[gadm_boundaries.city!="Hồ Chí Minh"], hcmc_boundaries])
    ward_boundaries = gpd.GeoDataFrame(ward_boundaries.drop(["cityscope_id","district_en", "ward_en","ward_title_en"], axis=1))
    ward_boundaries = get_representative_loc(ward_boundaries, "city")
    return ward_boundaries

def exec_dist():
    ward_boundaries = exec_ward()
    dist_boundaries = ward_boundaries.drop(["ward","ward_id","ward_title","ward_en"], axis=1)
    dist_boundaries = dist_boundaries.dissolve(by=["country","city","district","dist_title","dist_en","dist_id"], as_index=False)
    return dist_boundaries