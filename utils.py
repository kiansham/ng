import pandas as pd
import json
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid
import re
from typing import Union
from pathlib import Path
from config import Config

def load_local_css(css_path: Union[str, Path]) -> None:
    path = Path(css_path)
    if not path.is_file():
        st.warning(f"CSS file not found: {path}")
        return
    css = path.read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def refresh_data():
    load_db.clear()
    get_interactions_for_company.clear()
    get_lookup_values.clear()

    df, _ = load_db()
    st.session_state.FULL_DATA = df
    st.session_state.DATA = df.copy()
    st.session_state.data_refreshed = True
    st.session_state.refresh_counter += 1

@st.cache_data(ttl=300)
def load_db():
    df, config = pd.DataFrame(), {}
    if Config.ENGAGEMENTS_CSV_PATH.exists():
        df = pd.read_csv(Config.ENGAGEMENTS_CSV_PATH, encoding='utf-8-sig')
        df = fix_column_names(df)
        for col in ["start_date", "target_date", "last_interaction_date", "next_action_date", "created_date"]:
            if col in df.columns: df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
        for col in ['e', 's', 'g']:
            if col in df.columns: df[col] = df[col].astype(str).str.lower().isin(['true', '1', 'yes', 'y'])
        if 'interactions' not in df.columns: df['interactions'] = '[]'
        
        esg_theme_columns = ['climate_change', 'water', 'forests', 'other']
        for col in esg_theme_columns:
            if col not in df.columns:
                df[col] = 'N'
        
        df['theme'] = df.apply(get_themes_for_row, axis=1).astype(str).replace('None', '')
    
    if Config.CONFIG_JSON_PATH.exists():
        with Config.CONFIG_JSON_PATH.open() as f: config = json.load(f)
        
    if not df.empty:
        now = pd.Timestamp.now()
        df["days_to_next_action"] = (df.get("next_action_date", pd.NaT) - now).dt.days
        df["is_complete"] = df.get("outcome", pd.Series(dtype=str)).str.lower().isin(["engagement complete", "response received"])
        df["on_time"] = df.get("is_complete", False) & (df.get("target_date", pd.NaT) >= now)
        df["late"] = df.get("is_complete", False) & (df.get("target_date", pd.NaT) < now)
        df["overdue"] = (df.get("next_action_date", pd.NaT) < now) & (~df.get("is_complete", True))
        df["urgent"] = df.get("days_to_next_action", 999) <= Config.URGENT_DAYS
        
    return df, config

def save_engagements_df(df: pd.DataFrame):
    Config.ENGAGEMENTS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_save = df.copy()
    for col in ['e', 's', 'g']:
        if col in df_save.columns: df_save[col] = df_save[col].astype(str).str.upper()
    if 'interactions' not in df_save.columns: df_save['interactions'] = '[]'
    
    try:
        df_save.to_csv(Config.ENGAGEMENTS_CSV_PATH, index=False)
        load_db.clear()
    except PermissionError:
        raise PermissionError(
            f"Cannot save to {Config.ENGAGEMENTS_CSV_PATH}. "
            "Please close Excel or any other application that has this file open, then try again."
        )
    except Exception as e:
        raise Exception(f"Error saving engagement data: {str(e)}")

def import_csv_data(new_df: pd.DataFrame):
    try:
        current_df, _ = load_db()
        
        if not current_df.empty:
            archive_path = Config.ENGAGEMENTS_CSV_PATH.parent / f"archive_engagements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            current_df.to_csv(archive_path, index=False)
        
        for col in ["start_date", "target_date", "last_interaction_date", "next_action_date", "created_date"]:
            if col in new_df.columns:
                new_df[col] = pd.to_datetime(new_df[col], dayfirst=True, errors='coerce')
        
        for col in ['e', 's', 'g']:
            if col in new_df.columns:
                new_df[col] = new_df[col].astype(str).str.upper()
        
        if 'engagement_id' not in new_df.columns:
            new_df['engagement_id'] = range(1, len(new_df) + 1)
        
        if 'interactions' not in new_df.columns:
            new_df['interactions'] = '[]'
            
        save_engagements_df(new_df)
        return True, f"Successfully imported {len(new_df)} engagements. Previous data archived."
        
    except Exception as e:
        return False, f"Import failed: {str(e)}"

