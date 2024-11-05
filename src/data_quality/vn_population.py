import pandas as pd

"""
Source of population data: http://portal.thongke.gov.vn/khodulieudanso2019/Default.aspx
"""

import pandas as pd
from unidecode import unidecode

def read_excel_pivot(path, row_to_skip, row_header, cols_remove_agg, row_agg):
    df = pd.read_excel(path, skiprows=row_to_skip, header=row_header)
    # Fill up empty Group by level rows
    cols=df.columns[[0,1]]
    df.loc[:,cols] = df.loc[:,cols].ffill()
    # Remove all aggregated rows
    for col in df.columns[cols_remove_agg]:
        df = df[~df[col].str.contains(row_agg, na=False)]
    df.reset_index(drop=True, inplace=True)
    return df

def fix_admin_names(df):
    df["city"] = df.city.apply(lambda x: x.replace("Thành phố","Thành Phố").replace('Thanh Hoá','Thanh Hóa').replace('Khánh Hoà','Khánh Hòa').replace("  "," ").strip())
    df["district"] = df.district.apply(lambda x: x.replace("Thành phố","Thành Phố").replace("Thị xã","Thị Xã").replace("  "," ").strip())
    # Original administrative names
    df["district_org"] = df["district"]
    if "ward" in df.columns:
        df["ward"] = df["ward"].apply(lambda x: x.replace("Qui Hướng","Quy Hướng").replace("Mương Tranh","Mường Chanh").replace("Xốp Cộp","Sốp Cộp")
                                                 .replace("La Tơi","Ia Tơi").replace("La Dom","Ia Dom").replace("La Dal","Ia Dal")
                                                 .replace("La Rong","Ia Rong").replace("La Pal","Ia Pal").replace("Nà Ơt","Nà Ớt")
                                                 .replace(" Ii"," II").replace("Hòa Tú II","Hòa Tú 2").replace("trấn Phước Cát","trấn Phước Cát 1")
                                                 # .replace("Hoà","Hòa").replace("Hòan","Hoàn").replace("Hòai","Hoài")
                                                 .replace("  "," ").strip())
        df["ward"] = df["ward"].apply(lambda x: " ".join([k.title() if k.upper() != k else k for k in x.split()]))
        # Original administrative names
        df["ward_org"] = df["ward"]
    return df

def adminkeys_to_match(df, cols_to_fix):
    # Create matching keys between datasets by transforming administrative names
    for col in cols_to_fix:
        df[col] = df[col].apply(lambda x: x.replace(" ",""))
    for i in range(len(df)):
        for c in ["ThànhPhố","Tỉnh"]:
            df.loc[i,"city"] = df.city[i].replace(c,"")
        for d in ["ThànhPhố","Quận","ThịXã","Huyện"]:
            df.loc[i,"district"] = df.district[i].replace(d,"")
    # Buffer matching keys by removing all diacritics
    df["dist_en"] = df["district"].apply(lambda x: unidecode(x).lower())
    # Some district just has title&number, thus need to insert the title "Quận" back to these districts
    df["district"] = df["district"].apply(lambda x: "Quận"+str(int(x)) if x.isnumeric() else x)
    # After transformation, some districts/wards are duplicated, thus need to revert them back to their original names
    dup_dist = df.groupby(["city","district"])["dist_id"].transform('nunique').gt(1)
    df.loc[dup_dist,"district"] = df.loc[dup_dist,"district_org"].apply(lambda x: x.replace(" ",""))

    if "ward" in cols_to_fix:
        for i in range(len(df)):
            for w in ["Huyện","Phường","ThịTrấn","Xã"]:
                df.loc[i,"ward"] = df.ward[i].replace(w,"")
        # Buffer matching keys by removing all diacritics
        df["ward_en"] = df["ward"].apply(lambda x: unidecode(x).lower())
        # Some ward just has title&number, thus need to insert the title "Phường" back to these wards
        df["ward"] = df["ward"].apply(lambda x: "Phường"+str(int(x)) if x.isnumeric() else 
                                               ("Phường"+str(int(x)) if x.upper()==x and len(df.ward[i]) < 4  ##phườngIV
                                                else x))
        dup_ward = df.groupby(["city","district","ward"])["ward_id"].transform('nunique').gt(1)
        df.loc[dup_ward,"ward"] = df.loc[dup_ward,"ward_org"].apply(lambda x: x.replace(" ",""))
        
    return df

def transform_admin_data(df, cols, cols_to_fix):
    # Rename columns
    df.columns = cols
    # Fix some wrong adminnistrative names
    fix_admin_names(df)
    # Add administrative IDs to process data
    df["dist_id"] = df.groupby(["city","district"]).ngroup()
    if "ward" in cols:
        df["ward_id"] = df.groupby(["city","district","ward"]).ngroup()
    # Clean adminnistrative names to match with other datasets
    df = adminkeys_to_match(df, cols_to_fix)
    return df

def exec(population_size):
    # Population by Ward and Urban/Rural
    df_allpop = read_excel_pivot(path=r"data\Population data\Population by Urban (Ward).xlsx",
                                 row_to_skip=2, row_header=0,
                                 cols_remove_agg=[0,1], row_agg="Tổng số"
                                 )
    allpop_ward = transform_admin_data(df_allpop,
                                       cols=["city","district","ward","total","urban","rural"],
                                       cols_to_fix=["city","district","ward"]
                                       )
    
    # Population by Age and Urban/Rural
    df_popage = read_excel_pivot(path=r"data\Population data\Population by Age & Urban (District).xlsx",
                                 row_to_skip=2, row_header=[0,1],
                                 cols_remove_agg=[0], row_agg="Tổng số"
                                 )
    df_popage["15-34_urban"] = df_popage['1. Thành thị'][df_popage['1. Thành thị'].columns[3:7]].sum(axis=1)
    df_popage["15-34_rural"] = df_popage['2. Nông thôn'][df_popage['2. Nông thôn'].columns[3:7]].sum(axis=1)
    df_popage["15-34_total"] = df_popage["15-34_urban"] + df_popage["15-34_rural"]
    youngpop_dist = df_popage[df_popage.columns[[0,1,41,42,43]]]
    youngpop_dist = transform_admin_data(youngpop_dist,
                                         cols=["city","district","15-34_urban","15-34_rural","15-34_total"],
                                         cols_to_fix=["city","district"]
                                         )
    
    # Household number by Size and Urban/Rural
    df_household = read_excel_pivot(path=r"data\Population data\Population by Household Size (Ward).xlsx",
                                    row_to_skip=2, row_header=[0,1],
                                    cols_remove_agg=[0,1], row_agg="Tổng số"
                                    )

    df_household["5+_urban"] = df_household['1. Thành thị'][df_household['1. Thành thị'].columns[4:]].sum(axis=1)
    df_household["1-2_rural"] = df_household['2. Nông thôn'][df_household['2. Nông thôn'].columns[0:2]].sum(axis=1)
    df_household["5+_rural"] = df_household['2. Nông thôn'][df_household['2. Nông thôn'].columns[4:]].sum(axis=1)

    household_ward = df_household[df_household.columns[[0,1,2,5,6,7,8,20,21,15,16,22]]]
    household_ward = transform_admin_data(household_ward,
                                          cols=["city","district","ward","1_urban","2_urban","3_urban","4_urban","5+_urban","1-2_rural","3_rural","4_rural","5+_rural"],
                                          cols_to_fix=["city","district","ward"]
                                          )
    
    return allpop_ward if population_size=="all" else (youngpop_dist if population_size=="young" else household_ward)