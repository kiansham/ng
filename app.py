import pandas as pd
import streamlit as st
import time
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar
from config import Config, NAV_STYLES, PAGES_CONFIG
from utils import *
from pathlib import Path

def _initialize_session_state():
    if 'FULL_DATA' not in st.session_state:
        st.session_state.FULL_DATA = pd.DataFrame()
    if 'DATA' not in st.session_state:
        st.session_state.DATA = pd.DataFrame()
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = 'Dashboard'
    if 'data_refreshed' not in st.session_state:
        st.session_state.data_refreshed = False
    if 'refresh_counter' not in st.session_state:
        st.session_state.refresh_counter = 0
    if 'selected_region' not in st.session_state:
        st.session_state.selected_region = 'Global'
    if 'main_nav_default' not in st.session_state:
        st.session_state.main_nav_default = 0
    if 'enable_filtering' not in st.session_state:
        st.session_state.enable_filtering = False

def sidebar_filters(df: pd.DataFrame):
    render_icon_header("tune", "Filters", icon_size=18, text_size=18, div_style="margin-left:15px; margin-top:0px; margin-bottom:0px;")

    with st.expander(":material/notifications: Status Filter", expanded=False):
        st.caption("Filter by Engagement Status")
        status_options = st.segmented_control("Status", options=[":material/play_arrow: Started", ":material/pause: Not Started"], default=None, label_visibility="collapsed")
        started = status_options == ":material/play_arrow: Started"
        not_started = status_options == ":material/pause: Not Started"

    with st.expander(":material/business: Company Filters", expanded=False):
        region = st.multiselect("Region", get_lookup_values("region"))
        existing_countries = df.get('country', pd.Series()).dropna().unique()
        country = st.multiselect("Country", sorted(set(get_lookup_values("country") + list(existing_countries))))
        sector = st.multiselect("GICS Sector", get_lookup_values("gics_sector"))

    with st.expander(":material/forum: Engagement Type", expanded=False):
        esg_opt = st.segmented_control("By Category", options=[":material/eco: E", ":material/groups: S", ":material/account_balance: G"], default=None, label_visibility="visible")
        esg = {None: [], ":material/eco: E": ["e"], ":material/groups: S": ["s"], ":material/account_balance: G": ["g"]}.get(esg_opt, [])

        theme_options_map = {":material/thermostat: Climate": "Climate Change", ":material/water_drop: Water": "Water", ":material/forest: Forests": "Forests"}
        selected_theme = theme_options_map.get(st.segmented_control("By Theme", options=list(theme_options_map.keys()), default=None, label_visibility="collapsed"))
        progs = st.multiselect("Program", get_lookup_values("program"))
        objectives = st.multiselect("Objective", get_lookup_values("objective"))

    with st.expander(":material/people: Engagement Status", expanded=False):
        initial_status_map = {":material/play_arrow: Started": "Started", ":material/pause: Not Started": "Not Started"}
        initial_status_selection = st.segmented_control("Initial Status", options=list(initial_status_map.keys()), default=None, label_visibility="collapsed")
        initial_status = [initial_status_map.get(initial_status_selection)] if initial_status_selection else []
        outcome = st.multiselect("Outcome", get_lookup_values("outcome"))
        sentiment = st.multiselect("Sentiment", get_lookup_values("sentiment"))

    return progs, sector, region, country, outcome, sentiment, initial_status, esg, started, not_started, selected_theme, objectives

