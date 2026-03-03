import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NYC Airbnb & Subway Proximity",
    page_icon="🚇",
    layout="wide"
)

# ── Load data ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("data/airbnb_with_subway_features.csv")
    subway = pd.read_csv("data/MTA_Subway_Stations.csv")
    borough_map = {"M": "Manhattan", "Bk": "Brooklyn", "Q": "Queens", "Bx": "Bronx", "SI": "Staten Island"}
    subway["Borough_Full"] = subway["Borough"].map(borough_map)
    subway_clean = subway.drop_duplicates(subset=["GTFS Latitude", "GTFS Longitude"])
    with open("data/nyc-borough.geojson", "r") as f:
        borough_geo = json.load(f)
    return df, subway_clean, borough_geo

df, subway_clean, borough_geo = load_data()

# ── Sidebar filters ─────────────────────────────────────────────────────────
st.sidebar.title("Filters")

boroughs = st.sidebar.multiselect(
    "Borough",
    options=sorted(df["neighbourhood_group"].unique()),
    default=sorted(df["neighbourhood_group"].unique())
)

room_types = st.sidebar.multiselect(
    "Room Type",
    options=sorted(df["room_type"].unique()),
    default=sorted(df["room_type"].unique())
)

price_range = st.sidebar.slider(
    "Price Range ($ / night)",
    min_value=int(df["price_capped"].min()),
    max_value=int(df["price_capped"].max()),
    value=(int(df["price_capped"].min()), int(df["price_capped"].max()))
)

# Apply filters
mask = (
    df["neighbourhood_group"].isin(boroughs)
    & df["room_type"].isin(room_types)
    & df["price_capped"].between(*price_range)
)
fdf = df[mask]

st.sidebar.markdown("---")
st.sidebar.metric("Listings shown", f"{len(fdf):,}", f"of {len(df):,} total")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: INTRO & OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
st.title("Is Airbnb Listing Price Associated with Subway Proximity in NYC?")
st.markdown("""
**DATA 227 — Data Visualization Project | Winter 2026**
*Cristian Garcia, Avital Mintz, Vedant Dangayach*

---

New York City's subway system connects millions of residents and visitors to every corner of the city.
For short-term rental guests, proximity to public transit can make or break a stay. But does the market
actually price in subway access? We merged **{:,} Airbnb listings** with **{:,} MTA subway station
locations** to find out.
""".format(len(df), len(subway_clean)))

# Key metrics row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Median Price", f"${fdf['price'].median():,.0f}")
col2.metric("Avg Stations (0.5 mi)", f"{fdf['stations_05mi'].mean():.1f}")
col3.metric("Listings", f"{len(fdf):,}")
col4.metric("Neighborhoods", f"{fdf['neighbourhood'].nunique()}")

# ── Interactive Map ──────────────────────────────────────────────────────────
st.markdown("## Interactive Map")
st.markdown("Airbnb listings colored by nightly price, with subway stations shown as blue markers.")

map_sample = fdf.sample(n=min(5000, len(fdf)), random_state=42) if len(fdf) > 5000 else fdf

