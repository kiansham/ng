from __future__ import annotations
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import json
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
from streamlit_echarts import st_echarts
import streamlit_shadcn_ui as ui 
from streamlit_tile import streamlit_tile
import streamlit_plotly_events as plotly_events
from config import Config, CHART_CONFIGS, ENHANCED_CSS, NAV_STYLES, PAGES_CONFIG
from utils import *

st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon=Config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown('<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">', unsafe_allow_html=True)
st.markdown(ENHANCED_CSS, unsafe_allow_html=True)

def refresh_data():
    df, choices = load_db()
    df = fix_column_names(df)
    st.session_state.validator = DataValidator(choices)
    st.session_state.FULL_DATA = get_latest_view(df)
    st.session_state.DATA = st.session_state.FULL_DATA.copy()
    st.session_state.data_refreshed = True

def sidebar_filters(df):
    st.markdown(
        f'<span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:18px;">{Config.HEADER_ICONS["filter"]}</span>'
        f'<span style="vertical-align:middle;font-size:18px;font-weight:600;">Filters</span>',
        unsafe_allow_html=True
    )

    with st.expander("⚠️ Alerts", expanded=False):
        st.caption("Select to Show Upcoming Events")
        col1, col2 = st.columns(2)
        show_urgent = col1.toggle("Urgent", value=False)
        show_upcoming = col2.toggle("Upcoming", value=False)

    with st.expander("🏛️ Company Filters", expanded=False):
        companies = st.multiselect("Company", sorted(df.get("company_name", pd.Series()).unique()))
        region = st.multiselect("Region", get_lookup_values("region"))
        
        existing = df['country'].dropna().unique() if 'country' in df.columns else []
        all_countries = sorted(set(get_lookup_values("country") + list(existing)))
        country = st.multiselect("Country", all_countries)
        sector = st.multiselect("GICS Sector", get_lookup_values("gics_sector"))
        
    with st.expander("🗣️ Engagement Type", expanded=False):
        progs = st.multiselect("Program", get_lookup_values("program"))
        themes = st.multiselect("Theme", get_lookup_values("theme"))
        objectives = st.multiselect("Objective", get_lookup_values("objective"))
        esg_opt = st.radio("ESG Focus", ["All", "E", "S", "G"], horizontal=True)
        
    esg = ["e", "s", "g"] if esg_opt == "All" else [esg_opt.lower()]
    
    with st.expander("👥 Engagement Status", expanded=False):
        mile = st.multiselect("Milestone", get_lookup_values("milestone"))
        status = st.multiselect("Status", get_lookup_values("milestone_status"))

    return progs, sector, region, country, mile, status, esg, show_urgent, show_upcoming, companies, themes, objectives

def apply_filters(df, filters):
    if df.empty:
        return df

    progs, sector, region, country, mile, status, esg, urgent, upcoming, companies, themes, objectives = filters
    
    filter_map = {
        "program": progs, "gics_sector": sector, "region": region,
        "country": country, "milestone": mile, "milestone_status": status, 
        "company_name": companies, "theme": themes, "objective": objectives
    }
    
    for col, vals in filter_map.items():
        if vals and col in df.columns:
            df = df[df[col].isin(vals)]
    
    if esg and all(c in df.columns for c in esg):
        df = df[df[esg].any(axis=1)]
    
    if urgent and "urgent" in df.columns:
        df = df[df["urgent"]]
        
    if upcoming and "next_action_date" in df.columns:
        days_ahead = (pd.to_datetime(df["next_action_date"]) - pd.Timestamp.now()).dt.days
        df = df[days_ahead.between(0, 30)]
    
    return df