@st.cache_data(ttl=600)
def get_interactions_for_company(engagement_id: int):
    df, _ = load_db()
    if df.empty or engagement_id is None: return []
    record = df[pd.to_numeric(df.get('engagement_id'), errors='coerce') == int(engagement_id)]
    if record.empty: return []
    interactions = record.iloc[0].get('interactions', '[]')
    try: return json.loads(interactions) if pd.notna(interactions) and interactions.strip() else []
    except (json.JSONDecodeError, TypeError): return []

def create_engagement(data: dict):
    df, _ = load_db()
    if not df.empty and data.get('company_name', '').lower() in df.get('company_name', pd.Series()).str.lower().tolist():
        return False, f"'{data.get('company_name')}' already exists."
    next_id = (df['engagement_id'].max() + 1) if not df.empty and 'engagement_id' in df.columns else 1
    
    theme_flags = data.get("theme_flags", {})
    
    climate_change_flag = 'Y' if theme_flags.get("climate_change", False) else 'N'
    water_flag = 'Y' if theme_flags.get("water", False) else 'N'
    forests_flag = 'Y' if theme_flags.get("forests", False) else 'N'
    other_flag = 'Y' if theme_flags.get("other", False) else 'N'

    new_record = {
        "engagement_id": next_id, "company_name": data.get("company_name", ""), "isin": data.get("isin", ""),
        "aqr_id": data.get("aqr_id", ""), "gics_sector": data.get("gics_sector", ""), "country": data.get("country", ""),
        "region": data.get("region", ""), "program": data.get("program", ""), "theme": data.get("theme", ""),
        "objective": data.get("objective", ""), "start_date": data.get("start_date"), "target_date": data.get("target_date"),
        "e": data.get("e", False), "s": data.get("s", False), "g": data.get("g", False),
        "climate_change": climate_change_flag, 
        "water": water_flag,
        "forests": forests_flag, 
        "other": other_flag,
        "created_date": datetime.now(), "created_by": data.get("created_by", "System"), "last_interaction_date": None,
        "next_action_date": data.get("start_date"), "initial_status": data.get("initial_status", "Not Started"), "outcome": data.get("initial_status", "Not Started"),
        "sentiment": "No Response", "escalation_level": "None Required", "outcome_status": "N/A", "interactions": "[]",
    }
    new_df_record = pd.DataFrame([new_record])
    
    if not df.empty:
        for col in [c for c in df.columns if c not in new_df_record.columns]:
            new_df_record[col] = pd.NA
        for col in [c for c in new_df_record.columns if c not in df.columns]:
            df[col] = pd.NA

    df = pd.concat([df, new_df_record], ignore_index=True)
    try:
        save_engagements_df(df)
        return True, f"Engagement for '{data.get('company_name')}' created successfully (ID: {next_id})."
    except PermissionError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Failed to save engagement: {str(e)}"

