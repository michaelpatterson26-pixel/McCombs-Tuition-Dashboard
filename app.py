import streamlit as st
import pandas as pd
import altair as alt

# Set page configuration
st.set_page_config(page_title="McCombs Tuition Benchmark", layout="wide")

st.title("💡 Texas McCombs MBA Tuition Benchmarking Tool")
st.markdown("Evaluating UT Austin's competitive tuition and total cost of attendance (COA) footprint against the U.S. News Top 30.")

# 1. Load Data
@st.cache_data
def load_data():
    try:
        return pd.read_csv("mba_data.csv")
    except FileNotFoundError:
        st.error("Error: 'mba_data.csv' not found.")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # 2. Extract McCombs Baseline Data
    mccombs_row = df[df["School"].str.contains("UT Austin")]
    
    if mccombs_row.empty:
        st.error("Could not find 'UT Austin (McCombs)' in the dataset. Please check your CSV.")
    else:
        mccombs_tuition = mccombs_row["Annual Tuition"].values[0]
        mccombs_coa = mccombs_row["Total Annual COA"].values[0]
        mccombs_hike = mccombs_row["YOY Increase (%)"].values[0]

        # Calculate averages for comparisons
        market_tuition_avg = df['Annual Tuition'].mean()
        market_coa_avg = df['Total Annual COA'].mean()
        market_hike_avg = df['YOY Increase (%)'].mean()

        # 3. Calculate Deltas relative to McCombs
        df["Tuition Premium ($)"] = df["Annual Tuition"] - mccombs_tuition
        df["COA Premium ($)"] = df["Total Annual COA"] - mccombs_coa

        # 4. Top Level Focus Metrics (Left-justified with Burnt Orange Pop)
        col1, col2, col3 = st.columns(3)
        with col1:
            tuition_gap = int(market_tuition_avg - mccombs_tuition)
            st.metric(
                label="Annual Tuition Advantage", 
                value=f"${tuition_gap:,} Cheaper", 
                delta=f"McCombs Baseline: ${mccombs_tuition:,}",
                delta_color="off"
            )
            st.markdown(f"**Status:** UT saves you :orange[${tuition_gap:,}] vs the Top 30 average.")
            
        with col2:
            coa_gap = int(market_coa_avg - mccombs_coa)
            st.metric(
                label="Total COA Advantage", 
                value=f"${coa_gap:,} Cheaper", 
                delta=f"McCombs Baseline: ${mccombs_coa:,}",
                delta_color="off"
            )
            st.markdown(f"**Status:** UT saves you :orange[${coa_gap:,}] all-in per year.")
            
        with col3:
            hike_gap = mccombs_hike - market_hike_avg
            sign = "" if hike_gap < 0 else "+"
            
            # FIXED BLOCK: We format the string safely BEFORE passing it to st.markdown
            hike_diff_string = f"{abs(hike_gap):.2f}%"
            if hike_gap <= 0:
                status_text = f"**Status:** Tuitions are growing :green[{hike_diff_string}] slower at UT."
            else:
                status_text = f"**Status:** Tuitions are growing :red[{hike_diff_string}] faster at UT."
            
            st.metric(
                label="Rate Hike Differential", 
                value=f"{sign}{hike_gap:.2f}% vs Market", 
                delta=f"McCombs Increase: {mccombs_hike}%",
                delta_color="off"
            )
            st.markdown(status_text)

        st.markdown("---")

        # 5. Strategic Peer Group Filters
        st.sidebar.header("Strategic Peer Filters")
        
        peer_group = st.sidebar.radio(
            "Select Competitive Lens:",
            options=["All Top 30", "Direct Public Peers", "Texas Regional Competitors", "Top 15-20 Bracket"]
        )

        # Filter logic based on peer groups (UCLA included)
        if peer_group == "Direct Public Peers":
            filtered_df = df[df["School"].isin([
                "UT Austin (McCombs)", 
                "UC Berkeley (Haas)", 
                "UVA (Darden)", 
                "Michigan (Ross)", 
                "UCLA (Anderson)", 
                "UNC (Kenan-Flagler)", 
                "UW (Foster)"
            ])]
        elif peer_group == "Texas Regional Competitors":
            filtered_df = df[df["School"].isin(["UT Austin (McCombs)", "Rice University (Jones)", "UT Dallas (Jindal)"])]
        elif peer_group == "Top 15-20 Bracket":
            filtered_df = df[(df["Rank"] >= 13) & (df["Rank"] <= 22)]
        else:
            filtered_df = df

        # Prepare and sort data for visual presentation
        chart_df = filtered_df.sort_values(by="Tuition Premium ($)").reset_index()

        # 6. Visualizing the Price Delta 
        st.subheader("The Value Gap: How Much More/Less Do Peer Programs Cost?")
        st.markdown("Bars showing **above $0** represent programs more expensive than McCombs. Bars **below $0** are cheaper.")
        
        altair_chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X("School:N", sort=None, title="University Program"),
                y=alt.Y("Tuition Premium ($):Q", title="Tuition Delta (vs McCombs)", axis=alt.Axis(format="$,.0f"))
            )
            .properties(height=400)
        )
        
        st.altair_chart(altair_chart, use_container_width=True)

        st.markdown("---")

        # 7. Enhanced Data Table
        st.subheader("Granular Benchmarking Directory")
        st.dataframe(
            filtered_df.style.format({
                "Annual Tuition": "${:,.0f}",
                "Total Annual COA": "${:,.0f}",
                "YOY Increase (%)": "{:.2f}%",
                "Tuition Premium ($)": "${:+,.0f}",
                "COA Premium ($)": "${:+,.0f}"
            }),
            column_order=["Rank", "School", "Location", "Annual Tuition", "Tuition Premium ($)", "Total Annual COA", "COA Premium ($)", "YOY Increase (%)"],
            use_container_width=True,
            hide_index=True
        )