def dashboard():
    data = st.session_state['DATA']
    
    if data.empty:
        st.warning("No engagement data available.")
        return

    today = pd.Timestamp.now().normalize()
    days_ahead = (pd.to_datetime(data.get("next_action_date")) - today).dt.days
    week_tasks = data[days_ahead.between(0, 6)]
    month_tasks = data[days_ahead.between(7, 30)]
    
    col1, col2 = st.columns(2)
    col1.markdown(f'<div class="alert-urgent"><strong>📅 {len(week_tasks)} Meetings This Week</strong><br>Within 7 days</div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="alert-warning"><strong>🗓️ {len(month_tasks)} Meetings This Month</strong><br>Within 30 days</div>', unsafe_allow_html=True)

    render_icon_header(Config.HEADER_ICONS["metrics"], "Key Metrics")
    
    total = len(data)
    excluded = ["not started", "verified", "success", "cancelled"]
    active = (~data["milestone"].str.lower().isin(excluded)).sum() if "milestone" in data.columns else 0
    
    completed_list = ["success", "full disclosure", "partial disclosure", "verified"]
    completed = data["milestone"].str.lower().isin(completed_list).sum() if "milestone" in data.columns else 0
    
    success_list = ["Success", "Full Disclosure", "Partial Disclosure", "Verified"]
    success = data["milestone"].isin(success_list).sum() if "milestone" in data.columns else 0
    success_rate = round(success / total * 100) if total > 0 else 0
    
    not_started = data["milestone"].str.lower().eq("not started").sum() if "milestone" in data.columns else 0
    failed = data["milestone"].str.lower().eq("cancelled").sum() if "milestone" in data.columns else 0
    fail_rate = round(failed / total * 100) if total > 0 else 0

    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        st.metric("Total Engagements", total, f"Up {total} MoM", border=True)
        st.metric("Not Started", not_started, f"Down {active - not_started} MoM", border=True)
        st.metric("Success Rate", f"{success_rate}%", border=True)
        
    with col2:
        st.metric("Active Engagements", active, f"Up {active} MoM", border=True)
        st.metric("Engagements Complete", completed, f"Up {completed} MoM", border=True)
        st.metric("Fail Rate", f"{fail_rate}%", border=True)
        
    with col3:
        st.markdown(
            f'<div style="margin-top:-50px;margin-bottom:8px;">'
            f'<span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:40px;">{Config.HEADER_ICONS["milestone"]}</span>'
            f'<span style="vertical-align:middle;font-size:28px;font-weight:600;margin-left:10px;">Milestone Progress</span></div>',
            unsafe_allow_html=True
        )
        st.write(Config.CHART_CONTEXTS["milestone"])
        if "milestone" in data.columns:
            fig = create_chart(data["milestone"].value_counts(), chart_type="bar")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)
    render_icon_header(Config.HEADER_ICONS["esg"], "ESG Engagement Focus Areas")
    st.markdown('<span style="font-size:16px;color:#6c757d;">Distribution across <b>Climate Change</b>, <b>Water</b>, <b>Forests</b>, and <b>Other</b> themes.</span>', unsafe_allow_html=True)
    st.markdown('<div style="margin-bottom:-24px;"></div>', unsafe_allow_html=True)
    
    esg_data = {}
    theme_cols = ["Climate Change", "Water", "Forests", "Other"]
    total_themes = sum((data.get(col, pd.Series()) == "Y").sum() for col in theme_cols)
    
    if total > 0 and total_themes > 0:
        for theme in theme_cols:
            if theme in data.columns:
                count = (data[theme] == "Y").sum()
                esg_data[theme] = (count, round(count / total_themes * 100))
            else:
                esg_data[theme] = (0, 0)
    
    if esg_data:
        cols = st.columns(4)
        for i, (theme, (count, pct)) in enumerate(esg_data.items()):
            with cols[i]:
                option = create_esg_gauge(theme, count, Config.ESG_COLORS[theme], pct)
                option["series"][0]["detail"]["formatter"] = str(count)
                option["series"][0]["data"][0]["value"] = pct
                st_echarts(options=option, height="220px", key=f"esg-{theme}")

    render_icon_header(Config.HEADER_ICONS["table"], "Engagement Table")
    create_dataframe_component(data, Config.AGGRID_COLUMNS)
    cols = st.columns(6)
    with cols[-1]:
        csv = data.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            f"engagements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv"
        )

    render_hr(margin_top=100, margin_bottom=100)