fig_map = px.scatter_mapbox(
    map_sample,
    lat="latitude", lon="longitude",
    color="price_capped",
    color_continuous_scale="YlOrRd",
    opacity=0.5,
    hover_name="name",
    hover_data={
        "price": ":$.0f",
        "neighbourhood_group": True,
        "room_type": True,
        "stations_05mi": True,
        "latitude": False, "longitude": False, "price_capped": False
    },
    labels={"price_capped": "Price ($)", "stations_05mi": "Stations (0.5mi)"},
)
fig_map.add_trace(go.Scattermapbox(
    lat=subway_clean["GTFS Latitude"],
    lon=subway_clean["GTFS Longitude"],
    mode="markers",
    marker=dict(size=5, color="#1E88E5", opacity=0.7),
    name="Subway Stations",
    text=subway_clean["Stop Name"],
    hoverinfo="text"
))
fig_map.update_layout(
    mapbox_style="carto-positron",
    mapbox_center={"lat": 40.7128, "lon": -74.0060},
    mapbox_zoom=10,
    height=600,
    margin=dict(l=0, r=0, t=0, b=0)
)
st.plotly_chart(fig_map, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: DATA OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("## Data Overview")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### Price Distribution by Borough")
    fig_box = px.box(
        fdf, x="neighbourhood_group", y="price_capped",
        color="neighbourhood_group",
        category_orders={"neighbourhood_group": fdf.groupby("neighbourhood_group")["price_capped"]
                         .median().sort_values(ascending=False).index.tolist()},
        labels={"price_capped": "Price ($/night)", "neighbourhood_group": "Borough"},
    )
    fig_box.update_layout(showlegend=False, height=450)
    st.plotly_chart(fig_box, use_container_width=True)

with col_b:
    st.markdown("### Room Type Composition by Borough")
    room_counts = fdf.groupby(["neighbourhood_group", "room_type"]).size().reset_index(name="count")
    fig_room = px.bar(
        room_counts, x="neighbourhood_group", y="count", color="room_type",
        labels={"count": "Listings", "neighbourhood_group": "Borough", "room_type": "Room Type"},
        barmode="stack"
    )
    fig_room.update_layout(height=450)
    st.plotly_chart(fig_room, use_container_width=True)

# Subway density
col_c, col_d = st.columns(2)

with col_c:
    st.markdown("### Subway Stations by Borough")
    station_by_borough = subway_clean["Borough_Full"].value_counts().reset_index()
    station_by_borough.columns = ["Borough", "Stations"]
    fig_stn = px.bar(station_by_borough, x="Borough", y="Stations",
                     color="Borough", labels={"Stations": "Station Locations"})
    fig_stn.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_stn, use_container_width=True)

with col_d:
    st.markdown("### Avg Stations within 0.5 mi per Listing")
    avg_stn = fdf.groupby("neighbourhood_group")["stations_05mi"].mean().reset_index()
    avg_stn.columns = ["Borough", "Avg Stations"]
    fig_avg = px.bar(avg_stn.sort_values("Avg Stations", ascending=False),
                     x="Borough", y="Avg Stations", color="Borough")
    fig_avg.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_avg, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: CORE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("## Core Analysis: Price vs. Subway Proximity")
st.markdown("""
The central question: **does having more subway stations nearby correlate with higher Airbnb prices?**
Below we examine this at multiple levels — overall, by borough, and by neighborhood.
""")

# Binned bar chart
st.markdown("### Average Price by Number of Nearby Stations (0.5 mi)")
bin_stats = fdf.groupby("station_bin", observed=True).agg(
    mean_price=("price_capped", "mean"),
    median_price=("price_capped", "median"),
    count=("price_capped", "count")
).reset_index()

metric_choice = st.radio("Metric", ["Median", "Mean"], horizontal=True, key="metric_radio")
price_col = "median_price" if metric_choice == "Median" else "mean_price"

fig_bins = px.bar(
    bin_stats, x="station_bin", y=price_col,
    text="count",
    labels={"station_bin": "Stations within 0.5 mi", price_col: f"{metric_choice} Price ($)",
            "count": "Listings"},
    color=price_col, color_continuous_scale="YlOrRd"
)
fig_bins.update_traces(texttemplate="n=%{text:,}", textposition="outside")
fig_bins.update_layout(height=450)
st.plotly_chart(fig_bins, use_container_width=True)

# By borough facet
st.markdown("### Price vs. Stations — By Borough")
st.markdown("Controlling for borough removes the biggest confound. Within each borough, "
            "how does subway access relate to price?")

borough_means = fdf.groupby(["neighbourhood_group", "stations_05mi"]).agg(
    mean_price=("price_capped", "mean"),
    count=("price_capped", "count")
).reset_index()
# Only show station counts with enough data
borough_means = borough_means[borough_means["count"] >= 10]

fig_facet = px.line(
    borough_means, x="stations_05mi", y="mean_price",
    color="neighbourhood_group", markers=True,
    labels={"stations_05mi": "Stations within 0.5 mi", "mean_price": "Mean Price ($)",
            "neighbourhood_group": "Borough"},
    title="Mean Price by Station Count (min 10 listings per point)"
)
fig_facet.update_layout(height=500)
st.plotly_chart(fig_facet, use_container_width=True)

# Distance to nearest station
st.markdown("### Price by Distance to Nearest Station")
fig_dist = px.box(
    fdf.dropna(subset=["dist_bin"]),
    x="dist_bin", y="price_capped",
    color="dist_bin",
    category_orders={"dist_bin": ["<0.1 mi", "0.1-0.25 mi", "0.25-0.5 mi", "0.5-1 mi", ">1 mi"]},
    labels={"dist_bin": "Distance to Nearest Station", "price_capped": "Price ($/night)"},
)
fig_dist.update_layout(showlegend=False, height=450)
st.plotly_chart(fig_dist, use_container_width=True)