def dashboard_page():
    data = st.session_state.DATA
    if data.empty: st.warning("No engagement data available. Add an engagement or adjust filters."); return

    selected_sub_page = option_menu(None, ["Overview", "Additional Analysis"], icons=["bar-chart-line", "globe-americas"], orientation="horizontal", styles=NAV_STYLES)

    if selected_sub_page == "Overview":
        with st.container(border=True):
            total = len(data)
            active = (data.get("initial_status", pd.Series(dtype=str)).str.lower().isin(["started"])).sum()
            completed = data.get("outcome", pd.Series(dtype=str)).str.lower().isin(["engagement complete"]).sum()
            not_started = data.get("initial_status", pd.Series(dtype=str)).str.lower().eq("not started").sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Engagements in System", total)
            with col2:
                st.metric("Initiated Engagements", active)
            with col3:
                st.metric("Engagements Not Started", not_started)

            response_received = data.get("outcome", pd.Series(dtype=str)).str.lower().eq("response received").sum()
            email_failed = data.get("outcome", pd.Series(dtype=str)).str.lower().eq("email failed").sum()

            col1, col2 = st.columns(2)
            col1.markdown(f'<div class="alert-success"><strong>✅ {response_received} Responses Received</strong><br>Positive engagement outcomes</div>', unsafe_allow_html=True)
            col2.markdown(f'<div class="alert-urgent"><strong>❌ {email_failed} Emails Failed</strong><br>Require follow-up action</div>', unsafe_allow_html=True)

            render_icon_header("query_stats", "Key Metrics")
            
            success = data.get("outcome", pd.Series(dtype=str)).isin(["Engagement Complete", "Response Received"]).sum()
            success_rate = round(success / total * 100) if total > 0 else 0
            fail_rate = round(data.get("outcome", pd.Series(dtype=str)).str.lower().eq("email failed").sum() / total * 100) if total > 0 else 0

            col1, col2, col3 = st.columns([1, 1, 3.5])
            with col1:
                st.metric("Complete Engagements", completed)
            with col2:
                st.metric("Success Rate", f"{success_rate}%")

            with col3:
                render_icon_header("center_focus_strong", "ESG Engagement Focus Areas", div_style="margin-top:-57px;")
                render_esg_gauges(data, ["Climate Change", "Water", "Forests", "Other"], "dashboard")

            render_icon_header("table_chart", "Engagement List")
            create_dataframe_component(data, Config.COLUMNS)

            with st.columns(6)[-1]:
                st.download_button("Download Table", data.to_csv(index=False).encode('utf-8'), f"filtered_engagements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv", icon=":material/download:", use_container_width=True)

    elif selected_sub_page == "Additional Analysis":
        with st.container(border=True):
            all_regions_options = ["Global"] + sorted(st.session_state.FULL_DATA.get("region", pd.Series()).dropna().unique())
            st.session_state.selected_region = st.selectbox("Focus on Region", all_regions_options, index=all_regions_options.index(st.session_state.selected_region) if st.session_state.selected_region in all_regions_options else 0, key='selected_region_selectbox')
            geo_df = data if st.session_state.selected_region == "Global" else data[data.get("region") == st.session_state.selected_region]

            col1, col2 = st.columns([1, 3])
            with col1: render_geo_metrics(len(geo_df), geo_df.get("country", pd.Series()).nunique(), geo_df.get("country", pd.Series()).mode()[0] if not geo_df.get("country", pd.Series()).empty else "None")
            with col2: render_geo_map(geo_df, st.session_state.selected_region)

            col1, col2 = st.columns([1, 1])
            with col1: render_geo_distribution_chart(data, geo_df, st.session_state.selected_region)
            with col2: render_esg_themes(geo_df)

            render_icon_header("domain", "Sector Distribution", 32, 28)
            sector_data = geo_df.get("gics_sector", pd.Series()).value_counts()
            if not sector_data.empty: st.plotly_chart(create_chart(sector_data, chart_type="bar", height=400), use_container_width=True)
            else: st.info("No sector data available for this selection.")