def engagement_operations():
    tab1, tab2 = st.tabs(["➕ Create Engagement", "📝 Log Interaction"])
    
    with tab1:
        st.markdown('### Log New Engagement Target')
        
        with st.form("new_engagement", clear_on_submit=False):
            col1, col2 = st.columns(2)
            company = col1.text_input("Company Name *")
            gics = col2.selectbox("GICS Sector *", [""] + get_lookup_values("gics_sector"))

            col1, col2, col3 = st.columns(3)
            isin = col1.text_input("ISIN")
            aqr_id = col2.text_input("AQR ID")
            program = col3.selectbox("Program *", [""] + get_lookup_values("program"))
            
            col1, col2, col3 = st.columns(3)
            existing = sorted(st.session_state['FULL_DATA'].get('country', pd.Series()).dropna().unique())
            countries = sorted(set(get_lookup_values("country") + existing))
            country = col1.selectbox("Country *", [""] + countries)
            region = col2.selectbox("Region *", [""] + get_lookup_values("region"))
            theme = col3.selectbox("Theme", [""] + get_lookup_values("theme"))
            
            objective = st.selectbox("Objective", [""] + get_lookup_values("objective"))

            st.markdown("### ESG Focus Areas *")
            esg = get_esg_selection()

            st.markdown("### Timeline")
            col1, col2 = st.columns(2)
            start = col1.date_input("Start Date *", value=datetime.now().date())
            target = col2.date_input("Target Date", value=datetime.now().date() + timedelta(days=90))

            if st.form_submit_button("Create Engagement", type="primary"):
                errors = []
                if not company.strip(): errors.append("Company name required")
                if not gics: errors.append("GICS Sector required")
                if not program: errors.append("Program required")
                if not country: errors.append("Country required")
                if not region: errors.append("Region required")
                if not esg: errors.append("Select at least one ESG focus")
                
                if errors:
                    st.error("\n".join(f"• {e}" for e in errors))
                else:
                    existing_names = st.session_state['FULL_DATA'].get('company_name', pd.Series()).str.lower().tolist()
                    if company.lower() in existing_names:
                        st.error(f"'{company}' already exists")
                    else:
                        success, msg = create_engagement({
                            "company_name": company.strip(),
                            "gics_sector": gics,
                            "region": region,
                            "isin": isin.strip(),
                            "aqr_id": aqr_id.strip(),
                            "program": program,
                            "country": country,
                            "theme": theme,
                            "objective": objective,
                            "start_date": start,
                            "target_date": target,
                            "created_by": "System",
                            "e": "e" in esg,
                            "s": "s" in esg,
                            "g": "g" in esg
                        })
                        
                        if success:
                            st.success(msg)
                            st.balloons()
                            refresh_data()
                            st.rerun()
                        else:
                            st.error(msg)

    with tab2:
        st.markdown("### Log Interaction")
        company = company_selector_widget(st.session_state['FULL_DATA'], st.session_state['DATA'])
        
        if not company:
            st.info("Select a company to log an interaction")
            return

        eng = st.session_state['FULL_DATA'][st.session_state['FULL_DATA']["company_name"] == company].iloc[0]

        with st.expander("Current Status", expanded=True):
            cols = st.columns(3)
            cols[0].markdown(f"**Milestone**<br>{eng.get('milestone', 'N/A')}", unsafe_allow_html=True)
            cols[1].markdown(f"**Status**<br>{eng.get('milestone_status', 'N/A')}", unsafe_allow_html=True)
            cols[2].markdown(f"**Escalation**<br>{eng.get('escalation_level', 'N/A')}", unsafe_allow_html=True)

        with st.form("log_interaction", clear_on_submit=False):
            st.markdown("### Interaction Details")
            col1, col2 = st.columns(2)
            int_type = col1.selectbox("Type *", [""] + get_lookup_values("interaction_type"))
            int_date = col2.date_input("Date *", value=datetime.now().date())
            
            col1, col2 = st.columns(2)
            outcome = col1.selectbox("Outcome *", [""] + get_lookup_values("outcome_status"))
            
            esc_opts = get_lookup_values("escalation_level")
            current_esc = eng.get("escalation_level", "")
            escalation = col2.selectbox("Escalation", [current_esc] + [x for x in esc_opts if x != current_esc])

            summary = st.text_area("Summary *", height=150)
            
            st.markdown("### Milestone Update (Optional)")
            col1, col2 = st.columns(2)
            
            mile_opts = get_lookup_values("milestone")
            current_mile = eng.get("milestone", "")
            milestone = col1.selectbox("Milestone", [current_mile] + [x for x in mile_opts if x != current_mile])
            
            status_opts = get_lookup_values("milestone_status")
            current_stat = eng.get("milestone_status", "")
            status = col2.selectbox("Status", [current_stat] + [x for x in status_opts if x != current_stat])

            if st.form_submit_button("Log Interaction", type="primary"):
                if not int_type or not summary.strip() or not outcome:
                    st.error("Fill all required fields")
                else:
                    success, msg = log_interaction({
                        "engagement_id": eng["engagement_id"],
                        "last_interaction_date": int_date,
                        "next_action_date": datetime.now().date() + timedelta(days=14),
                        "interaction_summary": summary.strip(),
                        "interaction_type": int_type,
                        "outcome_status": outcome,
                        "escalation_level": escalation or current_esc,
                        "milestone": milestone if milestone != current_mile else current_mile,
                        "milestone_status": status if status != current_stat else current_stat,
                    })
                    
                    if success:
                        st.success(msg)
                        refresh_data()
                        st.rerun()
                    else:
                        st.error(msg)