# ── Correlation heatmap ──────────────────────────────────────────────────────
st.markdown("### Correlation Heatmap")
corr_cols = ["price_capped", "stations_05mi", "stations_1mi",
             "nearest_station_miles", "bedrooms", "beds", "rating",
             "number_of_reviews", "availability_365"]
corr_labels = ["Price", "Stations (0.5mi)", "Stations (1mi)",
               "Nearest Stn (mi)", "Bedrooms", "Beds", "Rating",
               "Reviews", "Availability"]
corr_matrix = fdf[corr_cols].corr().round(2)
corr_matrix.index = corr_labels
corr_matrix.columns = corr_labels

fig_corr = px.imshow(
    corr_matrix, text_auto=True, color_continuous_scale="RdBu_r",
    zmin=-1, zmax=1, aspect="auto"
)
fig_corr.update_layout(height=550)
st.plotly_chart(fig_corr, use_container_width=True)

# ── Neighborhood bubble chart ────────────────────────────────────────────────
st.markdown("### Neighborhood-Level View")
st.markdown("Each bubble is a neighborhood. Size = number of listings.")

nbhd = fdf.groupby("neighbourhood").agg(
    median_price=("price", "median"),
    mean_stations=("stations_05mi", "mean"),
    count=("price", "count"),
    borough=("neighbourhood_group", "first")
).reset_index()
nbhd = nbhd[nbhd["count"] >= 20]