def engagement_operations_page():
    selected_sub_page = option_menu(None, ["Add New Engagement", "Add New Interaction", "Engagement Records", "Database"],
                                    icons=["plus-square", "pencil-square", "card-checklist", "cloud-upload"],
                                    orientation="horizontal", styles=NAV_STYLES)

    if selected_sub_page == "Add New Engagement":
        with st.form("new_engagement", clear_on_submit=False):
            render_icon_header("add_business", "Log New Engagement Target", 26, 18)
            col1, col2, col3 = st.columns([1.2, .75, 1])
            with col1:
                theme_selection = get_themes()
            with col2:
                st.write(" ")
            with col3:
                esg_selection = get_esg()
            col1, col2, col3 = st.columns(3)
            company = col1.text_input("Company Name *")
            isin = col2.text_input("ISIN *")
            aqr_id = col3.text_input("AQR ID")


            col1, col2, col3 = st.columns([1, 1, 1])
            program_options = [""] + get_lookup_values("program")
            program_default_index = program_options.index("CDP") if "CDP" in program_options else 0
            program = col1.selectbox("Program *", program_options, index=program_default_index)
            objective_options = [""] + get_lookup_values("objective")
            objective_default_index = objective_options.index("CDP Disclosure") if "CDP Disclosure" in objective_options else 0
            objective = col2.selectbox("Objective", objective_options, index=objective_default_index)

            col1, col2, col3 = st.columns(3)
            gics = col1.selectbox("GICS Sector *", [""] + get_lookup_values("gics_sector"))
            existing = sorted(st.session_state.FULL_DATA.get('country', pd.Series()).dropna().unique())
            countries = sorted(set(get_lookup_values("country") + list(existing)))
            country_choice = col2.selectbox("Country *", [""] + countries + ["Other (enter custom)"])
            
            if country_choice == "Other (enter custom)":
                country = col2.text_input("Enter Country Name *", key="custom_country")
            else:
                country = country_choice
                
            region = col3.selectbox("Region *", [""] + get_lookup_values("region"))

            render_icon_header("schedule", "Timeline", 24, 18)
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
                if not esg_selection: errors.append("Select at least one ESG focus")

                if errors:
                    st.error("\n".join(f"• {e}" for e in errors))
                else:
                    existing_names = st.session_state.FULL_DATA.get('company_name', pd.Series()).str.lower().tolist()
                    if company.lower() in existing_names:
                        st.error(f"'{company}' already exists")
                    else:
                        success, msg = create_engagement({
                            "company_name": company.strip(), "gics_sector": gics,
                            "region": region, "isin": isin.strip(), "aqr_id": aqr_id.strip(),
                            "program": program, "country": country, "objective": objective,
                            "start_date": start, "target_date": target, "created_by": "System",
                            "e": "e" in esg_selection, "s": "s" in esg_selection, "g": "g" in esg_selection,
                            "theme_flags": theme_selection
                        })

                        if success:
                            st.success(msg)
                            st.balloons()
                            refresh_data()
                            st.rerun()
                        else:
                            st.error(msg)

    elif selected_sub_page == "Add New Interaction":
        with st.container(border=True):

            render_icon_header("edit_note", "Add New Engagement Interaction", 26, 18)
            company = company_selector_widget(st.session_state.FULL_DATA, st.session_state.DATA, key="log_interaction_company")

            if not company: st.info("Select a company to log an interaction."); return

            eng = st.session_state.FULL_DATA[st.session_state.FULL_DATA["company_name"] == company].iloc[0]

            with st.expander("Engagement Details:", expanded=True):
                cols = st.columns(4)
                cols[0].markdown(f"**Program:**<br>{eng.get('program', 'N/A')}", unsafe_allow_html=True)
                
                theme_icons = {
                    "climate_change": ":material/thermostat:",
                    "water": ":material/water_drop:",
                    "forests": ":material/forest:",
                    "other": ":material/category:"
                }
                theme_names = {
                    "climate_change": "Climate Change",
                    "water": "Water", 
                    "forests": "Forests",
                    "other": "Other"
                }
                
                active_themes = []
                for theme_col, icon in theme_icons.items():
                    if eng.get(theme_col) == 'Y':
                        theme_name = theme_names[theme_col]
                        active_themes.append(f"{icon} {theme_name}")
                
                theme_display = ", ".join(active_themes) if active_themes else "N/A"
                cols[1].markdown(f"**Theme:**<br>{theme_display}", unsafe_allow_html=True)
                
                cols[2].markdown(f"**Objective:**<br>{eng.get('objective', 'N/A')}", unsafe_allow_html=True)
                cols[3].markdown(f"**Current Status:**<br>{eng.get('outcome', 'N/A')}", unsafe_allow_html=True)

            with st.form("log_interaction", clear_on_submit=False):
                render_icon_header("edit_note", "Interaction Details", 26, 18)
                col1, col2 = st.columns(2)
                int_type = col1.selectbox("Type *", [""] + get_lookup_values("interaction_type"))
                int_date = col2.date_input("Date *", value=datetime.now().date())

                col1, col2 = st.columns(2)
                outcome = col1.selectbox("Current Status *", [""] + get_lookup_values("outcome_status"))

                esc_opts = get_lookup_values("escalation_level")
                current_esc = eng.get("escalation_level", "")
                escalation = col2.selectbox("Escalation", [current_esc] + [x for x in esc_opts if x != current_esc])

                summary = st.text_area("Summary *", height=150)

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

    elif selected_sub_page == "Database":
        with st.container(border=True):
            render_icon_header("cloud_upload", "Upload Engagement Data", 24, 18)
            uploaded_file = st.file_uploader(" ", type="csv", accept_multiple_files=False, label_visibility="collapsed")
            st.info("Please note that uploading data overrides existing data. Current data will be archived before importing the new file.")
            
            
            if uploaded_file is not None:
                try:
                    new_df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                    new_df = fix_column_names(new_df)
                    
                    required_columns = ['company_name', 'gics_sector', 'region', 'country', 'program']
                    missing_columns = [col for col in required_columns if col not in new_df.columns]
                    
                    if missing_columns:
                        st.error(f"Missing required columns: {', '.join(missing_columns)}")
                    else:
                        st.success(f"File validated successfully. Found {len(new_df)} engagements.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("New Engagements", len(new_df))
                        with col2:
                            st.metric("Current Engagements", len(st.session_state.FULL_DATA))
                        
                        if st.button("Import Data", type="primary"):
                            success, msg = import_csv_data(new_df)
                            if success:
                                st.success(msg)
                                refresh_data()
                                st.rerun()
                            else:
                                st.error(msg)
                                
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
            render_hr()
            if st.toggle("Show Full Database", value=False):
                with st.spinner("Loading full database..."):
                    time.sleep(0.5)
                    full_df = st.session_state.FULL_DATA
                    st.dataframe(full_df)
                    st.download_button(
                        "Download Full Database",
                        full_df.to_csv(index=False).encode('utf-8'),
                        f"full_engagement_db_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        icon=":material/download:",
                        use_container_width=True
                    )

    elif selected_sub_page == "Engagement Records":
        full_df = st.session_state.FULL_DATA
        filtered_df = st.session_state.DATA
        with st.container(border=True):
            render_icon_header("fact_check", "Engagement Records", 24, 18)

            company = company_selector_widget(full_df, filtered_df, key="engagement_records_company")
            if not company:
                st.info("Select a company to Display its Engagement History.")
                return

            data_record = full_df[full_df["company_name"] == company]
            if data_record.empty:
                st.info(f"No record found for company '{company}'.")
                return
            data = data_record.iloc[0]

            col1, col2 = st.columns([2.5, 1])
            
            with col1:
                with st.container(border=True):
                    render_icon_header("apartment", f"{data['company_name']}", 24, 18)
                    cols = st.columns(3)
                    cols[0].markdown(f"**Sector:** {data.get('gics_sector', 'N/A')}")
                    cols[1].markdown(f"**Country:** {data.get('country', 'N/A')}")
                    cols[2].markdown(f"**Region:** {data.get('region', 'N/A')}")
                with st.container(border=True):
                    render_icon_header("schedule", "Engagement Information", 24, 18)
                    cols = st.columns(3)
                    cols[0].markdown(f"**Program:** {data.get('program', 'N/A')}")
                    cols[1].markdown(f"**Objective:** {data.get('objective', 'N/A')}")
                    cols[2].markdown(f"**Current Status:** {data.get('outcome', 'N/A')}")

                    render_engagement_focus_themes(data)
                
            with col2:
                render_engagement_metrics(data)
                render_engagement_summary(data)

            with st.container(border=True):
                display_interaction_history(data['engagement_id'])


def task_management_page():
    with st.container(border=True):
        render_icon_header("calendar_month", "Engagement Calendar", 24, 18)
        df = st.session_state.DATA
        if df.empty or 'next_action_date' not in df.columns: st.warning("No tasks with upcoming dates are available or selected filters yield no results."); return
        tasks_df = df.dropna(subset=['next_action_date']).copy()
        if tasks_df.empty: st.info("No engagements to display for the current filter selection."); return
        urgent_tasks = tasks_df[tasks_df['urgent']].sort_values('next_action_date')
        
        # Add title for upcoming engagements section
        render_icon_header("schedule", "Upcoming Actions", 20, 16, div_style="margin:15px 0 10px 0;")
        
        if urgent_tasks.empty:
            st.info("No urgent actions required.")
        else:
            # Display in column format, up to 5 items per row
            urgent_list = urgent_tasks.to_dict('records')
            
            for i in range(0, len(urgent_list), 5):
                # Create columns for up to 5 items
                batch = urgent_list[i:i+5]
                cols = st.columns(len(batch))
                
                for j, row in enumerate(batch):
                    with cols[j]:
                        st.markdown(f"**{row['company_name']}**")
                        st.caption(f"Due: {pd.to_datetime(row['next_action_date']).strftime('%d %b')}")
            
            # Add spacing after urgent tasks
            st.markdown("---")
        calendar_events, _ = df_to_calendar_events(tasks_df)
        calendar(events=calendar_events, key="calendar_multi_month_view")

PAGE_FUNCTIONS = {"Dashboard": dashboard_page, "Engagement Log": engagement_operations_page, "Calendar": task_management_page}

def main():
    st.set_page_config(page_title=Config.APP_TITLE, page_icon=Config.APP_ICON, layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        '<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" '
        'rel="stylesheet">',
        unsafe_allow_html=True
    )
    load_local_css(Path(__file__).parent / "assets" / "style.css")

    _initialize_session_state()

    if not st.session_state.data_refreshed:
        with st.spinner('Loading application data...'):
            refresh_data()

    st.markdown(f'<div style="margin-bottom:-20px;"><span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:28px;">{'travel_explore'}</span><span style="vertical-align:middle;font-size:26px;font-weight:600;margin-left:10px;">{Config.APP_TITLE}</span></div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:11px 0 12px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)
    if st.session_state.FULL_DATA.empty:
        st.warning("No engagement data found. Please add an engagement to begin.")
        engagement_operations_page()
        st.stop()

    with st.sidebar:
        st.markdown(" ")
        titles = list(PAGES_CONFIG.keys())
        icons = [PAGES_CONFIG.get(p, {}).get('icon') for p in titles]

        selected = option_menu("Navigation", titles, icons=icons, menu_icon="cast", default_index=st.session_state['main_nav_default'], styles=NAV_STYLES, key="main_navigation")

        if selected != st.session_state.selected_page:
            st.session_state.selected_page = selected
            st.session_state.main_nav_default = titles.index(selected)
            st.rerun()

        st.markdown('<hr style="margin:0px 0 8px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)
        col1, col2 = st.columns([5, 2.5])
        with col1: st.markdown(f'<div style="margin-left:15px;"><span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:16px;">{'tune'}</span><span style="vertical-align:middle;font-size:16px;font-weight:500;margin-left:5px">Toggle Filtering</span></div>', unsafe_allow_html=True)
        col2.toggle("", value=st.session_state.enable_filtering, key="enable_filtering")
        st.markdown('<hr style="margin:0px 0 8px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)

        if st.session_state.enable_filtering:
            st.session_state.DATA = apply_filters(st.session_state.FULL_DATA, sidebar_filters(st.session_state.FULL_DATA))
        else:
            st.session_state.DATA = st.session_state.FULL_DATA.copy()

    if page_func := PAGE_FUNCTIONS.get(st.session_state.selected_page): page_func()
    else: st.error("Page not found.")

if __name__ == "__main__": main()