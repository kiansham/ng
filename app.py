import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar
from config import Config, NAV_STYLES, PAGES_CONFIG
from utils import *
from pathlib import Path

@st.cache_data
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8')

def init_state():
    defaults = {
        'FULL_DATA': pd.DataFrame(),
        'DATA': pd.DataFrame(),
        'selected_page': 'Dashboard',
        'data_refreshed': False,
        'refresh_counter': 0,
        'selected_region': 'Global',
        'main_nav_default': 0,
        'enable_filtering': False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def sidebar_filters(df: pd.DataFrame):
    with st.expander(':material/info: Status Filters', expanded=False):
        pills = st.pills("Filter: Started, Not Started, Repeats", options=[":material/check_circle:", ":material/block:", ":material/repeat:"], selection_mode="multi", key="combined_filter_pills", label_visibility="visible")
        
        status_values = []
        repeat_values = []
        
        if pills:
            if ":material/check_circle:" in pills:
                status_values.append("Started")
            if ":material/block:" in pills:
                status_values.append("Not Started")
            if ":material/repeat:" in pills:
                repeat_values.append(True)

    filters = {}
    
    with st.expander(":material/business: Company Filters", expanded=False):
        filters['region'] = st.multiselect("Region", get_lookup("region"), placeholder="By Region", label_visibility="collapsed")
        existing = df.get('country', pd.Series()).dropna().unique()
        filters['country'] = st.multiselect("Country", sorted(set(get_lookup("country") + list(existing))), placeholder="By Country", label_visibility="collapsed")
        filters['sector'] = st.multiselect("GICS Sector", get_lookup("gics_sector"), placeholder="By Sector", label_visibility="collapsed")

    with st.expander(":material/forum: Engagement Type", expanded=False):
        esg_pills = st.pills("By Category", options=[":material/eco: E", ":material/groups: S", ":material/account_balance: G"], selection_mode="multi", key="esg_pills")
        filters['esg'] = []
        if ":material/eco: E" in esg_pills: filters['esg'].append("e")
        if ":material/groups: S" in esg_pills: filters['esg'].append("s")
        if ":material/account_balance: G" in esg_pills: filters['esg'].append("g")
        
        theme_pills = st.pills("By Theme", options=[":material/thermostat: Climate", ":material/water_drop: Water", ":material/forest: Forests"], selection_mode="multi", key="theme_pills", label_visibility="collapsed")
        theme_map = {":material/thermostat: Climate": "Climate", ":material/water_drop: Water": "Water", ":material/forest: Forests": "Forests"}
        filters['theme'] = None
        for pill in theme_pills:
            if pill in theme_map:
                filters['theme'] = theme_map[pill]
                break
                
        filters['progs'] = st.multiselect("Program", get_lookup("program"), placeholder="By Engagement Program", label_visibility="collapsed")
        filters['objectives'] = st.multiselect("Objective", get_lookup("objective"), placeholder="By Objective", label_visibility="collapsed")

    with st.expander(":material/people: Engagement Status", expanded=False):
        filters['outcome'] = st.multiselect("Outcome", get_lookup("outcome"), placeholder="By Status", label_visibility="collapsed")
        filters['sentiment'] = st.multiselect("Sentiment", get_lookup("sentiment"), placeholder="By Sentiment", label_visibility="collapsed")

    return filters['progs'], filters['sector'], filters['region'], filters['country'], filters['outcome'], filters['sentiment'], status_values, filters['esg'], False, False, filters['theme'], filters['objectives'], repeat_values

def render_progress_bars(metrics: dict):
    rate = metrics.get('response_rate', 0)
    st.markdown(f"Response Rate ({rate:.0f}%)")
    st.progress(int(rate))

    rate = metrics.get('success_rate', 0)
    st.markdown(f"Success Rate ({rate:.0f}%)")
    st.progress(int(rate))

    rate = metrics.get('email_failed', 0)
    st.markdown(f"Email Failed Rate ({rate:.0f}%)")
    st.progress(int(rate))

    rate = metrics.get('completion_rate', 0)
    st.markdown(f"Completion Rate ({rate:.0f}%)")
    st.progress(int(rate))


def dashboard_page():
    data = st.session_state.DATA
    if data.empty: 
        st.warning("No engagement data available. Add an engagement or adjust filters.")
        return

    selected = option_menu(None, ["Overview"], icons=["bar-chart-line"], orientation="horizontal", styles=NAV_STYLES)

    if selected == "Overview":
        with st.container(border=True):
            total = len(data)
            active = (data.get("initial_status", pd.Series(dtype=str)).str.lower() == "started").sum()
            not_started = (data.get("initial_status", pd.Series(dtype=str)).str.lower() == "not started").sum()
            completed = (data.get("outcome", pd.Series(dtype=str)).str.lower() == "engagement complete").sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Engagements Planned", total)
            col2.metric("Initiated Engagements", active)
            col3.metric("Engagements Completed", completed)

            col1, col2, col3 = st.columns([1.5,3,3])
            with col1:
                render_header("query_stats", "Key Metrics")
            with col2:
                theme_pills = st.pills(" Filter by Engagement Type", options=[
                    ":material/thermostat: Climate", 
                    ":material/water_drop: Water", 
                    ":material/forest: Forests"
                ], selection_mode="multi", key="analysis_theme_pills", label_visibility="visible")
                if theme_pills:
                    theme_conditions = []
                    theme_map = {
                        ":material/thermostat: Climate": "climate_change",
                        ":material/water_drop: Water": "water", 
                        ":material/forest: Forests": "forests"
                    }
                    for pill in theme_pills:
                        if pill in theme_map:
                            col_name = theme_map[pill]
                            if col_name in data.columns:
                                theme_conditions.append(data[col_name] == "Y")
                    
                    if theme_conditions:
                        theme_mask = pd.concat(theme_conditions, axis=1).any(axis=1) if len(theme_conditions) > 1 else theme_conditions[0]
                        data = data[theme_mask]
            with col3:
                regions = ["Global"] + sorted(st.session_state.FULL_DATA.get("region", pd.Series()).dropna().unique())
                region = st.selectbox("Filter by Region", regions, key='region_select')
                st.session_state.selected_region = region
                geo_df = data if region == "Global" else data[data.get("region") == region]

            
            col1, col2 = st.columns([1,2])
            with col1:
                completed = (data.get("outcome", pd.Series(dtype=str)).str.lower() == "engagement complete").sum()
                success = data.get("outcome", pd.Series(dtype=str)).isin(["Engagement Complete", "Response Received"]).sum()
                response_received = (data.get("outcome", pd.Series(dtype=str)).str.lower() == "response received").sum()
                success_rate = round(success / total * 100) if total > 0 else 0
                response_rate = round(response_received / total * 100) if total > 0 else 0
                completion_rate = round(completed / total * 100) if total > 0 else 0
                metrics = {
                'success_rate': success_rate,
                'response_rate': response_rate,
                'completion_rate': completion_rate
                }
                render_progress_bars(metrics)
            
            with col2: 
                 render_map(geo_df, region)

            col1, col2 = st.columns([1, 1.5])
            with col1: 
                render_distribution(data, geo_df, region)
            with col2: 
                render_header("eco", "ESG Themes", 32, 28)
                if not geo_df.empty:
                    render_gauges(geo_df, ["Climate", "Water", "Forests", "Other"], "geo")
                else:
                    st.info("No data available for ESG analysis.")

            render_header("domain", "Sector Distribution", 32, 28)
            sector_data = geo_df.get("gics_sector", pd.Series()).value_counts()
            if not sector_data.empty: 
                st.plotly_chart(make_chart(sector_data, chart_type="bar", height=400), use_container_width=True)
            else: 
                st.info("No sector data available for this selection.")

            render_header("table_chart", "Engagement List")
            show_table(data, Config.COLUMNS)

            with st.columns(6)[-1]:
                csv = convert_df_to_csv(data)
                st.download_button("Download Table", csv, f"filtered_engagements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv", icon=":material/download:", use_container_width=True)

def ops_page():
    selected = option_menu(None, ["Add New Engagement", "Add New Interaction", "Engagement Records", "Database"],
                          icons=["plus-square", "pencil-square", "card-checklist", "cloud-upload"],
                          orientation="horizontal", styles=NAV_STYLES)

    if selected == "Add New Engagement":
        with st.form("new_engagement", clear_on_submit=False):
            render_header("add_business", "Log New Engagement Target", 26, 18)
            
            col1, col2, col3 = st.columns([1.2, .75, 1])
            with col1:
                theme_pills = st.pills("Themes", [":material/thermostat: Climate", ":material/water_drop: Water", ":material/forest: Forests", ":material/category: Other"], selection_mode="multi", key='theme_form_pills')
                themes = {
                    "climate_change": ":material/thermostat: Climate" in theme_pills,
                    "water": ":material/water_drop: Water" in theme_pills,
                    "forests": ":material/forest: Forests" in theme_pills,
                    "other": ":material/category: Other" in theme_pills
                }
            with col3:
                esg_pills = st.pills("ESG Category", [":material/eco: E", ":material/groups: S", ":material/account_balance: G"], selection_mode="multi", key='esg_form_pills')
                esg_flags = []
                if ":material/eco: E" in esg_pills: esg_flags.append("e")
                if ":material/groups: S" in esg_pills: esg_flags.append("s")
                if "account_balance: G" in esg_pills: esg_flags.append("g")

            col1, col2, col3 = st.columns(3)
            company = col1.text_input("Company Name *")
            isin = col2.text_input("ISIN *")
            aqr_id = col3.text_input("AQR ID")

            col1, col2, col3 = st.columns(3)
            gics = col1.selectbox("GICS Sector *", get_lookup("gics_sector"), index=None)
            existing = sorted(st.session_state.FULL_DATA.get('country', pd.Series()).dropna().unique())
            countries = sorted(set(get_lookup("country") + list(existing)))
            country = col2.selectbox("Country *", countries, index=None, accept_new_options=True)
            region = col3.selectbox("Region *", get_lookup("region"), index=None)

            col1, col2, col3, col4 = st.columns([1,1,1,1])
            programs = get_lookup("program")
            program = col1.selectbox("Program *", programs, index=programs.index("CDP") if "CDP" in programs else 0)
            objectives = get_lookup("objective")
            objective = col2.selectbox("Objective", objectives, index=objectives.index("CDP Disclosure") if "CDP Disclosure" in objectives else 0, accept_new_options=True)
            with col3:
                st.write(" ")
                st.write(" ")
                started = st.checkbox("Engagement Started", value=False, help="Select if email has already been sent")
            with col4:
                repeat_options = get_lookup("repeat")
                repeat_value = st.selectbox("Repeat Engagement", [""] + repeat_options, index=0, help="Select if this is a repeat engagement")
            
            start = st.date_input("Start Date *", value=datetime.now().date()) if started else None
            target = datetime(2025, 12, 31).date()

            if st.form_submit_button("Create Engagement", type="primary"):
                errors = []
                if not company.strip(): errors.append("Company name required")
                if not gics: errors.append("GICS Sector required")
                if not program: errors.append("Program required")
                if not country: errors.append("Country required")
                if not region: errors.append("Region required")
                if not esg_flags: errors.append("Select at least one ESG focus")

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
                            "e": "e" in esg_flags, "s": "s" in esg_flags, "g": "g" in esg_flags,
                            "theme_flags": themes, "initial_status": "Started" if started else "Not Started",
                            "repeat": repeat_value == "Yes" if repeat_value else False
                        })

                        if success:
                            refresh_data()
                            st.rerun()
                        else:
                            st.error(msg)

    elif selected == "Add New Interaction":
        with st.container(border=True):
            render_header("edit_note", "Add New Engagement Interaction", 26, 18)
            company = company_select(st.session_state.FULL_DATA, st.session_state.DATA, key="log_interaction_company")

            if not company: 
                st.info("Select a company to log an interaction.")
                return

            eng = st.session_state.FULL_DATA[st.session_state.FULL_DATA["company_name"] == company].iloc[0]

            with st.expander("Engagement Details:", expanded=True):
                cols = st.columns([0.5,1,1,1])
                cols[0].markdown(f"**Program:**<br>{eng.get('program', 'N/A')}", unsafe_allow_html=True)
                
                icons = {"climate_change": ":material/thermostat:", "water": ":material/water_drop:", "forests": ":material/forest:", "other": ":material/category:"}
                names = {"climate_change": "Climate", "water": "Water", "forests": "Forests", "other": "Other"}
                active = [f"{icons[k]} {names[k]}" for k in icons if eng.get(k) == 'Y']
                
                cols[1].markdown(f"**Theme:**<br>{', '.join(active) if active else 'N/A'}", unsafe_allow_html=True)
                cols[2].markdown(f"**Objective:**<br>{eng.get('objective', 'N/A')}", unsafe_allow_html=True)
                cols[3].markdown(f"**Current Status:**<br>{eng.get('outcome', 'N/A')}", unsafe_allow_html=True)

            with st.form("log_interaction", clear_on_submit=False):
                render_header("edit_note", "Interaction Details", 26, 18)
                col1, col2 = st.columns(2)
                int_type = col1.selectbox("Type *", [""] + get_lookup("interaction_type"))
                int_date = col2.date_input("Date *", value=datetime.now().date())

                col1, col2 = st.columns(2)
                outcome = col1.selectbox("Current Status *", [""] + get_lookup("outcome_status"))

                esc_opts = get_lookup("escalation_level")
                current_esc = eng.get("escalation_level", "")
                escalation = col2.selectbox("Escalation", [current_esc] + [x for x in esc_opts if x != current_esc])

                summary = st.text_area("Summary *", height=150)

                if st.form_submit_button("Log Interaction", type="primary"):
                    if not int_type or not summary.strip() or not outcome:
                        st.error("Fill all required fields")
                    else:
                        success, msg = log_interaction({
                            "engagement_id": eng["engagement_id"],
                            "date": int_date,
                            "interaction_summary": summary.strip(),
                            "interaction_type": int_type,
                            "outcome": outcome,
                            "escalation_level": escalation or current_esc
                        })
                        if success:
                            st.success(msg)
                            refresh_data()
                            st.rerun()
                        else:
                            st.error(msg)

    elif selected == "Database":
        with st.container(border=True):
            render_header("cloud_upload", "Database", 24, 18)
            
            st.caption('Editing and Uploading function should be updated by ESG Team only. Editing or Uploading data will potentially override existing data.')
            show_editable = st.toggle("Show Full Editable Database", value=False)
            if not show_editable:
                show_table(st.session_state.DATA, Config.COLUMNS)
            else:
                with st.form("edit_database_form", border=False, clear_on_submit=False):
                    full_df = st.session_state.FULL_DATA.copy()
                    
                    lookup_config = {}
                    config_cols = ["gics_sector", "region", "program", "theme", "interaction_type", 
                                  "repeat", "objective", "initial_status", "outcome", "sentiment", 
                                  "outcome_status", "outcome_colour", "escalation_level"]
                    for col in config_cols:
                        if col in full_df.columns:
                            lookup_config[col] = st.column_config.SelectboxColumn(
                                options=get_lookup(col),
                                required=col in ["gics_sector", "region", "program", "initial_status"]
                            )
                    edited_df = st.data_editor(full_df, hide_index=True, num_rows="dynamic", column_config=lookup_config, use_container_width=True)
                    if st.form_submit_button("Submit Changes"):
                        try:
                            save_engagements_df(edited_df)
                            refresh_data()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to save changes: {str(e)}")
            
            if st.toggle("Enable File Upload", value=False):
                uploaded = st.file_uploader(" ", type="csv", accept_multiple_files=False, label_visibility="collapsed")
                if uploaded:
                    try:
                        new_df = pd.read_csv(uploaded, encoding='utf-8-sig')
                        new_df = fix_columns(new_df)
                        required = ['company_name', 'gics_sector', 'region', 'country', 'program']
                        missing = [c for c in required if c not in new_df.columns]
                        if missing:
                            st.error(f"Missing required columns: {', '.join(missing)}")
                        else:
                            st.success(f"File validated successfully. Found {len(new_df)} engagements.")
                            
                            col1, col2 = st.columns(2)
                            col1.metric("New Engagements", len(new_df))
                            col2.metric("Current Engagements", len(st.session_state.FULL_DATA))
                            
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

    elif selected == "Engagement Records":
        full_df = st.session_state.FULL_DATA
        filtered = st.session_state.DATA
        with st.container(border=True):
            render_header("fact_check", "Engagement Records", 24, 18)

            company = company_select(full_df, filtered, key="engagement_records_company")
            if not company:
                st.info("Select a company to Display its Engagement History.")
                return

            records = full_df[full_df["company_name"] == company]
            if records.empty:
                st.info(f"No record found for company '{company}'.")
                return
            data = records.iloc[0]

            col1, col2 = st.columns([2.5, 1])
            
            with col1:
                with st.container(border=True):
                    render_header("apartment", f"{data['company_name']}", 24, 18)
                    cols = st.columns([1.5,1,1])
                    cols[0].markdown(f"**Sector:** {data.get('gics_sector', 'N/A')}")
                    cols[1].markdown(f"**Country:** {data.get('country', 'N/A')}")
                    cols[2].markdown(f"**Region:** {data.get('region', 'N/A')}")
                with st.container(border=True):
                    render_header("schedule", "Engagement Information", 24, 18)
                    cols = st.columns([0.8,1.5,1.5])
                    cols[0].markdown(f"**Program:** {data.get('program', 'N/A')}")
                    cols[1].markdown(f"**Objective:** {data.get('objective', 'N/A')}")
                    cols[2].markdown(f"**Current Status:** {data.get('outcome', 'N/A')}")

                    show_themes(data)
                
            with col2:
                show_metrics(data)
                show_summary(data)

            with st.container(border=True):
                show_interactions(data['engagement_id'])

