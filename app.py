import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
from streamlit_echarts import st_echarts
from streamlit_calendar import calendar
from config import Config, CHART_CONFIGS, ENHANCED_CSS, NAV_STYLES, PAGES_CONFIG, CALENDAR_OPTIONS, CALENDAR_STYLES
from utils import *

st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon=Config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown('<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">', unsafe_allow_html=True)
st.markdown(ENHANCED_CSS, unsafe_allow_html=True)

def sidebar_filters(df):
    st.markdown(
        f'<span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:18px;">{Config.HEADER_ICONS["filter"]}</span>'
        f'<span style="vertical-align:middle;font-size:18px;font-weight:600;">Filters</span>',
        unsafe_allow_html=True
    )

    with st.expander(":material/notifications: Alerts", expanded=False):
        st.caption("Select to Show Upcoming Events")
        alert_options = st.segmented_control(
            "Alert Type",
            options=[":material/priority_high: Urgent", ":material/schedule: Upcoming"],
            default=None,
            label_visibility="collapsed"
        )
        show_urgent = alert_options in [":material/priority_high: Urgent", "All"]
        show_upcoming = alert_options in [":material/schedule: Upcoming", "All"]

    with st.expander(":material/business: Company Filters", expanded=False):
        companies = st.multiselect("Company", sorted(df.get("company_name", pd.Series()).unique()))
        region = st.multiselect("Region", get_lookup_values("region"))
        
        existing = df['country'].dropna().unique() if 'country' in df.columns else []
        all_countries = sorted(set(get_lookup_values("country") + list(existing)))
        country = st.multiselect("Country", all_countries)
        sector = st.multiselect("GICS Sector", get_lookup_values("gics_sector"))
        
    with st.expander(":material/forum: Engagement Type", expanded=False):
        st.caption("ESG Focus Areas")
        esg_opt = st.segmented_control(
            "ESG",
            options=[":material/eco: E", ":material/groups: S", ":material/account_balance: G"],
            default=None,
            label_visibility="collapsed"
        )
        
        progs = st.multiselect("Program", get_lookup_values("program"))
        themes = st.multiselect("Theme", get_lookup_values("theme"))
        objectives = st.multiselect("Objective", get_lookup_values("objective"))
        
    esg_map = {None: ["e", "s", "g"], ":material/eco: E": ["e"], ":material/groups: S": ["s"], ":material/account_balance: G": ["g"]}
    esg = esg_map[esg_opt]
    
    with st.expander(":material/people: Engagement Status", expanded=False):
        mile = st.multiselect("Milestone", get_lookup_values("milestone"))
        status = st.multiselect("Status", get_lookup_values("milestone_status"))

    return progs, sector, region, country, mile, status, esg, show_urgent, show_upcoming, companies, themes, objectives

