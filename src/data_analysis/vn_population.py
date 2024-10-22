import pandas as pd

"""
Source of population data: http://portal.thongke.gov.vn/khodulieudanso2019/Default.aspx
"""

def read_excel_pivot(path, row_to_skip, newcols, cols_remove_agg, row_agg):
    df = pd.read_excel(path, skiprows=row_to_skip, header=0)
    # Fill up empty Group by level rows
    cols=df.columns[[0,1]]
    df.loc[:,cols] = df.loc[:,cols].ffill()
    # Rename columns
    df = df.set_axis(newcols, axis=1)
    # Remove excess spaces
    for col in newcols:
        df[col] = df[col].apply(lambda x: x.replace("  "," ").strip().title() if type(x)=="str" else x)
    # Remove all aggregated rows
    for col in cols_remove_agg:
        df = df[~df[col].str.contains(row_agg, na=False)]
    return df

def exec_allpop():
    allpop_ward = read_excel_pivot(path=r"data\Population data\Population by Urban (Ward).xlsx",
                                   row_to_skip=2,
                                   newcols=['city','district','ward','total','urban','rural'],
                                   cols_remove_agg=['city','district'],
                                   row_agg='Tổng số'
                                   )
    return allpop_ward

def exec_youngpop():
    pop_age_dist = read_excel_pivot(path=r"C:\Users\huongptt5\Documents\Finance insights\Streamlit\data\Population data\Population by Age & Urban (District).xlsx",
                                    row_to_skip=3,
                                    newcols=["city","district","total",
                                            "total_urban","0-4_urban","5-9_urban","10-14_urban","15-19_urban","20-24_urban","25-29_urban",
                                            "30-34_urban","35-39_urban","40-44_urban","45-49_urban","50-54_urban","55-59_urban","60-64_urban",
                                            "65-69_urban","70-74_urban","75-79_urban","80-84_urban","85+_urban",
                                            "total_rural","0-4_urban","5-9_rural","10-14_rural","15-19_rural","20-24_rural","25-29_rural",
                                            "30-34_rural","35-39_rural","40-44_rural","45-49_rural","50-54_rural","55-59_rural","60-64_rural",
                                            "65-69_rural","70-74_rural","75-79_rural","80-84_rural","85+_rural"],
                                    cols_remove_agg=["city"],
                                    row_agg="Tổng số"
                                    )
    pop_age_dist["15-34_urban"] = pop_age_dist["15-19_urban"] + pop_age_dist["20-24_urban"] + pop_age_dist["25-29_urban"] + pop_age_dist["30-34_urban"]
    pop_age_dist["15-34_rural"] = pop_age_dist["15-19_rural"] + pop_age_dist["20-24_rural"] + pop_age_dist["25-29_rural"]+ pop_age_dist["30-34_rural"]
    youngpop_dist = pop_age_dist[["city","district","total","15-34_urban","15-34_rural"]]
    return youngpop_dist