def task_management():
    df = st.session_state['DATA']
    
    if df.empty:
        st.warning("No tasks available")
        return

    upcoming = get_upcoming_tasks(df, Config.UPCOMING_DAYS)
    urgent = upcoming[upcoming['days_to_next_action'] <= Config.URGENT_DAYS]
    warning = upcoming[upcoming['days_to_next_action'].between(Config.URGENT_DAYS + 1, Config.WARNING_DAYS)]

    render_metrics([
        (f"Urgent (≤{Config.URGENT_DAYS} days)", len(urgent)),
        (f"Warning (≤{Config.WARNING_DAYS} days)", len(warning)),
        (f"Upcoming (≤{Config.UPCOMING_DAYS} days)", len(upcoming))
    ])

    if len(df) < len(st.session_state['FULL_DATA']):
        st.info("Tasks filtered to match current criteria")

    tabs = st.tabs(["🚨 Urgent", "⚠️ This Week", "📅 Upcoming"])
    today = datetime.now().date()

    for tab, tasks, label in zip(tabs, [urgent, warning, upcoming], ["Urgent", "This Week", "Upcoming"]):
        with tab:
            if not tasks.empty:
                for _, task in tasks.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        col1.markdown(f"**{task['company_name']}**")
                        col1.caption(f"Milestone: {task.get('milestone', 'N/A')}")
                        with col2:
                            handle_task_date_display(task['next_action_date'], today)
                        if col3.button("Complete", key=f"task_{task['engagement_id']}"):
                            success, msg = update_milestone_status(task['engagement_id'], "Complete")
                            if success:
                                st.success(msg)
                                refresh_data()
                                st.rerun()
                            else:
                                st.error(msg)
                        render_hr(margin_top=4, margin_bottom=8)
            else:
                st.info(f"No {label.lower()} tasks! 🎉")

