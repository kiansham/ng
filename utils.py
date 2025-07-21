import pandas as pd
import json
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import country_converter as coco
import uuid
import re
from typing import Union
from pathlib import Path
from config import Config

@st.cache_resource
def get_country_converter():
    return coco.CountryConverter()

cc = get_country_converter()

@st.cache_data
def _read_css(path: Path) -> str:
    return path.read_text() if path.is_file() else ""

def load_css(path: Union[str, Path]) -> None:
    path = Path(path)
    css = _read_css(path)
    if not css:
        st.warning(f"CSS file not found: {path}")
        return
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def refresh_data():
    load_db.clear()
    get_interactions.clear()
    get_lookup.clear()

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
        df = fix_columns(df)
        
        date_cols = ["start_date", "target_date", "last_interaction_date", "next_action_date", "created_date"]
        for col in date_cols:
            if col in df.columns: 
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
                
        bool_cols = ['e', 's', 'g', 'repeat']
        for col in bool_cols:
            if col in df.columns: 
                df[col] = df[col].astype(str).str.lower().isin(['true', '1', 'yes', 'y'])
                
        if 'interactions' not in df.columns: 
            df['interactions'] = '[]'
        
        theme_cols = ['climate_change', 'water', 'forests', 'other']
        for col in theme_cols:
            if col not in df.columns:
                df[col] = 'N'
        
        if 'repeat' not in df.columns:
            df['repeat'] = False
        
        df['theme'] = df.apply(get_row_themes, axis=1).astype(str).replace('None', '')
    
    if Config.CONFIG_JSON_PATH.exists():
        with Config.CONFIG_JSON_PATH.open() as f: 
            config = json.load(f)
        
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
    
    for col in ['e', 's', 'g', 'repeat']:
        if col in df_save.columns: 
            df_save[col] = df_save[col].astype(str).str.upper()
            
    if 'interactions' not in df_save.columns: 
        df_save['interactions'] = '[]'
    
    try:
        df_save.to_csv(Config.ENGAGEMENTS_CSV_PATH, index=False)
        load_db.clear()
    except PermissionError:
        raise PermissionError(f"Cannot save to {Config.ENGAGEMENTS_CSV_PATH}. Please close Excel or any other application that has this file open, then try again.")
    except Exception as e:
        raise Exception(f"Error saving engagement data: {str(e)}")

def import_csv_data(new_df: pd.DataFrame):
    try:
        current_df, _ = load_db()
        
        if not current_df.empty:
            archive = Config.ENGAGEMENTS_CSV_PATH.parent / f"archive_engagements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            current_df.to_csv(archive, index=False)
        
        date_cols = ["start_date", "target_date", "last_interaction_date", "next_action_date", "created_date"]
        for col in date_cols:
            if col in new_df.columns:
                new_df[col] = pd.to_datetime(new_df[col], dayfirst=True, errors='coerce')
        
        for col in ['e', 's', 'g', 'repeat']:
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
def get_interactions(engagement_id: int):
    df, _ = load_db()
    if df.empty or engagement_id is None: 
        return []
    record = df[pd.to_numeric(df.get('engagement_id'), errors='coerce') == int(engagement_id)]
    if record.empty: 
        return []
    interactions = record.iloc[0].get('interactions', '[]')
    try: 
        return json.loads(interactions) if pd.notna(interactions) and interactions.strip() else []
    except (json.JSONDecodeError, TypeError): 
        return []