def log_interaction(data: dict):
    df, _ = load_db()
    engagement_id = data.get("engagement_id")
    idx = df[pd.to_numeric(df.get('engagement_id'), errors='coerce') == int(engagement_id)].index
    if idx.empty: return False, "Engagement not found."
    idx = idx[0]
    
    for key, value in data.items():
        if key in df.columns and value is not None and value != "":
            if key in ["last_interaction_date", "next_action_date"]:
                df.loc[idx, key] = pd.to_datetime(value)
            else:
                df.loc[idx, key] = value
    
    try: interactions = json.loads(df.loc[idx, "interactions"] or '[]')
    except (json.JSONDecodeError, TypeError): interactions = []
    
    interaction_date = data.get("date") or data.get("last_interaction_date")
    interactions.append({
        "interaction_id": str(uuid.uuid4()), "interaction_type": data.get("interaction_type", "N/A"),
        "interaction_summary": data.get("interaction_summary", "No summary provided").strip(), 
        "interaction_date": pd.to_datetime(interaction_date).strftime('%Y-%m-%d'),
        "outcome_status": data.get("outcome_status", "N/A"), "logged_by": "System", 
        "logged_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    df.loc[idx, "interactions"] = json.dumps(interactions, indent=2)
    try:
        save_engagements_df(df)
        get_interactions_for_company.clear()
        return True, "Interaction logged successfully."
    except PermissionError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Failed to save interaction: {str(e)}"

@st.cache_data(ttl=600)
def get_lookup_values(field: str):
    _, config = load_db()
    return [str(v) for v in config.get(field, []) if v]

def render_icon_header(icon: str, text: str, icon_size: int = 30, text_size: int = 28, div_style: str = "margin:4px 0 12px 0;"):
    st.markdown(f'<div style="{div_style}"><span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:{icon_size}px;">{icon}</span><span style="vertical-align:middle;font-size:{text_size}px;font-weight:600;margin-left:10px;">{text}</span></div>', unsafe_allow_html=True)

def render_hr(margin_top: int = 8, margin_bottom: int = 12):
    st.markdown(f'<hr style="margin:{margin_top}px 0 {margin_bottom}px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)

def create_dataframe_component(df: pd.DataFrame, columns_to_display: list = None):
    if df.empty: st.info("No data to display."); return
    df_display = df[[c for c in columns_to_display if c in df.columns]].copy() if columns_to_display else df.copy()
    
    for col in ['last_interaction_date', 'next_action_date', 'target_date']:
        if col in df_display.columns: 
            df_display[col] = pd.to_datetime(df_display[col], errors='coerce').dt.strftime("%d/%m/%Y").fillna(' ')
    
    format_header = lambda c: 'GICS Sector' if c.lower() == 'gics_sector' else c.replace('_', ' ').title()
    st.dataframe(df_display.rename(columns={col: format_header(col) for col in df_display.columns}), use_container_width=True, hide_index=True)

def create_chart(data: pd.Series, chart_type: str = "bar", **kwargs):
    colors = kwargs.get('colors', Config.CB_SAFE_PALETTE)
    fig = px.bar(x=data.index, y=data.values, color=data.index, color_discrete_sequence=colors) if chart_type == "bar" else go.Figure()
    fig.update_layout(
        title=kwargs.get('title', ''), xaxis_title="", yaxis_title="",
        paper_bgcolor=kwargs.get('paper_bgcolor', Config.CHART_DEFAULTS["paper_bgcolor"]),
        plot_bgcolor=kwargs.get('plot_bgcolor', Config.CHART_DEFAULTS["plot_bgcolor"]),
        margin=kwargs.get('margin', Config.CHART_DEFAULTS["margin"]),
        height=kwargs.get('height', Config.CHART_DEFAULTS["height"]),
        showlegend=kwargs.get('showlegend', Config.CHART_DEFAULTS["showlegend"]))
    return fig

def create_esg_gauge(label: str, value: int, colour: str, percentage: float = None):
    tooltip = f"{label}<br/>Count: {value}" + (f"<br/>Share: {percentage}%" if percentage is not None else "")
    display_value = max(0, min(100, int(percentage or 0)))
    return {
        "tooltip": {"show": True, "formatter": tooltip},
        "series": [{
            "type": "gauge", "startAngle": 180, "endAngle": 0, "radius": "115%",
            "center": ["45%", "58%"], "itemStyle": {"color": colour},
            "progress": {"show": True, "width": 15},
            "axisLine": {"lineStyle": {"width": 15, "color": [[1, "#f0f2f6"]]}},
            "splitLine": {"show": False}, "axisTick": {"show": False},
            "axisLabel": {"show": False}, "pointer": {"show": False}, "min": 0, "max": 100,
            "data": [{"value": display_value, "name": label}],
            "title": {"show": True, "offsetCenter": [0, "-30%"], "fontSize": 14, "fontWeight": 600, "color": "#262730"},
            "detail": {"formatter": str(max(0, int(value or 0))), "offsetCenter": [0, 5], "fontSize": 24, "fontWeight": 700, "color": colour, "valueAnimation": True},
            "animation": True, "animationDuration": 1000
        }]
    }

def company_selector_widget(full_df: pd.DataFrame, filtered_df: pd.DataFrame, key: str = None):
    if full_df.empty:
        st.warning("No company data available.")
        return None
    
    companies = []
    if not filtered_df.empty:
        companies = sorted(filtered_df["company_name"].unique())
    else:
        companies = sorted(full_df["company_name"].unique())

    if not companies:
        st.info("No companies found with the current filters.")
        return None
    
    if not filtered_df.empty and len(filtered_df) < len(full_df):
        st.info(f"{len(companies)} companies match the current filters.")
        
    return st.selectbox("Select a Company to Display and Edit its Engagement History", companies, index=0, key=key)

def display_interaction_history(engagement_id: int):
    interactions = get_interactions_for_company(engagement_id)
    
    render_icon_header('history', "Recent Interactions", 26, 18)
    
    if not interactions:
        st.info("No interactions recorded for this engagement.")
        return
    
    df = pd.DataFrame(interactions)
    df['interaction_date'] = pd.to_datetime(df.get('interaction_date'))
    df = df.sort_values('interaction_date', ascending=False)
    
    if df.empty:
        st.info("No interactions to display.")
    else:
        for _, row in df.iterrows():
            # Add Material UI icons for interaction types
            interaction_icons = {
                "Email": ":material/email:",
                "Call": ":material/call:",
                "Meeting": ":material/groups:",
                "Letter": ":material/mail:",
                "Video Call": ":material/videocam:"
            }
            
            interaction_type = row.get('interaction_type', 'None Logged')
            icon = interaction_icons.get(interaction_type, ":material/chat:")
            date_str = row.get('interaction_date').strftime('%d %b %Y')
            
            st.markdown(f"**{icon} {interaction_type} - {date_str}**")
            
            # Use consistent formatting for outcome and sentiment
            cols = st.columns(2)
            cols[0].markdown(f"**Outcome:** {row.get('outcome_status', 'None Logged')}")
            cols[1].markdown(f"**Sentiment:** {row.get('sentiment', 'None Logged')}")
            
            st.markdown(f"**Summary:** {row.get('interaction_summary', 'No summary provided.')}")
            render_hr()

def render_engagement_focus_themes(data):
    themes_mapping = {"Climate": "climate_change", "Water": "water", "Forests": "forests", "Other": "other"}
    
    active_themes = []
    for theme_name, col_name in themes_mapping.items():
        if data.get(col_name) == 'Y':
            active_themes.append(theme_name)
    
    focus_areas = ", ".join(active_themes) if active_themes else "N/A"
    st.markdown(f"**Engagement Focus:** {focus_areas}")
    
    themes = {"Climate": "thermostat", "Water": "water_drop", "Forests": "forest"}
    # Use the same mapping as the text section for column names
    theme_to_column = {"Climate": "climate_change", "Water": "water", "Forests": "forests"}
    cols = st.columns(len(themes))
    
    for i, (theme, icon) in enumerate(themes.items()):
        col_name = theme_to_column[theme]
        is_active = data.get(col_name) == 'Y'
        color = Config.ESG_COLORS.get(theme, 'white') if is_active else '#e8e8e8'
        
        with cols[i]:
            st.markdown(f"""
            <div style="text-align:center; padding: 5px; border-radius: 10px; background-color: {color}20;">
                <span class="material-icons-outlined" style="font-size: 36px; color: {color};">{icon}</span>
                <div style="font-size: 12px; font-weight: 500; color: {color}; margin-top: 5px;">{theme}</div>
            </div>
            """, unsafe_allow_html=True)

def render_engagement_summary(data):
    with st.container(border=True):
        render_icon_header("summarize", "Engagement Actions", 20, 18)
        initial_status = data.get('initial_status', '').lower()
        last_contact = pd.to_datetime(data.get('last_interaction_date'))
        next_action = pd.to_datetime(data.get('next_action_date'))
        
        cols1,cols2 = st.columns([1,1])
        
        if initial_status == 'not started':
            cols1.markdown(f"**Last Contact:**")
            cols1.markdown(f"None Yet")
            cols2.markdown(f"**Next Action:**")
            start_date = pd.to_datetime(data.get('start_date'))
            cols2.markdown(f"{start_date.strftime('%d %b %Y') if pd.notna(start_date) else ' '}")
        else:
            cols1.markdown(f"**Last Contact:**")
            cols1.markdown(f"{last_contact.strftime('%d %b %Y') if pd.notna(last_contact) else 'N/A'}")
            cols2.markdown(f"**Next Action:**")
            cols2.markdown(f"{next_action.strftime('%d %b %Y') if pd.notna(next_action) else 'None'}")

def render_engagement_metrics(data):
    with st.container(border=True):        
        outcome_color_map = {
            "In Progress": "#3498db",
            "Response Received": "#2ecc71",
            "Engagement Complete": "#27ae60",
            "No Response": "#f39c12",
            "Email Failed": "#e74c3c",
            "Follow Up - First": "#f39c12",
            "Follow Up - Second": "#e67e22"
        }
        
        current_outcome = data.get('outcome', 'Not Started')
        color = outcome_color_map.get(current_outcome, "#95a5a6")
        
        st.markdown(f"""
        <div style="text-align:center; padding:20px;">
            <div style="font-size:16px; color:#666; margin-top:5px;">Current Status:</div>
            <div style="font-size:22px; font-weight:bold; color:{color};">{current_outcome}</div>
        </div>
        """, unsafe_allow_html=True)
        
def render_esg_category_display(data):
    """Displays the E, S, G focus for an engagement."""
    with st.container(border=True):
        render_icon_header("category", "ESG Category", 20, 18)
        esg_map = {'e': 'Environmental', 's': 'Social', 'g': 'Governance'}
        active_esg = [esg_map[flag] for flag in esg_map if data.get(flag)]
        
        if not active_esg:
            st.info("No ESG category selected.")
        else:
            for esg in active_esg:
                st.markdown(f"- **{esg}**")
def render_esg_focus_chart(data):
    with st.container(border=True):
        render_icon_header("center_focus_strong", "Engagement Focus", 26, 18)
        
        esg_data = {
            'Environmental': 'Y' if data.get('e', False) else 'N',
            'Social': 'Y' if data.get('s', False) else 'N',
            'Governance': 'Y' if data.get('g', False) else 'N'
        }
        
        active_esg = [k for k, v in esg_data.items() if v == 'Y']
        
        if active_esg:
            fig = go.Figure(go.Pie(
                labels=active_esg,
                values=[1] * len(active_esg),
                hole=0.4,
                marker_colors=["#2E8B57", "#4682B4", "#9370DB"][:len(active_esg)]
            ))
            
            fig.update_layout(
                height=200,
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=True,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No ESG focus areas selected")

def get_themes_for_row(row):
    theme_cols = {"Climate": "climate_change", "Water": "water", "Forests": "forests", "Other": "other"}
    themes = [label for label, col in theme_cols.items() if col in row and str(row[col]).strip().upper() == 'Y']
    return ', '.join(themes) or 'None'

def fix_column_names(df: pd.DataFrame):
    if df.empty: return df
    normalize = lambda c: re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_')
    rename_map = {}
    target_names = {'company_name', 'country', 'gics_sector', 'isin', 'aqr_id', 'program', 'theme', 'objective', 
                    'start_date', 'target_date', 'e', 's', 'g', 'climate_change', 'water', 'forests', 'other', 
                    'created_date', 'created_by', 'last_interaction_date', 'next_action_date', 'initial_status',
                    'outcome', 'sentiment', 'escalation_level', 'outcome_status', 'interactions', 'outcome_colour', 'repeat',
                    'engagement_id', 'milestone', 'milestone_status', 'interaction_type', 'interaction_summary', 'outcome_date'}
    
    for col in df.columns:
        normalized_col = normalize(col)
        if normalized_col in target_names and col != normalized_col:
            if normalized_col == 'company_name' and 'company name' not in col.lower() and 'company_name' not in col.lower():
                continue
            rename_map[col] = normalized_col
        if 'outcome_color' in normalized_col or 'outcome_colour' in normalized_col:
            rename_map[col] = 'outcome_colour'
    return df.rename(columns=rename_map)

def render_geo_metrics(total: int, countries: int, most_active: str):
    st.metric("Total Engagements", total)
    st.metric("Countries Engaged", countries)
    st.metric("Most Active Country", most_active)

def render_geo_map(geo_df: pd.DataFrame, selected_region: str):
    if geo_df.empty or "country" not in geo_df.columns or geo_df["country"].dropna().empty:
        st.info("No geographic data available for the selected region."); return
    
    country_data = geo_df.groupby("country").size().reset_index(name="count")
    country_data['iso_code'] = country_data['country'].map(Config.COUNTRY_ISO_MAP)
    mapped = country_data.dropna(subset=['iso_code'])

    if mapped.empty: st.warning("No countries found with valid ISO codes for mapping."); return

    fig = px.choropleth(mapped, locations="iso_code", color="count", hover_name="country",
                        color_continuous_scale="Viridis", range_color=[0, mapped["count"].max()])
    
    scope_mapping = {"Global": "world", "Asia": "asia", "Europe": "europe", "North America": "north america", 
                     "South America": "south america", "Oceania": "asia"}
    
    fig.update_layout(
        geo=dict(bgcolor='rgba(0,0,0,0)', showframe=False, showcoastlines=True, showcountries=False,
                 showland=False, showocean=False, showlakes=False,
                 scope=scope_mapping.get(selected_region, "world"),
                 fitbounds="locations" if selected_region != "Global" else False, visible=True),
        height=300, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    fig.update_coloraxes(colorbar=dict(thickness=5, len=0.7, x=1.02, xpad=10, y=0.5))
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Engagements: %{z}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

def render_geo_distribution_chart(data: pd.DataFrame, geo_df: pd.DataFrame, selected_region: str):
    chart_data = data.get("region", pd.Series()).value_counts() if selected_region == "Global" else geo_df.get("country", pd.Series()).value_counts()
    chart_title = "Regional Distribution" if selected_region == "Global" else f"Countries in {selected_region}"
    render_icon_header("pie_chart", chart_title, 32, 28)
    if chart_data is not None and not chart_data.empty:
        fig = go.Figure(go.Pie(labels=chart_data.index, values=chart_data.values, hole=0.8, 
                              marker_colors=Config.CB_SAFE_PALETTE[:len(chart_data)], 
                              textinfo='percent', hoverinfo='label+value', textfont_size=12))
        fig.update_layout(height=375, margin=dict(l=10, r=100, t=40, b=10), 
                         paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                         showlegend=True, legend=dict(orientation="v", yanchor="top", y=0.5, 
                                                     xanchor="right", x=1.05, font=dict(size=10)))
        st.plotly_chart(fig, use_container_width=False)
    else: st.info("No data to display for this selection.")

def render_esg_themes(geo_df: pd.DataFrame):
    render_icon_header("eco", "ESG Themes", 32, 28)
    if geo_df.empty: st.info("No data available for ESG analysis."); return
    render_esg_gauges(geo_df, ["Climate", "Water", "Forests", "Other"], "geo")

def render_esg_gauges(data: pd.DataFrame, theme_cols: list, key_prefix: str):
    from streamlit_echarts import st_echarts
    
    name_mapping = {"Climate": "climate_change", "Water": "water", "Forests": "forests", "Other": "other"}
    
    theme_data = {}
    for theme in theme_cols:
        col_name = name_mapping.get(theme, theme.lower().replace(' ', '_'))
        if col_name in data.columns:
            theme_data[theme] = (data[col_name] == "Y").sum()
        else:
            theme_data[theme] = 0
            
    total_themes = sum(theme_data.values())

    if total_themes > 0:
        
        for row_idx in range(0, len(theme_cols), 2):
            gauge_cols = st.columns(2)
            for col_idx in range(2):
                if (theme_idx := row_idx + col_idx) < len(theme_cols):
                    theme = theme_cols[theme_idx]
                    with gauge_cols[col_idx]:
                        count = int(theme_data.get(theme, 0))
                        percentage = int(round((count / total_themes) * 100)) if total_themes > 0 else 0
                        import hashlib
                        tab_context = "overview" if key_prefix == "dashboard" else "geo_analysis"
                        data_signature = f"{key_prefix}_{theme}_{len(data)}_{total_themes}"
                        signature_hash = hashlib.md5(data_signature.encode()).hexdigest()[:12]
                        unique_key = f"esg_{tab_context}_{key_prefix}_{theme.lower().replace(' ', '_')}_{signature_hash}"
                        st_echarts(options=create_esg_gauge(theme, count, Config.ESG_COLORS.get(theme), percentage), 
                                 height="200px", key=unique_key)
    else: st.info("No ESG themes data available for the selected region or filter.")

def apply_filters(df: pd.DataFrame, filters: tuple):
    if df.empty: return df
    progs, sector, region, country, outcome, sentiment, initial_status, esg, urgent, upcoming, selected_theme, objectives = filters
    
    conditions = []
    filter_map = {"program": progs, "gics_sector": sector, "region": region, "country": country, 
                  "outcome": outcome, "sentiment": sentiment, "initial_status": initial_status, "objective": objectives}
    
    for col, vals in filter_map.items():
        if vals and col in df.columns: conditions.append(df[col].isin(vals))

    if selected_theme:
        theme_mapping = {"Climate": "climate_change", "Water": "water", "Forests": "forests", "Other": "other"}
        normalized_theme = theme_mapping.get(selected_theme, selected_theme.lower().replace(' ', '_'))
        if normalized_theme in df.columns: conditions.append(df[normalized_theme] == "Y")

    if esg:
        esg_conditions = []
        for esg_flag in esg:
            if esg_flag in df.columns:
                esg_conditions.append(df[esg_flag])
        
        if esg_conditions:
            conditions.append(pd.concat(esg_conditions, axis=1).any(axis=1))
        
    if urgent and "urgent" in df.columns: conditions.append(df["urgent"] == True)
    if upcoming and "next_action_date" in df.columns:
        days_ahead = (pd.to_datetime(df["next_action_date"]) - pd.Timestamp.now().normalize()).dt.days
        conditions.append(days_ahead.between(0, 30))
        
    if not conditions: return df
    
    combined_mask = pd.Series(True, index=df.index)
    for condition in conditions:
        if not condition.empty: combined_mask &= condition
        
    return df[combined_mask]

def df_to_calendar_events(df: pd.DataFrame):
    events = []
    resources = [{"id": prog, "title": prog} for prog in df.get("program", pd.Series()).dropna().unique()]
    
    for _, row in df.iterrows():
        if pd.notna(row.get("next_action_date")):
            next_action_dt = pd.to_datetime(row.get("next_action_date"))
            days_left = (next_action_dt - pd.Timestamp.now().normalize()).days
            
            className = "event-urgent" if days_left <= Config.URGENT_DAYS else "event-warning" if days_left <= Config.WARNING_DAYS else "event-upcoming"
            events.append({"title": row.get("company_name"), "start": next_action_dt.isoformat(), 
                          "end": (next_action_dt + timedelta(hours=1)).isoformat(),
                          "resourceId": row.get("program"), "classNames": [className]})
    return events, resources

def get_themes():
    theme_options = [
        ":material/thermostat: Climate",
        ":material/water_drop: Water", 
        ":material/forest: Forests",
        ":material/category: Other"
    ]
    selected_themes = st.pills("Themes", theme_options, selection_mode="multi", key='theme_pills')
    
    theme_flags = {
        "climate_change": ":material/thermostat: Climate" in selected_themes,
        "water": ":material/water_drop: Water" in selected_themes,
        "forests": ":material/forest: Forests" in selected_themes,
        "other": ":material/category: Other" in selected_themes
    }
    return theme_flags

def get_esg():
    esg_options = [
        ":material/eco: E",
        ":material/groups: S", 
        ":material/account_balance: G"
    ]
    selected_esg = st.pills("ESG Category", esg_options, selection_mode="multi", key='esg_pills')
    result_esg = []
    if ":material/eco: E" in selected_esg:
        result_esg.append("e")
    if ":material/groups: S" in selected_esg:
        result_esg.append("s")
    if ":material/account_balance: G" in selected_esg:
        result_esg.append("g")
    return result_esg