def calendar_page():
    option_menu(None, ["Calendar"], icons=["calendar-month"], orientation="horizontal", styles=NAV_STYLES)

    with st.container(border=True):
        render_header("calendar_month", "Engagement Calendar", 24, 18)
        df = st.session_state.DATA
        if df.empty or 'next_action_date' not in df.columns: 
            st.warning("No tasks with upcoming dates are available or selected filters yield no results.")
            return
        tasks = df.dropna(subset=['next_action_date']).copy()
        if tasks.empty: 
            st.info("No engagements to display for the current filter selection.")
            return
        urgent = tasks[tasks['urgent']].sort_values('next_action_date')
        
        render_header("schedule", "Upcoming Actions", 20, 16, div_style="margin:15px 0 10px 0;")
        
        if urgent.empty:
            st.info("No urgent actions required.")
        else:
            urgent_list = urgent.to_dict('records')
            
            for i in range(0, len(urgent_list), 5):
                batch = urgent_list[i:i+5]
                cols = st.columns(len(batch))
                
                for j, row in enumerate(batch):
                    with cols[j]:
                        st.markdown(f"**{row['company_name']}**")
                        st.caption(f"Due: {pd.to_datetime(row['next_action_date']).strftime('%d %b')}")
            
            st.markdown("---")
        events, _ = to_calendar_events(tasks)
        calendar(events=events, key="calendar_multi_month_view")