fig_nbhd = px.scatter(
    nbhd, x="mean_stations", y="median_price",
    size="count", color="borough", hover_name="neighbourhood",
    labels={"mean_stations": "Avg Stations within 0.5 mi",
            "median_price": "Median Price ($)",
            "count": "Listings", "borough": "Borough"},
    size_max=40, opacity=0.7
)
fig_nbhd.update_layout(height=550)
st.plotly_chart(fig_nbhd, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: CHOROPLETH
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("## Choropleth: Median Price by Borough")

borough_prices = fdf.groupby("neighbourhood_group").agg(
    median_price=("price", "median"),
    mean_price=("price", "mean"),
    listing_count=("price", "count"),
    median_stations=("stations_05mi", "median")
).reset_index()

fig_choro = px.choropleth_mapbox(
    borough_prices,
    geojson=borough_geo,
    locations="neighbourhood_group",
    featureidkey="properties.name",
    color="median_price",
    color_continuous_scale="YlOrRd",
    hover_data={"mean_price": ":$.0f", "listing_count": ":,", "median_stations": True},
    labels={"median_price": "Median Price ($)", "mean_price": "Mean Price ($)",
            "listing_count": "Listings", "median_stations": "Median Stations (0.5mi)"},
)
fig_choro.update_layout(
    mapbox_style="carto-positron",
    mapbox_center={"lat": 40.7128, "lon": -74.0060},
    mapbox_zoom=9.5,
    height=550,
    margin=dict(l=0, r=0, t=0, b=0)
)
st.plotly_chart(fig_choro, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: REGRESSION RESULTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("## Statistical Analysis: OLS Regression")
st.markdown("""
We estimate three OLS regression models to test whether subway proximity predicts Airbnb price,
progressively adding controls following a DAG-based causal framework:

- **Model 1:** Price ~ Stations *(bivariate)*
- **Model 2:** Price ~ Stations + Borough
- **Model 3:** Price ~ Stations + Borough + Room Type + Bedrooms + Beds
""")

# Run regressions on full (unfiltered) data for stable estimates
import statsmodels.api as sm_api

reg_df = df[["price_capped", "stations_05mi", "neighbourhood_group",
             "room_type", "bedrooms", "beds"]].dropna().copy()
reg_df["bedrooms"] = pd.to_numeric(reg_df["bedrooms"], errors="coerce")
reg_df["beds"] = pd.to_numeric(reg_df["beds"], errors="coerce")
reg_df = reg_df.dropna()
reg_df = pd.get_dummies(reg_df, columns=["neighbourhood_group", "room_type"], drop_first=True)
for c in reg_df.columns:
    reg_df[c] = reg_df[c].astype(float)

y = reg_df["price_capped"]
borough_cols = [c for c in reg_df.columns if c.startswith("neighbourhood_group_")]
room_cols = [c for c in reg_df.columns if c.startswith("room_type_")]

X1 = sm_api.add_constant(reg_df[["stations_05mi"]])
m1 = sm_api.OLS(y, X1).fit()

X2 = sm_api.add_constant(reg_df[["stations_05mi"] + borough_cols])
m2 = sm_api.OLS(y, X2).fit()

X3 = sm_api.add_constant(reg_df[["stations_05mi", "bedrooms", "beds"] + borough_cols + room_cols])
m3 = sm_api.OLS(y, X3).fit()

# Display results
r1, r2, r3 = st.columns(3)
r1.metric("Model 1 (bivariate)", f"${m1.params['stations_05mi']:.2f}/station",
          f"R² = {m1.rsquared:.3f}")
r2.metric("Model 2 (+Borough)", f"${m2.params['stations_05mi']:.2f}/station",
          f"R² = {m2.rsquared:.3f}")
r3.metric("Model 3 (Full)", f"${m3.params['stations_05mi']:.2f}/station",
          f"R² = {m3.rsquared:.3f}")

# Coefficient comparison chart
coef_data = pd.DataFrame({
    "Model": ["1: Bivariate", "2: + Borough", "3: Full Controls"],
    "Coefficient": [m1.params["stations_05mi"], m2.params["stations_05mi"], m3.params["stations_05mi"]],
    "CI_low": [m1.conf_int().loc["stations_05mi", 0],
               m2.conf_int().loc["stations_05mi", 0],
               m3.conf_int().loc["stations_05mi", 0]],
    "CI_high": [m1.conf_int().loc["stations_05mi", 1],
                m2.conf_int().loc["stations_05mi", 1],
                m3.conf_int().loc["stations_05mi", 1]],
})

fig_coef = go.Figure()
fig_coef.add_trace(go.Bar(
    y=coef_data["Model"], x=coef_data["Coefficient"],
    orientation="h",
    marker_color=["#2196F3", "#FF9800", "#4CAF50"],
    error_x=dict(
        type="data",
        symmetric=False,
        array=coef_data["CI_high"] - coef_data["Coefficient"],
        arrayminus=coef_data["Coefficient"] - coef_data["CI_low"]
    )
))
fig_coef.add_vline(x=0, line_dash="dash", line_color="black")
fig_coef.update_layout(
    title="Coefficient on 'Stations within 0.5 mi' Across Models",
    xaxis_title="$ per additional station (95% CI)",
    height=350
)
st.plotly_chart(fig_coef, use_container_width=True)

st.markdown(f"""
**Interpretation:** Each additional subway station within 0.5 miles is associated with a
**${m3.params['stations_05mi']:.2f}** change in nightly price, after controlling for borough,
room type, and listing size.
""")

with st.expander("Full Model 3 Regression Table"):
    st.text(m3.summary().as_text())

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: CONCLUSIONS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("## Summary & Limitations")

st.markdown("""
### Key Findings

1. **Borough dominates pricing.** Manhattan has the highest prices *and* the densest subway coverage,
   creating a strong confound.
2. **Raw correlation is positive** — more subway stations nearby correlates with higher prices — but
   much of this is driven by borough.
3. **After controlling for borough, room type, and size,** the relationship between subway proximity
   and price is revealed more clearly by the regression.
4. **Room type and listing size** are the strongest individual predictors of price.

### Limitations

- **Observational data** — we cannot claim causation. Subway stations correlate with other
  neighborhood amenities (restaurants, nightlife) that also drive price.
- **Missing variables** — listing quality, photos, specific amenities, and seasonality are not
  captured.
- **Cross-sectional** — a single snapshot in time; prices change seasonally.
- **Distance metric** — straight-line distance differs from walking distance; actual transit
  accessibility depends on service frequency.

### Future Directions

- Incorporate time-series data for seasonal analysis
- Add neighborhood-level controls (median income, walkability, crime)
- Use natural experiments (new station openings) for causal inference
""")

st.markdown("---")
st.markdown("""
### Data Sources

1. [NYC Airbnb Listings (Inside Airbnb / Kaggle)](https://www.kaggle.com/datasets/vrindakallu/new-york-dataset)
2. [MTA Subway Stations (Data.gov)](https://catalog.data.gov/dataset/mta-subway-stations)
3. [NYC Borough Boundaries (GeoJSON)](https://data.insideairbnb.com/united-states/ny/new-york-city/)
""")
