import pandas as pd
import geopandas as gpd
from unidecode import unidecode
import json

def flatten_adminDB(json_filepath):
    """
    # Flatten nested store location data into a list of store dictionaries.
    """
    # Get json file content
    with open(json_filepath, encoding="utf8") as f:
        json_data = json.load(f)
    
    flattened_wards = []
    # Traverse the nested structure
    for location in json_data['fullDataLocation']:
        for province in location['provinceList']:
            province_name = province['name']
            provinceId = province['id']

            for district in province['districtBOList']:
                district_name = district['name'].split("(")[0] if "(" in district['name'] else district['name']
                districtId = district['id']
                
                for ward in district['wards']:
                    ward_name = ward['name'].split("(")[0] if "(" in ward['name'] else ward['name']
                    wardId = ward['id']
                            
                    # Create flattened administrative dictionary
                    flattened_ward = {
                        'provinceId': provinceId,
                        'city': province_name.replace(',', ';'),
                        'districtId': districtId,
                        'district': district_name.replace(',', ';'),
                        'wardId': wardId,
                        'ward': ward_name.replace(',', ';')
                    }
                    flattened_wards.append(flattened_ward)
    
    # Sort by storeId and remove duplicates
    flattened_wards.sort(key=lambda x: x['wardId'])
    # Remove duplicates while preserving order
    seen_ward_ids = set()
    unique_wards = []
    for ward in flattened_wards:
        if ward['wardId'] not in seen_ward_ids:
            seen_ward_ids.add(ward['wardId'])
            unique_wards.append(ward)

    return pd.DataFrame.from_dict(unique_wards)

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

def adminkeys_to_match(df, cols_to_fix):
    # Create matching keys between datasets by transforming administrative names
    for col in cols_to_fix:
        # Unify administrative titles by removing their spaces
        titles_withspace = ["thành phố","thị xã","thị trấn"]
        df[col] = df[col].apply(lambda x: x.replace(" ","",1) if x.lower().startswith(tuple(titles_withspace)) else x)
        for index, row in df.iterrows():
            titles_withdot = ["tp.","t.","q.","tx.","h.","p.","tt.","x."]
            titles_nodot = ["thànhphố","tỉnh","quận","thịxã","huyện","phường","thịtrấn","xã"]
            # Remove all administrative titles
            if row[col].lower().startswith(tuple(titles_withdot)):
                notitle = "".join(row[col].strip().split(".")[1:]).replace(" ","")
                title = "".join(row[col].strip().split(".")[0]).lower()
            elif row[col].lower().startswith(tuple(titles_nodot)):
                notitle = "".join(row[col].strip().split(" ")[1:]).replace(" ","")
                title = "".join(row[col].strip().split(" ")[0]).lower()
            else:
                notitle = row[col].replace(" ","")
                title = ""
            # Some district/ward just has title & (latin)number, or just number, thus need to insert the title "Quận"/"Phường" back
            if col=="district":
                df.loc[index, col] = "Quận"+notitle if notitle.isnumeric() else notitle
            elif col=="ward":
                df.loc[index, col] = "Phường"+notitle if notitle.isnumeric() else ("Phường"+notitle if notitle.upper()==notitle and len(notitle) < 4 else notitle) ##phườngIV
            else:
                df.loc[index, col] = notitle
        # Buffer matching keys by creating original administrative names
            df.loc[index, col+"_org"] = "" if notitle.isnumeric() and title!="" else ("" if notitle.upper()==notitle and len(notitle) < 4 and title!="" else title)
        df[col+"_org"] = df[col+"_org"].replace({"tp":"ThànhPhố","t":"Tỉnh","q":"Quận","h":"Huyện","tx":"ThịXã","p":"Phường","tt":"ThịTrấn","x":"Xã",
                                                 "thànhphố":"ThànhPhố","tỉnh":"Tỉnh","quận":"Quận","huyện":"Huyện","thịxã":"ThịXã","phường":"Phường",
                                                  "thịtrấn":"ThịTrấn","xã":"Xã"})
        df[col+"_org"] = df[col+"_org"] + df[col]
        df[col+"_org"] = df[col+"_org"].apply(insert_space)
        # Buffer matching keys by removing all diacritics
        df[col+"_en"] = df[col].apply(lambda x: unidecode(x).lower())
    return df

def exec(brand):
    # WCM store location
    wcm_stores = pd.read_excel(r"data\Winmart location.xlsx")
    # Some wards have changed names multiple times, while the GADM's boundaries only reflect admistratives before 2020
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="5549"].index, "ward"] = "VĩnhLạc" #instead of VĩnhBảo
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="3355"].index, "ward"] = "BìnhTrịĐôngB" #instead of BìnhTrịĐông
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="4939"].index, "ward"] = "TânMai" #instead of TamHiệp
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID.isin(["6398","6491"])].index, "ward"] = "QuyếtTiến" #instead of ĐoànKết
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID.isin(["3161","3160","3572"])].index, "ward"] = "PhụngCông" #instead of XuânQuan
    # Nghị quyết 130/NQ-CP[4] điều chỉnh: Thành lập các phường 1, 2, 3, 4, 5 thuộc thị xã Cai Lậy trên cơ sở giải thể thị trấn Cai Lậy
    # và điều chỉnh địa giới hành chính 2 xã Nhị Mỹ, Tân Bình
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="6411"].index, "ward"] = "Phường1" #instead of CaiLậy
    # Nghị định 156/2003/NĐ-CP[5] điều chỉnh 24 ha diện tích tự nhiên và 1.211 người của phường Phú Thọ về phường Phú Hòa quản lý
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="6693"].index, "ward"] = "PhúHòa" #instead of PhúThọ
    # Nghị định 156/2003/NĐ-CP[5] điều chỉnh 24 ha diện tích tự nhiên và 1.211 người của phường Phú Thọ về phường Phú Hòa quản lý
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="3104"].index, "ward"] = "XuânTảo" #instead of XuânĐỉnh
    # Vincom Mega Mall Ocean Park: wrong ward
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="1699"].index, "ward"] = "KiêuKỵ" #instead of TrâuQuỳ
    # Vincom Plaza Long Biên: wrong ward
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="1541"].index, "ward"] = "PhúcLợi" #instead of ViệtHưng
    # Khu đô thị Việt Hưng: wrong ward
    wcm_stores.loc[wcm_stores[wcm_stores.STORE_ID=="3182"].index, "ward"] = "ViệtHưng" #instead of GiangBiên
    # Create matching keys
    wcm_stores = adminkeys_to_match(wcm_stores, cols_to_fix=["city","district","ward"])

    # BHX store location
    bhx_stores = pd.read_excel(r"data\BHX_Stores.xlsx")
    bhx_stores = bhx_stores[bhx_stores.columns[[0,1,8,11,18,3,6,7,15,14,13]]]
    # Add up administrative names
    bhx_admin_list = flatten_adminDB(r"data\BHX_IdbLocationCommon.json")
    bhx_admin_list = adminkeys_to_match(bhx_admin_list, cols_to_fix=["city","district","ward"])
    bhx_stores = pd.merge(bhx_stores, bhx_admin_list, how="left", on=["provinceId","districtId","wardId"])

    return wcm_stores if brand=="Winmart" else bhx_stores