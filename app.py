import streamlit as st
import pandas as pd
import altair as alt

# Set page configuration
st.set_page_config(page_title="McCombs Tuition Benchmark", layout="wide")

st.title("💡 Texas McCombs MBA Competitive Intelligence")
st.markdown("Evaluating UT Austin's competitive tuition footprint and peer-program content presence against the U.S. News Top 30.")

# 1. Load Data
@st.cache_data
def load_tuition_data():
    try:
        return pd.read_csv("mba_data.csv")
    except FileNotFoundError:
        st.error("Error: 'mba_data.csv' not found.")
        return pd.DataFrame()

@st.cache_data
def load_blog_data():
    try:
        return pd.read_csv("mba_blogs.csv")
    except FileNotFoundError:
        st.error("Error: 'mba_blogs.csv' not found.")
        return pd.DataFrame()

df = load_tuition_data()
blogs_df = load_blog_data()

tab1, tab2 = st.tabs(["💰 Tuition Benchmarking", "📰 Admissions Blog & RSS Tracker"])

# =====================================================================
# TAB 1: TUITION BENCHMARKING (unchanged from original)
# =====================================================================
with tab1:
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

# =====================================================================
# TAB 2: ADMISSIONS BLOG & RSS TRACKER
# =====================================================================
with tab2:
    st.markdown(
        "Tracks whether each U.S. News Top 20 MBA program runs a school-hosted admissions/student-life "
        "blog, and whether that blog exposes a working RSS feed you could pipe into a monitoring pipeline. "
        "Faculty-research feeds (e.g. Kellogg Insight, HBS Working Knowledge) are excluded — this tracks "
        "content relevant to marketing/admissions competitive intel specifically."
    )

    if not blogs_df.empty:
        status_order = [
            "Live - RSS Confirmed",
            "Live - No RSS Found",
            "Not Confirmed",
            "Likely Dormant",
            "Not Found",
            "Dead",
        ]
        status_colors = {
            "Live - RSS Confirmed": "#1a7f37",   # green
            "Live - No RSS Found": "#bf8700",    # amber
            "Not Confirmed": "#6e7781",          # gray
            "Likely Dormant": "#bf8700",         # amber
            "Not Found": "#cf222e",              # red
            "Dead": "#cf222e",                   # red
        }

        # --- Summary metrics ---
        counts = blogs_df["RSS Status"].value_counts()
        total_schools = len(blogs_df)
        live_rss = int(counts.get("Live - RSS Confirmed", 0))
        live_no_rss = int(counts.get("Live - No RSS Found", 0))
        dead_or_missing = total_schools - live_rss - live_no_rss

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Live RSS Feeds", f"{live_rss} / {total_schools}")
            st.markdown("Ready to pipe into a digest/monitoring pipeline today.")
        with m2:
            st.metric("Live Content, No Feed", f"{live_no_rss} / {total_schools}")
            st.markdown("Genuinely current admissions content — would need scraping instead of a feed.")
        with m3:
            st.metric("Dead / Not Found / Unconfirmed", f"{dead_or_missing} / {total_schools}")
            st.markdown("No usable school-hosted admissions blog located at time of research.")

        st.markdown("---")

        # --- Filter ---
        selected_statuses = st.multiselect(
            "Filter by status:",
            options=status_order,
            default=status_order,
        )
        view_df = blogs_df[blogs_df["RSS Status"].isin(selected_statuses)].sort_values("Rank")

        # --- Status breakdown chart ---
        st.subheader("Status Breakdown")
        status_chart_df = blogs_df["RSS Status"].value_counts().reindex(status_order).fillna(0).reset_index()
        status_chart_df.columns = ["RSS Status", "Count"]
        status_bar = (
            alt.Chart(status_chart_df)
            .mark_bar()
            .encode(
                x=alt.X("Count:Q", title="Number of Schools"),
                y=alt.Y("RSS Status:N", sort=status_order, title=""),
                color=alt.Color(
                    "RSS Status:N",
                    scale=alt.Scale(domain=list(status_colors.keys()), range=list(status_colors.values())),
                    legend=None,
                ),
            )
            .properties(height=220)
        )
        st.altair_chart(status_bar, use_container_width=True)

        st.markdown("---")

        # --- Detail table ---
        st.subheader("School-by-School Directory")

        def highlight_status(val):
            color = status_colors.get(val, "#000000")
            return f"color: {color}; font-weight: 600"

        styled = view_df.style.map(highlight_status, subset=["RSS Status"])

        st.dataframe(
            styled,
            column_order=["Rank", "School", "Blog Name", "Blog URL", "RSS Status", "Content Type", "Notes"],
            column_config={
                "Blog URL": st.column_config.LinkColumn("Blog URL", display_text="Visit ↗"),
            },
            use_container_width=True,
            hide_index=True,
            height=600,
        )

        st.caption(
            "Last verified via manual research. Re-check periodically — school CMS migrations "
            "(e.g. Yale SOM, Columbia) have silently killed feeds before."
        )
    else:
        st.info("Add `mba_blogs.csv` to the app directory to populate this tab.")