def enhanced_analysis():
    df = st.session_state['DATA']
    
    if df.empty:
        st.warning("No data for analysis")
        return

    tab1, tab2, tab3 = st.tabs(["🎯 Engagement Analysis", "🌍 Geographic Analysis", "📈 Status Trends"])

    with tab1:
        st.warning("Work in Progress")

        context, chart = st.columns([1.5, 1])
        with context:
            render_icon_header(Config.HEADER_ICONS["esg"], "ESG Focus Distribution", 40, 28)
            st.write("Distribution by ESG focus area. Shows count of active engagements.")
        with chart:
            esg_data = pd.Series({
                "Environmental": df.get("e", pd.Series()).sum(),
                "Social": df.get("s", pd.Series()).sum(),
                "Governance": df.get("g", pd.Series()).sum()
            })
            if esg_data.sum() > 0:
                fig = create_chart(esg_data, chart_type="pie")
                st.plotly_chart(fig, use_container_width=True)

        if "gics_sector" in df.columns:
            context, chart = st.columns([1, 2])
            with context:
                render_icon_header(Config.HEADER_ICONS["sector"], "Sector Distribution", 40, 28)
                st.write(Config.CHART_CONTEXTS["sector"])
            with chart:
                fig = create_chart(df["gics_sector"].value_counts(), chart_type="bar")
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        render_icon_header(Config.HEADER_ICONS["region"], "Geographical Analysis", 40, 28)
        
        regions = ["Global"] + sorted(df["region"].unique()) if "region" in df.columns else ["Global"]
        selected = st.selectbox("Select Region", regions, key="geo_region")
        
        geo_df = df[df["region"] == selected] if selected != "Global" else df

        col1, col2 = st.columns([1, 3])

        with col1:
            if not geo_df.empty:
                render_geo_metrics(
                    len(geo_df),
                    geo_df["country"].nunique(),
                    geo_df["country"].mode()[0] if not geo_df["country"].empty else "N/A"
                )

        with col2:
            if not geo_df.empty and "country" in geo_df.columns:
                country_data = geo_df.groupby("country").size().reset_index(name="count")
                country_data['iso_code'] = country_data['country'].map(Config.COUNTRY_ISO_MAP)
                mapped = country_data.dropna(subset=['iso_code'])
                
                if not mapped.empty:
                    fig = create_chart(
                        mapped,
                        chart_type="choropleth", 
                        locations="iso_code",
                        color="count",
                        hover_name="country",
                        color_continuous_scale="Viridis",
                        range_color=[0, geo_df["country"].value_counts().max()]
                    )
                    
                    fig.update_layout(
                        geo=dict(
                            bgcolor='rgba(0,0,0,0)',
                            showframe=False,
                            showcoastlines=True,
                            coastlinecolor="rgba(68,68,68,0.15)",
                            projection_type='natural earth',
                            showcountries=True,
                            countrycolor="rgba(68,68,68,0.15)",
                            showland=True,
                            landcolor='rgb(243,243,243)',
                            showocean=True,
                            oceancolor='rgb(230,235,240)',
                            showlakes=True,
                            lakecolor='rgb(230,235,240)',
                            fitbounds="locations"
                        ),
                        height=400,
                        margin=dict(l=0, r=0, t=0, b=0)
                    )
                    
                    fig.update_coloraxes(colorbar=dict(thickness=5, len=0.7, x=1.02, xpad=10, y=0.5))
                    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Engagements: %{z}<extra></extra>")
                    
                    st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            chart_data = None
            chart_title = ""

            if selected == "Global":
                chart_title = "Regional Distribution"
                if "region" in df.columns and not df["region"].dropna().empty:
                    chart_data = df["region"].value_counts()
            else:
                chart_title = f"Countries in {selected}"
                if "country" in geo_df.columns and not geo_df["country"].dropna().empty:
                    chart_data = geo_df["country"].value_counts()
            
            st.markdown(f"#### {chart_title}")
            if chart_data is not None and not chart_data.empty:
                fig = go.Figure(go.Pie(
                    labels=chart_data.index,
                    values=chart_data.values,
                    hole=0.7,
                    marker_colors=Config.CB_SAFE_PALETTE,
                    textinfo='percent',
                    hoverinfo='label+percent+value',
                    textfont_size=14
                ))

                fig.update_layout(
                    height=400,
                    margin=dict(l=20, r=20, t=50, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    )
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data to display for this selection.")
                
        with col2:
            st.markdown("#### ESG Themes")
            st.markdown("")
            st.markdown("")
            st.markdown("")
            theme_cols = ["Climate Change", "Water", "Forests", "Other"]
            theme_data = {}
            
            for theme in theme_cols:
                if theme in geo_df.columns:
                    count = (geo_df[theme] == "Y").sum()
                    theme_data[theme] = count
                else:
                    theme_data[theme] = 0
            
            total_themes = sum(theme_data.values())
            
            if total_themes > 0:
                for row_idx in range(0, len(theme_cols), 2):
                    gauge_cols = st.columns(2)
                    
                    for col_idx in range(2):
                        theme_idx = row_idx + col_idx
                        if theme_idx < len(theme_cols):
                            theme = theme_cols[theme_idx]
                            count = theme_data[theme]
                            
                            with gauge_cols[col_idx]:
                                percentage = round((count / total_themes) * 100) if total_themes > 0 else 0
                                color = Config.ESG_COLORS[theme]
                                
                                option = create_esg_gauge(theme, count, color, percentage)
                                option["series"][0]["detail"]["formatter"] = str(count)
                                option["series"][0]["data"][0]["value"] = percentage
                                option["series"][0]["radius"] = "110%"
                                option["series"][0]["center"] = ["50%", "65%"]
                                
                                st_echarts(options=option, height="180px", key=f"geo-theme-{selected}-{theme}")
            else:
                st.info("No theme data for this region")
            
        if not geo_df.empty:
            pass
        else:
            st.info("No geographic data to display.")
        col1, col2 = st.columns([1.14, 1])
        with col1:
            if selected != "Global":
                region_df = df[df["region"] == selected]
                total = len(region_df)
                avg = int(df.groupby("region").size().mean())
                compare = "Higher" if total > avg else "Lower" if total < avg else "Equal to"
                st.info(f"{selected} has {total} companies targeted. That's {compare} than avg. ({avg})")
        with col2:
            st.warning(f"100% of {selected}'s engagements are currently Active.")
      
    with tab3:
        st.warning("Work in Progress")
        st.subheader("Engagement Status")
        analytics = get_engagement_analytics(df)
        
        if not analytics["monthly_trends"].empty:
            fig = go.Figure(go.Scatter(
                x=analytics["monthly_trends"]["month"],
                y=analytics["monthly_trends"]["new_engagements"],
                mode='lines+markers',
                line=dict(color=Config.CB_SAFE_PALETTE[0], width=3),
                marker=dict(size=8, color=Config.CB_SAFE_PALETTE[0])
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode='x unified',
                xaxis_title="",
                yaxis_title=""
            )
            st.plotly_chart(fig, use_container_width=True)

def company_deep_dive():
    full_df = st.session_state['FULL_DATA']
    filtered_df = st.session_state['DATA']

    company = company_selector_widget(full_df, filtered_df)
    if not company:
        return

    data = full_df[full_df["company_name"] == company].iloc[0]

    with st.container(border=True):
        render_icon_header("apartment", f"Company Snapshot: {data['company_name']}", 32, 28)
        cols = st.columns(3)
        cols[0].markdown(f"**Sector:** {data.get('gics_sector', 'N/A')}")
        cols[1].markdown(f"**Region:** {data.get('region', 'N/A')}")
        cols[2].markdown(f"**Country:** {data.get('country', 'N/A')}")
        render_hr(0, 0)

    with st.container(border=True):
        render_icon_header("camera_alt", "Engagement Snapshot", 38, 28)
        cols = st.columns(3)
        cols[0].markdown(f"**Program:** {data.get('program', 'N/A')}")
        cols[1].markdown(f"**Objective:** {data.get('objective', 'N/A')}")
        cols[2].markdown(f"**Health:** {data.get('milestone_status', 'N/A')}")

    render_hr(10, 10)
    render_icon_header("history", "Interaction History")
    display_interaction_history(data['engagement_id'])
    render_hr(10, 10)

PAGE_FUNCTIONS = {
    "dashboard": dashboard,
    "engagement_management": engagement_operations,
    "task_management": task_management,
    "analytics": enhanced_analysis,
    "company_deep_dive": company_deep_dive,
}

def navigation():
    with st.sidebar:
        st.markdown(" ")
        titles = list(PAGES_CONFIG.keys())
        icons = [PAGES_CONFIG[p]['icon'] for p in titles]
        
        if 'selected_page' not in st.session_state:
            st.session_state.selected_page = 'Dashboard'
            
        try:
            idx = titles.index(st.session_state.selected_page)
        except ValueError:
            idx = 0
            st.session_state.selected_page = titles[0]
            
        selected = option_menu(
            "Navigation", titles,
            icons=icons,
            menu_icon="cast", 
            default_index=idx,
            styles=NAV_STYLES,
            key="main_navigation"
        )
        
        if selected != st.session_state.selected_page:
            st.session_state.selected_page = selected

        render_hr(0, 0)

        col1, col2 = st.columns([5, 2.5])
        with col1:
            st.markdown(
                f'<div style="margin-left:15px;">'
                f'<span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:22px;">{Config.HEADER_ICONS["filter"]}</span>'
                f'<span style="vertical-align:middle;font-size:20px;font-weight:500;margin-left:5px;">Toggle Filtering</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col2:
            filtering = st.toggle("", value=False, key="enable_filtering")

        render_hr(0, 8)
        
        if filtering:
            filters = sidebar_filters(st.session_state['FULL_DATA'])
            st.session_state['DATA'] = apply_filters(st.session_state['FULL_DATA'], filters)
        else:
            st.session_state['DATA'] = st.session_state['FULL_DATA'].copy()

def main():
    render_icon_header(Config.HEADER_ICONS["app_title"], Config.APP_TITLE, 32, 32)
    st.markdown('<div style="margin-top:-33px;"></div>', unsafe_allow_html=True)
    render_hr()
    
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = 'Dashboard'
    
    if 'validator' not in st.session_state or 'FULL_DATA' not in st.session_state:
        with st.spinner('Loading...'):
            refresh_data()
    
    if st.session_state.FULL_DATA.empty:
        st.warning("No data found. Add an engagement to begin.")
        engagement_operations()
        return

    try:
        navigation()
        
        page_name = PAGES_CONFIG[st.session_state.selected_page]['function']
        page_func = PAGE_FUNCTIONS[page_name]
        
        if st.session_state.get('data_refreshed', False):
            with st.spinner(f'Loading {st.session_state.selected_page}...'):
                page_func()
            st.session_state.data_refreshed = False
        else:
            page_func()

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)
        if st.button("Clear Cache"):
            st.cache_data.clear()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()