def dashboard():
    data = st.session_state['DATA']
    if data.empty:
        st.warning("No engagement data available.")
        return
    today = pd.Timestamp.now().normalize()
    days_ahead = (pd.to_datetime(data.get("next_action_date")) - today).dt.days
    week_tasks = data[days_ahead.between(0, 6)]
    month_tasks = data[days_ahead.between(7, 30)]
    theme_cols = ["Climate Change", "Water", "Forests", "Other"]
    
    tab1, tab2= st.tabs([":material/dashboard: Overview", ":material/public: Geographic Analysis"])
    with tab1:
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

        col1, col2, col3 = st.columns([1, 1, 3.5])
        
        with col1:
            st.metric("Total Engagements", total, f"Up {total} MoM", border=True)
            st.metric("Not Started", not_started, f"Down {active - not_started} MoM", border=True)
            st.metric("Success Rate", f"{success_rate}%", border=True)
            
        with col2:
            st.metric("Active Engagements", active, f"Up {active} MoM", border=True)
            st.metric("Engagements Complete", completed, f"Up {completed} MoM", border=True)
            st.metric("Fail Rate", f"{fail_rate}%", border=True)
            
        with col3:
            render_icon_header(Config.HEADER_ICONS["esg"], "ESG Engagement Focus Areas", div_style="margin-top:-57px;")
            
            # Calculate theme data
            theme_data = {}
            for theme in theme_cols:
                if theme in data.columns:
                    count = (data[theme] == "Y").sum()
                    theme_data[theme] = count
                else:
                    theme_data[theme] = 0
            
            total_themes = sum(theme_data.values())
            
            # Force initialization check - trigger rerun if needed
            if 'dashboard_charts_initialized' not in st.session_state:
                st.session_state.dashboard_charts_initialized = False
            
            # Render charts with proper initialization
            if st.session_state.get('app_initialized', False) and len(data) > 0:
                for row_idx in range(0, len(theme_cols), 2):
                    gauge_cols = st.columns(2)
                    for col_idx in range(2):
                        theme_idx = row_idx + col_idx
                        if theme_idx < len(theme_cols):
                            theme = theme_cols[theme_idx]
                            count = theme_data[theme]
                            with gauge_cols[col_idx]:
                                count = int(count)
                                percentage = int(round((count / total_themes) * 100)) if total_themes > 0 else 0
                                color = Config.ESG_COLORS[theme]
                                option = create_esg_gauge(theme, count, color, percentage)
                                
                                # Render chart with error handling
                                try:
                                    st_echarts(
                                        options=option, 
                                        height="200px", 
                                        key=f"main_{theme.replace(' ', '_').lower()}"
                                    )
                                except Exception as e:
                                    st.error(f"Chart rendering error for {theme}: {str(e)}")
                
                # Mark charts as initialized and force rerun if this is first time
                if not st.session_state.dashboard_charts_initialized:
                    st.session_state.dashboard_charts_initialized = True
                    st.rerun()
            else:
                # Show loading placeholder
                for row_idx in range(0, len(theme_cols), 2):
                    gauge_cols = st.columns(2)
                    for col_idx in range(2):
                        theme_idx = row_idx + col_idx
                        if theme_idx < len(theme_cols):
                            theme = theme_cols[theme_idx]
                            with gauge_cols[col_idx]:
                                st.info(f"Loading {theme} chart...")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            render_icon_header("insights", "Insights", 40, 28)
            theme_coverage_count = sum(theme_data.values())
            avg_themes_per_engagement = round(theme_coverage_count / total, 2) if total > 0 else 0
            cdp_count = (data["program"] == "CDP").sum() if "program" in data.columns else 0
            cdp_percentage = round(cdp_count / total * 100) if total > 0 else 0
            direct_count = total - cdp_count
            direct_percentage = 100 - cdp_percentage
            st.markdown(f"We've currently begun **{total}** out of **22** engagements.")
            progress_pct = round((total / 22) * 100)
            fig_eng = go.Figure()
            fig_eng.add_trace(go.Bar(
                x=[100], y=['Progress'], orientation='h', marker=dict(color='#e0e0e0'),
                showlegend=False, hoverinfo='skip'
            ))
            fig_eng.add_trace(go.Bar(
                x=[progress_pct], y=['Progress'], orientation='h', marker=dict(color='#2E8B57'),
                text=[f'{total}/22 ({progress_pct}%)'],
                textposition='inside' if progress_pct > 30 else 'outside',
                textfont=dict(color='white' if progress_pct > 30 else '#2E8B57'),
                showlegend=False,
                hovertemplate=f'{total} out of 22 engagements<br>{progress_pct}% complete<extra></extra>'
            ))
            
            fig_eng.update_layout(
                height=55, margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[0, 100]),
                yaxis=dict(showgrid=False, showticklabels=False),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', barmode='overlay'
            )
            st.plotly_chart(fig_eng, use_container_width=True)
            st.markdown(f"We've covered **{theme_coverage_count}** themes, or **{avg_themes_per_engagement}** themes per engagement.")
            stacked_bar_data = []
            for theme in theme_cols:
                theme_engagements = data[data[theme] == 'Y'] if theme in data.columns else pd.DataFrame()
                if not theme_engagements.empty:
                    cdp_theme_count = (theme_engagements['program'] == 'CDP').sum()
                    other_theme_count = len(theme_engagements) - cdp_theme_count
                    stacked_bar_data.append({
                        'Theme': theme, 'CDP': cdp_theme_count, 'Other': other_theme_count,
                        'Total': len(theme_engagements)
                    })

            fig_themes_stacked = go.Figure()
            if stacked_bar_data:
                stacked_df = pd.DataFrame(stacked_bar_data).sort_values(by='Total', ascending=True)
                fig_themes_stacked.add_trace(go.Bar(
                    y=stacked_df['Theme'], x=stacked_df['Other'],
                    name='Other Programs', orientation='h', marker_color=Config.CB_SAFE_PALETTE[1]
                ))
                fig_themes_stacked.add_trace(go.Bar(
                    y=stacked_df['Theme'], x=stacked_df['CDP'],
                    name='CDP Program', orientation='h', marker_color=Config.CB_SAFE_PALETTE[2]
                ))
            fig_themes_stacked.update_layout(
                barmode='stack', height=150, margin=dict(l=0, r=0, t=20, b=5),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, showticklabels=True, automargin=True),
                legend=dict(orientation="h", yanchor="top", y=1.2, xanchor="right", x=1, font=dict(size=10))
            )
            st.plotly_chart(fig_themes_stacked, use_container_width=True)
            st.markdown(f"The majority of our engagements (**{cdp_percentage}%**) are CDP.")
            fig = go.Figure(data=[
                go.Bar(
                    x=['CDP', 'Direct'], y=[cdp_count, direct_count],
                    text=[f'{cdp_percentage}%', f'{direct_percentage}%'],
                    textposition='auto', marker_color=['#4682B4', '#fc8d62']
                )
            ])
            
            fig.update_layout(
                height=150, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, showticklabels=False)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            render_icon_header(Config.HEADER_ICONS["milestone"], "Milestone Progress", 40, 28, div_style="margin-top:0px;")
            st.write(Config.CHART_CONTEXTS["milestone"])
            if "milestone" in data.columns:
                fig = create_chart(
                    data["milestone"].value_counts(), chart_type="bar", height=530,
                    margin={"l": 40, "r": 20, "t": 20, "b": 80}
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

        render_icon_header(Config.HEADER_ICONS["table"], "Engagement List")
        create_dataframe_component(data, Config.AGGRID_COLUMNS)
        cols = st.columns(6)
        with cols[-1]:
            csv = data.to_csv(index=False)
            st.download_button(
                "Download Table",
                csv,
                f"filtered_engagements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                icon=":material/download:",
                use_container_width=True,
            )

    with tab2:
        render_icon_header(Config.HEADER_ICONS["region"], "Regional & Sector Analysis", 40, 28)
        
        regions = ["Global"] + sorted(data["region"].unique()) if "region" in data.columns else ["Global"]
        
        # Initialize selected region in session state
        if 'selected_region' not in st.session_state:
            st.session_state.selected_region = "Global"
        
        # Ensure selected region is valid
        if st.session_state.selected_region not in regions:
            st.session_state.selected_region = "Global"
            
        selected_idx = regions.index(st.session_state.selected_region) if st.session_state.selected_region in regions else 0
        selected = st.selectbox(
            "Select to Focus on Region", 
            regions, 
            index=selected_idx,
            key="geo_region_selector"
        )
        
        # Update session state when selection changes
        if selected != st.session_state.selected_region:
            st.session_state.selected_region = selected
        
        geo_df = data if selected == "Global" else data[data["region"] == selected]
        
        # Calculate active engagements for the selected region
        excluded = ["not started", "verified", "success", "cancelled"]
        active = (~data["milestone"].str.lower().isin(excluded)).sum() if "milestone" in data.columns else 0

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
                        mapped, chart_type="choropleth", locations="iso_code", color="count",
                        hover_name="country", color_continuous_scale="Viridis",
                        range_color=[0, geo_df["country"].value_counts().max()]
                    )
                    
                    scope_mapping = {
                        "Global": "world", "Asia": "asia", "Europe": "europe",
                        "North America": "north america", "South America": "south america",
                        "Oceania": "world", "Africa": "world",
                    }
                    geo_scope = scope_mapping.get(selected, "world")
                    geo_config = dict(
                        bgcolor='rgba(0,0,0,0)', showframe=False, showcoastlines=True,
                        coastlinecolor="rgba(68,68,68,0.15)", projection_type='equirectangular',
                        showcountries=True, countrycolor="rgba(68,68,68,0.15)",
                        showland=True, landcolor='rgb(243,243,243)',
                        showocean=True, oceancolor='rgb(230,235,240)',
                    )
                    
                    if selected in ["Oceania", "Africa"] or (selected not in scope_mapping):
                        geo_config["fitbounds"] = "locations"
                    else:
                        geo_config["scope"] = geo_scope
                    fig.update_layout(geo=geo_config, height=400, margin=dict(l=0, r=0, t=0, b=0))
                    fig.update_coloraxes(colorbar=dict(thickness=5, len=0.7, x=1.02, xpad=10, y=0.5))
                    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Engagements: %{z}<extra></extra>")
                    st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            chart_data = None
            chart_title = ""
            if selected == "Global":
                chart_title = "Regional Distribution"
                if "region" in data.columns and not data["region"].dropna().empty:
                    chart_data = data["region"].value_counts()
            else:
                chart_title = f"Countries in {selected}"
                if "country" in geo_df.columns and not geo_df["country"].dropna().empty:
                    chart_data = geo_df["country"].value_counts()
            render_icon_header("pie_chart", chart_title, 24, 20)
            if chart_data is not None and not chart_data.empty:
                fig = go.Figure(go.Pie(
                    labels=chart_data.index, values=chart_data.values, hole=0.7,
                    marker_colors=Config.CB_SAFE_PALETTE, textinfo='percent',
                    hoverinfo='label+percent+value', textfont_size=14
                ))
                fig.update_layout(
                    height=400, margin=dict(l=20, r=20, t=50, b=20),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data to display for this selection.")
                
        with col2:
            render_icon_header("eco", "ESG Themes", 24, 20)
            
            # Calculate theme data for selected region
            theme_data = {}
            for theme in theme_cols:
                if theme in geo_df.columns:
                    count = (geo_df[theme] == "Y").sum()
                    theme_data[theme] = count
                else:
                    theme_data[theme] = 0
            
            total_themes = sum(theme_data.values())
            
            # Force initialization check for geo charts
            geo_init_key = f"geo_charts_initialized_{selected.replace(' ', '_')}"
            if geo_init_key not in st.session_state:
                st.session_state[geo_init_key] = False
            
            # Render charts with proper initialization
            if not geo_df.empty and st.session_state.get('app_initialized', False):
                for row_idx in range(0, len(theme_cols), 2):
                    gauge_cols = st.columns(2)
                    for col_idx in range(2):
                        theme_idx = row_idx + col_idx
                        if theme_idx < len(theme_cols):
                            theme = theme_cols[theme_idx]
                            count = theme_data[theme]
                            with gauge_cols[col_idx]:
                                count = int(count)
                                percentage = int(round((count / total_themes) * 100)) if total_themes > 0 else 0
                                color = Config.ESG_COLORS[theme]
                                option = create_esg_gauge(theme, count, color, percentage)
                                
                                # Render chart with error handling
                                try:
                                    st_echarts(
                                        options=option, height="200px", 
                                        key=f"geo_{theme.replace(' ', '_').lower()}"
                                    )
                                except Exception as e:
                                    st.error(f"Geo chart rendering error for {theme}: {str(e)}")
                
                # Mark charts as initialized and force rerun if this is first time for this region
                if not st.session_state[geo_init_key]:
                    st.session_state[geo_init_key] = True
                    st.rerun()
            else:
                if geo_df.empty:
                    st.info("No ESG theme data available for the selected region.")
                else:
                    # Show loading placeholder
                    for row_idx in range(0, len(theme_cols), 2):
                        gauge_cols = st.columns(2)
                        for col_idx in range(2):
                            theme_idx = row_idx + col_idx
                            if theme_idx < len(theme_cols):
                                theme = theme_cols[theme_idx]
                                with gauge_cols[col_idx]:
                                    st.info(f"Loading {theme} chart...")
            
        if not geo_df.empty:
            col1, col2 = st.columns([1.14, 1])
            with col1:
                if selected != "Global":
                    region_df = data[data["region"] == selected]
                    total = len(region_df)
                    avg = int(data.groupby("region").size().mean())
                    compare = "higher" if total > avg else "lower" if total < avg else "equal to"
                    st.info(f"{selected} has {total} companies targeted. That's {compare} than average ({avg}).")
            with col2:
                excluded = ["not started", "verified", "success", "cancelled"]
                active_in_region = (~geo_df["milestone"].str.lower().isin(excluded)).sum() if "milestone" in geo_df.columns else 0
                active_pct = round(active_in_region / len(geo_df) * 100) if len(geo_df) > 0 else 0
                st.warning(f"{active_pct}% of {selected}'s engagements are currently Active.")

        render_icon_header(Config.HEADER_ICONS["sector"], "Sector Distribution", 40, 28)
        if "gics_sector" in data.columns:
            st.write(Config.CHART_CONTEXTS["sector"])
            fig = create_chart(data["gics_sector"].value_counts(), chart_type="bar")
            st.plotly_chart(fig, use_container_width=True)
      

def engagement_operations():
    tab1, tab2, tab3 = st.tabs([
        f":material/add_business: Create Engagement",
        f":material/edit_note: Log Interaction",
        f":material/bookmark_manager: Engagement Records"
    ])
    
    with tab1:
        render_icon_header("add_business", "Log New Engagement Target", 32, 28)
        
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

            render_icon_header("eco", "ESG Focus Areas *", 24, 20)
            esg = get_esg_selection(defaults=(False, False, False))

            render_icon_header("schedule", "Timeline", 24, 20)
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
        render_icon_header("edit_note", "Log Interaction", 32, 28)
        company = company_selector_widget(st.session_state['FULL_DATA'], st.session_state['DATA'], key="log_interaction_company")
        
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
            render_icon_header("description", "Interaction Details", 24, 20)
            col1, col2 = st.columns(2)
            int_type = col1.selectbox("Type *", [""] + get_lookup_values("interaction_type"))
            int_date = col2.date_input("Date *", value=datetime.now().date())
            
            col1, col2 = st.columns(2)
            outcome = col1.selectbox("Outcome *", [""] + get_lookup_values("outcome_status"))
            
            esc_opts = get_lookup_values("escalation_level")
            current_esc = eng.get("escalation_level", "")
            escalation = col2.selectbox("Escalation", [current_esc] + [x for x in esc_opts if x != current_esc])

            summary = st.text_area("Summary *", height=150)
            
            render_icon_header("flag", "Milestone Update (Optional)", 24, 20)
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

    with tab3:
        render_icon_header("business", "Engagement Records", 32, 28)
        full_df = st.session_state['FULL_DATA']
        filtered_df = st.session_state['DATA']

        company = company_selector_widget(full_df, filtered_df, key="engagement_records_company")
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
        render_icon_header("history", "Engagement Records")
        display_interaction_history(data['engagement_id'])
        render_hr(10, 10)
def task_management():
    df = st.session_state.get('DATA', pd.DataFrame())
    if df.empty or 'next_action_date' not in df.columns:
        st.warning("No tasks with upcoming dates are available for the current filter selection.")
        return
    tasks_df = df.dropna(subset=['next_action_date']).copy()
    if tasks_df.empty:
        st.info("No engagements with a 'Next Action Date' to display on the calendar.")
        return
    calendar_events, resources = df_to_calendar_events(tasks_df)
    render_icon_header("calendar_month", "Multi-Month Calendar View", 32, 28)
    calendar(
        events=calendar_events, custom_css=CALENDAR_STYLES,
        key="calendar_multi_month_view", options=CALENDAR_OPTIONS,
    )

PAGE_FUNCTIONS = {
    "dashboard": dashboard,
    "engagement_management": engagement_operations,
    "task_management": task_management,
}

def navigation():
    with st.sidebar:
        st.markdown(" ")
        titles = [k for k in PAGES_CONFIG.keys() if k != "Analytics"]
        icons = [PAGES_CONFIG[p]['icon'] for p in titles]
        idx = titles.index(st.session_state.selected_page) if st.session_state.selected_page in titles else 0
        selected = option_menu(
            "Navigation", titles, icons=icons, menu_icon="cast", 
            default_index=idx, styles=NAV_STYLES, key="main_navigation"
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
    # Initialize core session state variables
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = 'Dashboard'
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = False
    
    # Load data if not available
    if 'validator' not in st.session_state or 'FULL_DATA' not in st.session_state:
        with st.spinner('Loading application data...'):
            refresh_data()
            # Mark as initialized after data load
            st.session_state.app_initialized = True
            # Force a rerun to ensure proper chart initialization
            if not st.session_state.get('initial_rerun_done', False):
                st.session_state.initial_rerun_done = True
                st.rerun()
    
    render_icon_header(Config.HEADER_ICONS["app_title"], Config.APP_TITLE, 32, 32)
    st.markdown('<div style="margin-top:-33px;"></div>', unsafe_allow_html=True)
    render_hr()
    
    if st.session_state.FULL_DATA.empty:
        st.warning("No data found. Add an engagement to begin.")
        engagement_operations()
        return
        
    try:
        navigation()
        page_name = PAGES_CONFIG[st.session_state.selected_page]['function']
        page_func = PAGE_FUNCTIONS[page_name]
        page_func()
    except Exception as e:
        st.error(f"Application error: {e}")
        st.exception(e)
        if st.button("Reset Application"):
            st.cache_data.clear()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()