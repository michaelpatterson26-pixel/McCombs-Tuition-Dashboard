import streamlit as st
import pandas as pd
import altair as alt
import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime
import re

# Set page configuration
st.set_page_config(page_title="McCombs Tuition Benchmark", layout="wide")

st.title("💡 Texas McCombs MBA Competitive Intelligence")
st.markdown("Evaluating UT Austin's competitive tuition footprint and peer-program content presence against the U.S. News Top 30.")

# =====================================================================
# DATA LOADERS
# =====================================================================
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

def strip_html(text):
    """Light HTML stripper for RSS summaries that include markup."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8217;", "'").replace("&#8216;", "'")
    text = text.replace("&#8220;", '"').replace("&#8221;", '"').replace("&#8230;", "...")
    return text.strip()

def parse_entry_date(entry):
    """Try several fields/formats; fall back to None if nothing parses."""
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime(*val[:6])
            except Exception:
                pass
    for key in ("published", "updated"):
        val = entry.get(key)
        if val:
            try:
                return parsedate_to_datetime(val).replace(tzinfo=None)
            except Exception:
                pass
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_feed_entries(school, feed_url, max_items=6):
    """Fetch and parse one RSS feed. Returns a list of dicts, or an error string."""
    try:
        parsed = feedparser.parse(feed_url)
        if parsed.bozo and not parsed.entries:
            return f"error: could not parse feed ({parsed.bozo_exception})"
        if not parsed.entries:
            return "error: feed returned zero entries"

        items = []
        for entry in parsed.entries[:max_items]:
            items.append({
                "school": school,
                "title": entry.get("title", "(untitled)"),
                "link": entry.get("link", feed_url),
                "date": parse_entry_date(entry),
                "summary": strip_html(entry.get("summary", entry.get("description", "")))[:280],
            })
        return items
    except Exception as e:
        return f"error: {e}"

@st.cache_data(ttl=3600, show_spinner=False)
def build_combined_feed(blogs_df):
    """Fetch every confirmed feed URL and combine into one sorted list."""
    all_items = []
    fetch_errors = {}
    feed_rows = blogs_df[blogs_df["RSS Feed URL"].notna() & (blogs_df["RSS Feed URL"] != "")]

    for _, row in feed_rows.iterrows():
        result = fetch_feed_entries(row["School"], row["RSS Feed URL"])
        if isinstance(result, str):
            fetch_errors[row["School"]] = result
        else:
            all_items.extend(result)

    # Sort newest first; items with no parseable date sink to the bottom
    all_items.sort(key=lambda x: x["date"] or datetime.min, reverse=True)
    return all_items, fetch_errors


df = load_tuition_data()
blogs_df = load_blog_data()

tab1, tab2 = st.tabs(["💰 Tuition Benchmarking", "📰 Admissions Blog Feed"])

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
# TAB 2: ADMISSIONS BLOG FEED (live, scrollable)
# =====================================================================
with tab2:
    st.markdown(
        "Live pull of recent posts from peer-program admissions/student-life blogs that expose a "
        "working RSS feed. Sorted newest first. Refreshes hourly."
    )

    if blogs_df.empty:
        st.info("Add `mba_blogs.csv` to the app directory to populate this tab.")
    else:
        feed_schools = blogs_df[blogs_df["RSS Feed URL"].notna() & (blogs_df["RSS Feed URL"] != "")]["School"].tolist()

        if not feed_schools:
            st.warning("No schools currently have a populated 'RSS Feed URL' in mba_blogs.csv.")
        else:
            with st.spinner("Fetching latest posts..."):
                combined_feed, fetch_errors = build_combined_feed(blogs_df)

            top_col1, top_col2 = st.columns([3, 1])
            with top_col1:
                selected_schools = st.multiselect(
                    "Filter by school:",
                    options=sorted(feed_schools),
                    default=sorted(feed_schools),
                )
            with top_col2:
                if st.button("🔄 Refresh now", use_container_width=True):
                    fetch_feed_entries.clear()
                    build_combined_feed.clear()
                    st.rerun()

            visible_items = [item for item in combined_feed if item["school"] in selected_schools]

            st.caption(f"Showing {len(visible_items)} posts from {len(selected_schools)} school(s).")

            if fetch_errors:
                with st.expander(f"⚠️ {len(fetch_errors)} feed(s) failed to load — click for details"):
                    for school, err in fetch_errors.items():
                        st.markdown(f"- **{school}**: {err}")
                    st.caption(
                        "A failure here usually means the feed URL in mba_blogs.csv needs updating — "
                        "school blogs occasionally migrate platforms and silently break their old feed path."
                    )

            st.markdown("---")

            # --- Scrollable feed list ---
            if not visible_items:
                st.info("No posts to show for the current filter.")
            else:
                feed_container = st.container(height=700)
                with feed_container:
                    for item in visible_items:
                        date_str = item["date"].strftime("%b %d, %Y") if item["date"] else "Date unknown"
                        st.markdown(f"##### [{item['title']}]({item['link']})")
                        st.caption(f"**{item['school']}** · {date_str}")
                        if item["summary"]:
                            st.write(item["summary"] + ("…" if len(item["summary"]) >= 280 else ""))
                        st.markdown("---")

        # --- Status tracker, tucked below as supporting context ---
        with st.expander("📋 Full school-by-school status directory (including schools with no live feed)"):
            status_order = [
                "Live - RSS Confirmed",
                "Live - No RSS Found",
                "Not Confirmed",
                "Likely Dormant",
                "Not Found",
                "Dead",
            ]
            status_colors = {
                "Live - RSS Confirmed": "#1a7f37",
                "Live - No RSS Found": "#bf8700",
                "Not Confirmed": "#6e7781",
                "Likely Dormant": "#bf8700",
                "Not Found": "#cf222e",
                "Dead": "#cf222e",
            }

            counts = blogs_df["RSS Status"].value_counts()
            total_schools = len(blogs_df)
            live_rss = int(counts.get("Live - RSS Confirmed", 0))
            live_no_rss = int(counts.get("Live - No RSS Found", 0))
            dead_or_missing = total_schools - live_rss - live_no_rss

            m1, m2, m3 = st.columns(3)
            m1.metric("Live RSS Feeds", f"{live_rss} / {total_schools}")
            m2.metric("Live Content, No Feed", f"{live_no_rss} / {total_schools}")
            m3.metric("Dead / Not Found / Unconfirmed", f"{dead_or_missing} / {total_schools}")

            def highlight_status(val):
                color = status_colors.get(val, "#000000")
                return f"color: {color}; font-weight: 600"

            styled = blogs_df.sort_values("Rank").style.map(highlight_status, subset=["RSS Status"])
            st.dataframe(
                styled,
                column_order=["Rank", "School", "Blog Name", "Blog URL", "RSS Status", "RSS Feed URL", "Content Type", "Notes"],
                column_config={
                    "Blog URL": st.column_config.LinkColumn("Blog URL", display_text="Visit ↗"),
                },
                use_container_width=True,
                hide_index=True,
                height=500,
            )
            st.caption(
                "Last verified via manual research. Re-check periodically — school CMS migrations "
                "(e.g. Yale SOM, Columbia) have silently killed feeds before."
            )