def create_engagement(data: dict):
    df, _ = load_db()
    if not df.empty and data.get('company_name', '').lower() in df.get('company_name', pd.Series()).str.lower().tolist():
        return False, f"'{data.get('company_name')}' already exists."
    
    next_id = (df['engagement_id'].max() + 1) if not df.empty and 'engagement_id' in df.columns else 1
    
    themes = data.get("theme_flags", {})
    
    new_record = {
        "engagement_id": next_id, 
        "company_name": data.get("company_name", ""), 
        "isin": data.get("isin", ""),
        "aqr_id": data.get("aqr_id", ""), 
        "gics_sector": data.get("gics_sector", ""), 
        "country": data.get("country", ""),
        "region": data.get("region", ""), 
        "program": data.get("program", ""), 
        "objective": data.get("objective", ""), 
        "start_date": data.get("start_date"), 
        "target_date": data.get("target_date"),
        "e": data.get("e", False), 
        "s": data.get("s", False), 
        "g": data.get("g", False),
        "climate_change": 'Y' if themes.get("climate_change", False) else 'N',
        "water": 'Y' if themes.get("water", False) else 'N',
        "forests": 'Y' if themes.get("forests", False) else 'N',
        "other": 'Y' if themes.get("other", False) else 'N',
        "created_date": datetime.now(), 
        "created_by": data.get("created_by", "System"), 
        "last_interaction_date": None,
        "next_action_date": data.get("start_date"), 
        "initial_status": data.get("initial_status", "Not Started"), 
        "outcome": data.get("initial_status", "Not Started"),
        "sentiment": "No Response", 
        "escalation_level": "None Required", 
        "outcome_status": "N/A", 
        "interactions": "[]",
        "repeat": data.get("repeat", False),
    }
    
    new_df = pd.DataFrame([new_record])
    
    if not df.empty:
        for col in df.columns:
            if col not in new_df.columns:
                new_df[col] = pd.NA
        for col in new_df.columns:
            if col not in df.columns:
                df[col] = pd.NA

    df = pd.concat([df, new_df], ignore_index=True)
    
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
    if idx.empty: 
        return False, "Engagement not found."
    idx = idx[0]
    
    for key, value in data.items():
        if key in df.columns and value is not None and value != "":
            if key in ["last_interaction_date", "next_action_date"]:
                df.loc[idx, key] = pd.to_datetime(value)
            else:
                df.loc[idx, key] = value
    
    try: 
        interactions = json.loads(df.loc[idx, "interactions"] or '[]')
    except (json.JSONDecodeError, TypeError): 
        interactions = []
    
    int_date = data.get("date") or data.get("last_interaction_date")
    interactions.append({
        "interaction_id": str(uuid.uuid4()), 
        "interaction_type": data.get("interaction_type", "N/A"),
        "interaction_summary": data.get("interaction_summary", "No summary provided").strip(), 
        "interaction_date": pd.to_datetime(int_date).strftime('%Y-%m-%d'),
        "outcome_status": data.get("outcome_status", "N/A"), 
        "logged_by": "System", 
        "logged_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    df.loc[idx, "interactions"] = json.dumps(interactions, indent=2)
    
    try:
        save_engagements_df(df)
        get_interactions.clear()
        return True, "Interaction logged successfully."
    except PermissionError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Failed to save interaction: {str(e)}"

@st.cache_data(ttl=600)
def get_lookup(field: str):
    _, config = load_db()
    return [str(v) for v in config.get(field, []) if v]

def render_header(icon: str, text: str, icon_size: int = 30, text_size: int = 28, div_style: str = "margin:4px 0 12px 0;"):
    st.markdown(f'<div style="{div_style}"><span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:{icon_size}px;">{icon}</span><span style="vertical-align:middle;font-size:{text_size}px;font-weight:600;margin-left:10px;">{text}</span></div>', unsafe_allow_html=True)

def show_table(df: pd.DataFrame, cols: list = None):
    if df.empty: 
        st.info("No data to display.")
        return
        
    display = df[[c for c in cols if c in df.columns]].copy() if cols else df.copy()
    
    date_cols = ['last_interaction_date', 'next_action_date', 'target_date']
    for col in date_cols:
        if col in display.columns: 
            display[col] = pd.to_datetime(display[col], errors='coerce').dt.strftime("%d/%m/%Y").fillna(' ')
    
    format_col = lambda c: 'GICS Sector' if c.lower() == 'gics_sector' else c.replace('_', ' ').title()
    st.dataframe(display.rename(columns={col: format_col(col) for col in display.columns}), use_container_width=True, hide_index=True)

def make_chart(data: pd.Series, chart_type: str = "bar", **kwargs):
    colors = kwargs.get('colors', Config.CB_SAFE_PALETTE)
    orientation = kwargs.get('orientation', 'v')
    
    if chart_type == "bar":
        if orientation == 'h':
            fig = px.bar(x=data.values, y=data.index, color=data.index, 
                        color_discrete_sequence=colors, orientation='h')
        else:
            fig = px.bar(x=data.index, y=data.values, color=data.index, 
                        color_discrete_sequence=colors)
    else:
        fig = go.Figure()
    # Set appropriate axis titles based on orientation
    if orientation == 'h':
        x_title = kwargs.get('xaxis_title', "Count")
        y_title = kwargs.get('yaxis_title', "")
    else:
        x_title = kwargs.get('xaxis_title', "")
        y_title = kwargs.get('yaxis_title', "Count")
    
    fig.update_layout(
        title=kwargs.get('title', ''), 
        xaxis_title=x_title, 
        yaxis_title=y_title,
        paper_bgcolor=kwargs.get('paper_bgcolor', Config.CHART_DEFAULTS["paper_bgcolor"]),
        plot_bgcolor=kwargs.get('plot_bgcolor', Config.CHART_DEFAULTS["plot_bgcolor"]),
        margin=kwargs.get('margin', Config.CHART_DEFAULTS["margin"]),
        height=kwargs.get('height', Config.CHART_DEFAULTS["height"]),
        showlegend=kwargs.get('showlegend', Config.CHART_DEFAULTS["showlegend"])
    )
    return fig

def make_gauge(label: str, value: int, colour: str, percentage: float = None):
    tooltip = f"{label}<br/>Count: {value}" + (f"<br/>Share: {percentage}%" if percentage is not None else "")
    display = max(0, min(100, int(percentage or 0)))
    return {
        "tooltip": {"show": True, "formatter": tooltip},
        "series": [{
            "type": "gauge",
            "startAngle": 90,
            "endAngle": -270,
            "radius": "85%",
            "center": ["50%", "50%"],
            "min": 0,
            "max": 100,
            "progress": {
                "show": True,
                "width": 8,
                "roundCap": True,
                "itemStyle": {
                    "color": colour
                }
            },
            "axisLine": {
                "lineStyle": {
                    "width": 8,
                    "color": [[1, "#f0f2f6"]]
                }
            },
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {"show": False},
            "pointer": {"show": False},
            "title": {
                "show": True,
                "fontSize": 12,
                "fontWeight": 500,
                "color": "#666",
                "offsetCenter": [0, "30%"]
            },
            "detail": {
                "formatter": str(max(0, int(value or 0))),
                "fontSize": 23,
                "fontWeight": 600,
                "color": colour,
                "offsetCenter": [0, "-5%"],
                "valueAnimation": True
            },
            "data": [{"value": display, "name": label}],
            "animation": True,
            "animationDuration": 1200,
            "animationEasing": "cubicOut"
        }]
    }

def company_select(full: pd.DataFrame, filtered: pd.DataFrame, key: str = None):
    if full.empty:
        st.warning("No company data available.")
        return None
    
    companies = sorted(filtered["company_name"].unique()) if not filtered.empty else sorted(full["company_name"].unique())

    if not companies:
        st.info("No companies found with the current filters.")
        return None
    
    if not filtered.empty and len(filtered) < len(full):
        st.info(f"{len(companies)} companies match the current filters.")
        
    return st.selectbox("Select a Company to Display and Edit its Engagement History", companies, index=0, key=key)

def show_interactions(engagement_id: int):
    interactions = get_interactions(engagement_id)
    
    render_header('history', "Recent Interactions", 26, 18)
    
    if not interactions:
        st.info("No interactions recorded for this engagement.")
        return
    
    df = pd.DataFrame(interactions)
    df['interaction_date'] = pd.to_datetime(df.get('interaction_date'))
    df = df.sort_values('interaction_date', ascending=False)
    
    if df.empty:
        st.info("No interactions to display.")
    else:
        icons = {"Email": "email:", "Call": "call:", "Meeting": "groups:", "Letter": "mail:", "Video Call": "videocam:"}
        
        for _, row in df.iterrows():
            int_type = row.get('interaction_type', 'None Logged')
            icon = icons.get(int_type, "chat:")
            date_str = row.get('interaction_date').strftime('%d %b %Y')
            
            st.markdown(f"**{icon} {int_type} - {date_str}**")
            
            cols = st.columns(2)
            cols[0].markdown(f"**Outcome:** {row.get('outcome_status', 'None Logged')}")
            cols[1].markdown(f"**Sentiment:** {row.get('sentiment', 'None Logged')}")
            
            st.markdown(f"**Summary:** {row.get('interaction_summary', 'No summary provided.')}")
            st.markdown('<hr style="margin:8px 0 12px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)

def show_themes(data):
    mapping = {"Climate": "climate_change", "Water": "water", "Forests": "forests", "Other": "other"}
    
    active = [name for name, col in mapping.items() if data.get(col) == 'Y']
    st.markdown(f"**Engagement Focus:** {', '.join(active) if active else 'N/A'}")
    
    themes = {"Climate": "thermostat", "Water": "water_drop", "Forests": "forest"}
    cols = st.columns(len(themes))
    
    for i, (theme, icon) in enumerate(themes.items()):
        col_name = {"Climate": "climate_change", "Water": "water", "Forests": "forests"}[theme]
        is_active = data.get(col_name) == 'Y'
        color = Config.ESG_COLORS.get(theme, 'white') if is_active else '#e8e8e8'
        
        with cols[i]:
            st.markdown(f"""
            <div style="text-align:center; padding: 5px; border-radius: 10px; background-color: {color}20;">
                <span class="material-icons-outlined" style="font-size: 36px; color: {color};">{icon}</span>
                <div style="font-size: 12px; font-weight: 500; color: {color}; margin-top: 5px;">{theme}</div>
            </div>
            """, unsafe_allow_html=True)

def show_summary(data):
    with st.container(border=True):
        render_header("summarize", "Engagement Actions", 20, 18)
        initial = data.get('initial_status', '').lower()
        last = pd.to_datetime(data.get('last_interaction_date'))
        next = pd.to_datetime(data.get('next_action_date'))
        
        col1, col2 = st.columns([1,1])
        
        if initial == 'not started':
            col1.markdown(f"**Last Contact:**")
            col1.markdown(f"None Yet")
            col2.markdown(f"**Next Action:**")
            start = pd.to_datetime(data.get('start_date'))
            col2.markdown(f"{start.strftime('%d %b %Y') if pd.notna(start) else ' '}")
        else:
            col1.markdown(f"**Last Contact:**")
            col1.markdown(f"{last.strftime('%d %b %Y') if pd.notna(last) else 'N/A'}")
            col2.markdown(f"**Next Action:**")
            col2.markdown(f"{next.strftime('%d %b %Y') if pd.notna(next) else 'None'}")

def show_metrics(data):
    with st.container(border=True):        
        colors = {
            "In Progress": "#3498db",
            "Response Received": "#2ecc71",
            "Engagement Complete": "#27ae60",
            "No Response": "#f39c12",
            "Email Failed": "#e74c3c",
            "Follow Up - First": "#f39c12",
            "Follow Up - Second": "#e67e22"
        }
        
        outcome = data.get('outcome', 'Not Started')
        color = colors.get(outcome, "#95a5a6")
        
        st.markdown(f"""
        <div style="text-align:center; padding:20px;">
            <div style="font-size:16px; color:#666; margin-top:5px;">Current Status:</div>
            <div style="font-size:22px; font-weight:bold; color:{color};">{outcome}</div>
        </div>
        """, unsafe_allow_html=True)

def render_geo_metrics(total: int, countries: int, most_active: str):
    st.metric("Total Engagements", total)
    st.metric("Countries Engaged", countries)
    st.metric("Most Active Country", most_active)

@st.cache_data
def _convert_to_iso(countries: tuple) -> list:
    return cc.convert(names=list(countries), to='ISO3')

def render_map(geo_df: pd.DataFrame, region: str):
    if geo_df.empty or "country" not in geo_df.columns or geo_df["country"].dropna().empty:
        st.info("No geographic data available for selected region.")
        return
        
    df = geo_df.groupby("country").size().reset_index(name="count")
    df['iso_code'] = _convert_to_iso(tuple(df['country']))
    df = df[df['iso_code'] != 'not found']
    if df.empty:
        st.warning("No valid geographic data to display on the map.")
        return

    PLOTLY_SCOPES = {
        "Global": "world", "North America": "north america", "South America": "south america",
        "Europe": "europe", "Asia": "asia", "Africa": "africa"
    }
    BBOXES = {
        "Oceania": {"lon": [110, 180], "lat": [-50, 10]},
        "South America": {"lon": [-82, -34], "lat": [-56, 13]},
        "Africa": {"lon": [-20, 55], "lat": [-35, 38]},
        "North America": {"lon": [-170, -50], "lat": [5, 75]}
    }

    fig = px.choropleth(
        df,
        locations="iso_code",
        color="count",
        hover_name="country",
        color_continuous_scale="teal",
        range_color=[0, df['count'].max() or 1]
    )
    
    geo_args = {}
    if region in BBOXES:
        bbox = BBOXES[region]
        geo_args.update({
            "scope": "world", "fitbounds": False,
            "lonaxis_range": bbox["lon"], "lataxis_range": bbox["lat"]
        })
    else:
        scope = PLOTLY_SCOPES.get(region, "world")
        fit = False if region == "Global" else "locations"
        geo_args.update({"scope": scope, "fitbounds": fit})
    
    fig.update_geos(**geo_args)
    
    fig.update_layout(
        geo=dict(
            bgcolor='rgba(0,0,0,0)', showframe=False, showcoastlines=False, 
            showcountries=True, showland=False, showocean=False, showlakes=False
        ),
        height=340, margin=dict(l=10, r=40, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    
    fig.update_coloraxes(colorbar=dict(thickness=4, len=0.6, x=0.95, xpad=3, y=0.5))
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Engagements: %{z}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

def render_distribution(data: pd.DataFrame, geo_df: pd.DataFrame, region: str):
    chart_data = data.get("region", pd.Series()).value_counts() if region == "Global" else geo_df.get("country", pd.Series()).value_counts()
    title = "Regional Distribution" if region == "Global" else f"Countries in {region}"
    render_header("analytics", title, 32, 28)
    
    if chart_data is not None and not chart_data.empty:
        if region == "Global":
            y = chart_data.index.tolist()
            x = chart_data.values.tolist()
            base_colors = Config.CB_SAFE_PALETTE
            repeats = (len(y) // len(base_colors)) + 1
            colors = (base_colors * repeats)[:len(y)]
            fig = go.Figure()
            for i, (region_name, value) in enumerate(zip(y, x)):
                fig.add_trace(go.Scatter(
                    x=[0, value], y=[region_name, region_name], mode='lines',
                    line=dict(color='#bbb', width=3),
                    showlegend=False,
                    hoverinfo='skip',
                ))
                fig.add_trace(go.Scatter(
                    x=[value], y=[region_name], mode='markers+text',
                    marker=dict(size=14, color=colors[i]),
                    text=[value],
                    textposition='middle right',
                    textfont=dict(size=14),
                    showlegend=False,
                    hovertemplate='<b>%{y}</b><br>Count: %{x}<extra></extra>'
                ))
            fig.update_layout(
                height=200,
                margin=dict(l=2, r=10, t=2, b=2),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(title=' ', showgrid=False, zeroline=False),
                yaxis=dict(title='', showgrid=False, zeroline=False, autorange='reversed'),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            y = chart_data.index.tolist()
            x = chart_data.values.tolist()
            base_colors = Config.CB_SAFE_PALETTE
            repeats = (len(y) // len(base_colors)) + 1
            colors = (base_colors * repeats)[:len(y)]
            fig = go.Figure()
            for i, (country, value) in enumerate(zip(y, x)):
                fig.add_trace(go.Scatter(
                    x=[0, value], y=[country, country], mode='lines',
                    line=dict(color='#bbb', width=3),
                    showlegend=False,
                    hoverinfo='skip',
                ))
                fig.add_trace(go.Scatter(
                    x=[value], y=[country], mode='markers+text',
                    marker=dict(size=14, color=colors[i]),
                    text=[value],
                    textposition='middle right',
                    textfont=dict(size=14),
                    showlegend=False,
                    hovertemplate='<b>%{y}</b><br>Count: %{x}<extra></extra>'
                ))
            fig.update_layout(
                height=200,
                margin=dict(l=2, r=10, t=2, b=2),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(title=' ', showgrid=False, zeroline=False),
                yaxis=dict(title='', showgrid=False, zeroline=False, autorange='reversed'),
            )
            st.plotly_chart(fig, use_container_width=True)
    else: 
        st.info("No data to display for this selection.")

def render_gauges(data: pd.DataFrame, themes: list, key_prefix: str):
    from streamlit_echarts import st_echarts
    
    mapping = {"Climate": "climate_change", "Water": "water", "Forests": "forests", "Other": "other"}
    
    theme_data = {}
    for theme in themes:
        col = mapping.get(theme, theme.lower().replace(' ', '_'))
        theme_data[theme] = (data[col] == "Y").sum() if col in data.columns else 0
            
    total = sum(theme_data.values())

    if total > 0:
        for i in range(0, len(themes), 2):
            cols = st.columns(2)
            for j in range(2):
                if (idx := i + j) < len(themes):
                    theme = themes[idx]
                    with cols[j]:
                        count = int(theme_data.get(theme, 0))
                        pct = int(round((count / total) * 100)) if total > 0 else 0
                        context = "overview" if key_prefix == "dashboard" else "geo_analysis"
                        key = f"esg_{context}_{key_prefix}_{theme.lower().replace(' ', '_')}"
                        st_echarts(options=make_gauge(theme, count, Config.ESG_COLORS.get(theme), pct),
                                 height="200px", key=key)
    else: 
        st.info("No ESG themes data available for the selected region or filter.")

def apply_filters(df: pd.DataFrame, filters: tuple):
    if df.empty: 
        return df
        
    progs, sector, region, country, outcome, sentiment, status, esg, urgent, upcoming, theme, objectives, repeat_values = filters
    
    conditions = []
    mappings = {"program": progs, "gics_sector": sector, "region": region, "country": country, 
                "outcome": outcome, "sentiment": sentiment, "initial_status": status, "objective": objectives}
    
    for col, vals in mappings.items():
        if vals and col in df.columns: 
            conditions.append(df[col].isin(vals))

    if theme:
        mapping = {"Climate": "climate_change", "Water": "water", "Forests": "forests", "Other": "other"}
        normalized = mapping.get(theme, theme.lower().replace(' ', '_'))
        if normalized in df.columns: 
            conditions.append(df[normalized] == "Y")

    if esg:
        esg_conds = [df[flag] for flag in esg if flag in df.columns]
        if esg_conds:
            conditions.append(pd.concat(esg_conds, axis=1).any(axis=1))
        
    if urgent and "urgent" in df.columns: 
        conditions.append(df["urgent"] == True)
        
    if upcoming and "next_action_date" in df.columns:
        days = (pd.to_datetime(df["next_action_date"]) - pd.Timestamp.now().normalize()).dt.days
        conditions.append(days.between(0, 30))
    
    if repeat_values and "repeat" in df.columns:
        conditions.append(df["repeat"].isin(repeat_values))
        
    if not conditions: 
        return df
    
    mask = pd.Series(True, index=df.index)
    for cond in conditions:
        if not cond.empty: 
            mask &= cond
        
    return df[mask]

def to_calendar_events(df: pd.DataFrame):
    events = []
    resources = [{"id": p, "title": p} for p in df.get("program", pd.Series()).dropna().unique()]
    
    for _, row in df.iterrows():
        if pd.notna(row.get("next_action_date")):
            next_dt = pd.to_datetime(row.get("next_action_date"))
            days = (next_dt - pd.Timestamp.now().normalize()).days
            
            cls = "event-urgent" if days <= Config.URGENT_DAYS else "event-warning" if days <= Config.WARNING_DAYS else "event-upcoming"
            events.append({
                "title": row.get("company_name"), 
                "start": next_dt.isoformat(), 
                "end": (next_dt + timedelta(hours=1)).isoformat(),
                "resourceId": row.get("program"), 
                "classNames": [cls]
            })
    return events, resources

def get_row_themes(row):
    mapping = {"Climate": "climate_change", "Water": "water", "Forests": "forests", "Other": "other"}
    themes = [label for label, col in mapping.items() if col in row and str(row[col]).strip().upper() == 'Y']
    return ', '.join(themes) or 'None'

def fix_columns(df: pd.DataFrame):
    if df.empty: 
        return df
        
    normalize = lambda c: re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_')
    renames = {}
    targets = {'company_name', 'country', 'gics_sector', 'isin', 'aqr_id', 'program', 'theme', 'objective', 
               'start_date', 'target_date', 'e', 's', 'g', 'climate_change', 'water', 'forests', 'other', 
               'created_date', 'created_by', 'last_interaction_date', 'next_action_date', 'initial_status',
               'outcome', 'sentiment', 'escalation_level', 'outcome_status', 'interactions', 'outcome_colour', 
               'repeat', 'engagement_id'}
    
    for col in df.columns:
        norm = normalize(col)
        if norm in targets and col != norm:
            if norm == 'company_name' and 'company name' not in col.lower() and 'company_name' not in col.lower():
                continue
            renames[col] = norm
        if 'outcome_color' in norm or 'outcome_colour' in norm:
            renames[col] = 'outcome_colour'
            
    return df.rename(columns=renames)

# Inject custom CSS to reduce vertical spacing between ESG gauge chart rows
st.markdown("""
    <style>
    /* Further reduce vertical spacing between Streamlit columns containing echarts */
    .element-container:has(.stEcharts) {
        margin-bottom: -18px !important;
        padding-bottom: 0 !important;
    }
    }
    </style>
""", unsafe_allow_html=True)