PAGES = {"Dashboard": dashboard_page, "Engagement Log": ops_page, "Calendar": calendar_page}

def main():
    st.set_page_config(page_title=Config.APP_TITLE, page_icon=Config.APP_ICON, layout="wide", initial_sidebar_state="expanded")
    st.markdown('<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">', unsafe_allow_html=True)
    load_css(Path(__file__).parent / "assets" / "style.css")

    init_state()

    if not st.session_state.data_refreshed:
        with st.spinner('Loading application data...'):
            refresh_data()

    st.markdown(f'<div style="margin-bottom:-20px;"><span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:28px;">travel_explore</span><span style="vertical-align:middle;font-size:26px;font-weight:600;margin-left:10px;">{Config.APP_TITLE}</span></div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:11px 0 12px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)
    
    if st.session_state.FULL_DATA.empty:
        st.warning("No engagement data found. Please add an engagement to begin.")
        ops_page()
        st.stop()

    with st.sidebar:
        st.markdown(" ")
        titles = list(PAGES_CONFIG.keys())
        icons = [PAGES_CONFIG[p]['icon'] for p in titles]

        selected = option_menu("Navigation", titles, icons=icons, menu_icon="cast", default_index=st.session_state['main_nav_default'], styles=NAV_STYLES, key="main_navigation")

        if selected != st.session_state.selected_page:
            st.session_state.selected_page = selected
            st.session_state.main_nav_default = titles.index(selected)
            st.rerun()

        st.markdown('<hr style="margin:0px 0 8px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)
        col1, col2 = st.columns([5, 2.5])
        with col1: 
            st.markdown(f'<div style="margin-left:15px;"><span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:16px;">tune</span><span style="vertical-align:middle;font-size:16px;font-weight:500;margin-left:5px">Toggle Filtering</span></div>', unsafe_allow_html=True)
        col2.toggle("", value=st.session_state.enable_filtering, key="enable_filtering")
        st.markdown('<hr style="margin:0px 0 8px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)

        if st.session_state.enable_filtering:
            st.session_state.DATA = apply_filters(st.session_state.FULL_DATA, sidebar_filters(st.session_state.FULL_DATA))
        else:
            st.session_state.DATA = st.session_state.FULL_DATA.copy()

    if page := PAGES.get(st.session_state.selected_page): 
        page()
    else: 
        st.error("Page not found.")

if __name__ == "__main__": 
    main()