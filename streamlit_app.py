import streamlit as st
import pandas as pd
import geopandas
import folium
import shapely
from streamlit_folium import st_folium


@st.cache_data
def get_raw_colleges_data() -> pd.DataFrame:
    df = pd.read_parquet("data/colleges.parquet")
    return df


@st.cache_data
def get_colleges_data() -> geopandas.GeoDataFrame:
    name_mapping = {
        "INSTNM": "name",
        "CITY": "city",
        "STABBR": "state",
        "ZIP": "zipcode",
        "LATITUDE": "lat",
        "LONGITUDE": "lon",
        "INSTURL": "homepage",
    }
    df = get_raw_colleges_data()[name_mapping.keys()]
    df = df[df["LATITUDE"] != "NULL"]
    df["LATITUDE"] = df["LATITUDE"].astype("float")
    df["LONGITUDE"] = df["LONGITUDE"].astype("float")
    df = df.rename(columns=name_mapping)
    gdf = geopandas.GeoDataFrame(df, geometry=geopandas.points_from_xy(df.lon, df.lat))
    return gdf


@st.cache_data
def get_colleges_data_dictionary() -> pd.DataFrame:
    colleges = get_raw_colleges_data()
    columns = [
        "VARIABLE NAME",
        "NAME OF DATA ELEMENT",
        "dev-category",
        "developer-friendly name",
        "API data type",
        "LABEL",
        "SHOWN/USE ON SITE",
    ]
    df = pd.read_parquet("data/data_dictionary.parquet", columns=columns)
    df = df[df["VARIABLE NAME"].isin(colleges.columns)]
    return df


@st.cache_data
def get_nearest_colleges(lon: float, lat: float, limit: int) -> geopandas.GeoDataFrame:
    point = shapely.geometry.Point(lon, lat)
    gdf = get_colleges_data()
    gdf["distance"] = gdf.distance(point)
    return gdf.sort_values("distance").reset_index(drop=True).iloc[:limit]


st.set_page_config(
    page_title="Nearest Colleges", page_icon="🎓", initial_sidebar_state="collapsed"
)

st.header("Find Nearest Colleges")
with st.expander("What's This?"):
    st.write(
        """\
        Move around the map to find the nearest colleges to the center of the map!

        Defaults to 10, but open the sidebar on the left to increase or decrease this number.

        Inspiration for spoke design from examples such as [https://rkda.xyz/spoke/](https://rkda.xyz/spoke/) (by [@rukku](https://twitter.com/rukku)) built with [Turf JS](https://turfjs.org/).

        Data points come from U.S. College Scorecard Open Dataset (see the [official site](https://collegescorecard.ed.gov/) for better filtering and searching!)

        Built with ❤️ by [Gerard Bentley](https://gerardbentley.com)
"""
    )
number_of_colleges = st.sidebar.number_input("Number of Colleges", 1, 100, 10)

default_center = [34.101130680572346, -117.71258907392622]
m = folium.Map(location=default_center, zoom_start=15)
fg = folium.FeatureGroup(name="Seattle Locations")

lat, lon = st.session_state.get("center", default_center)
st.write(f"Lat, Lon: `{lat},{lon}`")
nearest_colleges = get_nearest_colleges(lon, lat, number_of_colleges)

for row in nearest_colleges.itertuples():
    fg.add_child(
        folium.Marker(
            [row.lat, row.lon],
            popup=[row.name],
            tooltip=row.name,
        ),
    )
    fg.add_child(
        folium.ColorLine(
            [[row.lat, row.lon], [lat, lon]],
            colors=nearest_colleges["distance"],
            weight=4,
        ),
    )

folium_data = st_folium(m, feature_group_to_add=fg, width=725)
folium_lat = folium_data.get("center").get("lat")
folium_lon = folium_data.get("center").get("lng")
if folium_lat != lat or folium_lon != lon:
    st.session_state["center"] = [folium_lat, folium_lon]
    st.experimental_rerun()

if (choice := folium_data["last_object_clicked"]) and choice != st.session_state.get(
    "last_object_clicked"
):
    st.session_state["last_object_clicked"] = choice
    chosen_college = (
        get_nearest_colleges(choice["lng"], choice["lat"], 1).iloc[0].to_dict()
    )
    st.session_state["chosen_college"] = chosen_college
    st.experimental_rerun()

if choice := st.session_state.get("chosen_college"):
    st.write(choice)

with st.expander("Nearest Colleges Data"):
    st.dataframe(
        nearest_colleges[[x for x in nearest_colleges.columns if x != "geometry"]]
    )

colleges_data_dictionary = get_colleges_data_dictionary()
with st.expander("colleges_data_dictionary"):
    st.dataframe(colleges_data_dictionary)


if st.checkbox("Show Raw College data"):
    st.dataframe(get_raw_colleges_data())
