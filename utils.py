from __future__ import annotations
import pandas as pd
import json
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import re
import streamlit_shadcn_ui as ui
from config import Config

ENGAGEMENTS_CSV_PATH = Path("engagements.csv")
CONFIG_JSON_PATH = Path("configchoice.json")

class DataValidator:
    def __init__(self, choices):
        self.choices = choices
        self.required = ['gics_sector', 'region', 'program', 'country']

    def validate_field(self, field, value):
        if field not in self.choices:
            return True, None
            
        if field in self.required and not str(value).strip():
            return False, f"{field.replace('_', ' ').title()} is required."
        
        if value and value not in self.choices[field]:
            return False, f"Invalid {field}: '{value}'"
        
        return True, None
    
    def validate_record(self, record):
        errors = {}
        
        if not record.get('company_name', '').strip():
            errors['company_name'] = ["Company name required"]
        
        if not any(record.get(f, False) for f in ['e', 's', 'g']):
            errors['esg_flags'] = ["Select at least one ESG flag"]
        
        for field, value in record.items():
            if field in self.choices:
                valid, msg = self.validate_field(field, value)
                if not valid:
                    errors.setdefault(field, []).append(msg)
        
        return errors

@st.cache_data(ttl=300)
def load_db():
    df, config = pd.DataFrame(), {}
    
    try:
        if ENGAGEMENTS_CSV_PATH.exists():
            df = pd.read_csv(ENGAGEMENTS_CSV_PATH, encoding='utf-8-sig')
            # Fix BOM issues
            if 'company_name' in df.columns[0]:
                df.columns = ['company_name'] + list(df.columns[1:])
            
            # Date columns
            for col in ["start_date", "target_date", "last_interaction_date", "next_action_date", "created_date"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
            
            # Boolean columns
            for col in ['e', 's', 'g']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.lower().isin(['true', '1', 'yes', 'y'])
                    
            if 'interactions' not in df.columns:
                df['interactions'] = '[]'
    except Exception as e:
        st.error(f"Error loading data: {e}")

    if CONFIG_JSON_PATH.exists():
        try:
            config = json.load(CONFIG_JSON_PATH.open())
        except Exception as e:
            st.error(f"Error loading config: {e}")

    return df, config

def save_engagements_df(df):
    try:
        ENGAGEMENTS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        df_save = df.copy()
        for col in ['e', 's', 'g']:
            if col in df_save.columns:
                df_save[col] = df_save[col].astype(str)
        
        if 'interactions' not in df_save.columns:
            df_save['interactions'] = '[]'
        
        df_save.to_csv(ENGAGEMENTS_CSV_PATH, index=False)
        load_db.clear()
    except Exception as e:
        st.toast(f"Save failed: {e}", icon="❌")
        raise

def get_latest_view(df):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    now = pd.Timestamp.now()
    
    # Ensure datetime types
    for col in ['target_date', 'next_action_date', 'last_interaction_date', 'start_date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Calculate metrics
    df["days_to_next_action"] = (df["next_action_date"] - now).dt.days
    df["is_complete"] = df["milestone_status"].str.lower() == "complete"
    df["on_time"] = df["is_complete"] & (df["target_date"] >= now)
    df["late"] = df["is_complete"] & (df["target_date"] < now)
    df["overdue"] = (df["next_action_date"] < now) & (~df["is_complete"])
    df["urgent"] = df["days_to_next_action"] <= 3

    return df

def get_upcoming_tasks(df, days=14):
    if df.empty or 'next_action_date' not in df.columns:
        return pd.DataFrame()

    today = pd.Timestamp.now().normalize()
    mask = (
        (df['next_action_date'] >= today) &
        (df['next_action_date'] <= today + timedelta(days=days)) &
        (df['milestone_status'].str.lower() != 'complete')
    )
    return df[mask].sort_values("next_action_date")

def get_interactions_for_company(engagement_id):
    df, _ = load_db()
    if df.empty:
        return []
    
    try:
        engagement_id = int(engagement_id)
    except (ValueError, TypeError):
        return []
    
    record = df[pd.to_numeric(df['engagement_id'], errors='coerce') == engagement_id]
    if record.empty:
        return []

    interactions = record.iloc[0].get('interactions', '[]')
    try:
        return json.loads(interactions) if pd.notna(interactions) else []
    except (json.JSONDecodeError, TypeError):
        return []

def create_engagement(data):
    df, _ = load_db()
    
    # Check duplicate
    if not df.empty and 'company_name' in df.columns:
        if data['company_name'].lower() in df['company_name'].str.lower().tolist():
            return False, f"'{data['company_name']}' already exists"

    next_id = (df['engagement_id'].max() + 1) if not df.empty else 1
    
    new_record = {
        "engagement_id": next_id,
        "company_name": data.get("company_name", ""),
        "isin": data.get("isin", ""),
        "aqr_id": data.get("aqr_id", ""),
        "gics_sector": data.get("gics_sector", ""),
        "country": data.get("country", ""),
        "region": data.get("region", ""),
        "program": data.get("program", ""),
        "theme": data.get("theme", ""),
        "objective": data.get("objective", ""),
        "start_date": data.get("start_date"),
        "target_date": data.get("target_date"),
        "e": data.get("e", False),
        "s": data.get("s", False),
        "g": data.get("g", False),
        "Climate Change": "Y" if data.get("e") else "N",
        "Water": "Y" if data.get("e") else "N",
        "Forests": "Y" if data.get("e") else "N",
        "Other": "Y" if data.get("g") else "N",
        "created_date": datetime.now(),
        "created_by": data.get("created_by", "System"),
        "last_interaction_date": None,
        "next_action_date": data.get("start_date"),
        "milestone": "Initiated",
        "milestone_status": "Amber",
        "escalation_level": "None Required",
        "outcome_status": "N/A",
        "interaction_type": "",
        "interaction_summary": "",
        "outcome_date": None,
        "lessons_learned": "",
        "interactions": "[]",
    }
    
    try:
        df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
        save_engagements_df(df)
        return True, f"{data['company_name']} created (ID: {next_id})"
    except Exception as e:
        return False, str(e)

def log_interaction(data):
    df, _ = load_db()
    engagement_id = data.get("engagement_id")
    
    idx = df[pd.to_numeric(df['engagement_id'], errors='coerce') == engagement_id].index
    if idx.empty:
        return False, "Engagement not found"
    idx = idx[0]

    # Update main record
    for key in ["last_interaction_date", "next_action_date", "milestone", 
                "milestone_status", "escalation_level", "outcome_status", 
                "interaction_type", "interaction_summary"]:
        if key in data and data[key]:
            df.loc[idx, key] = data[key]
    
    # Update interaction history
    if 'interactions' not in df.columns:
        df['interactions'] = '[]'
    
    try:
        interactions = json.loads(df.loc[idx, "interactions"] or '[]')
    except:
        interactions = []

    interactions.append({
        "interaction_id": str(uuid.uuid4()),
        "interaction_type": data.get("interaction_type", ""),
        "interaction_summary": data.get("interaction_summary", ""),
        "interaction_date": pd.to_datetime(data.get("last_interaction_date")).strftime('%Y-%m-%d'),
        "outcome_status": data.get("outcome_status", ""),
        "milestone": data.get("milestone", ""),
        "milestone_status": data.get("milestone_status", ""),
        "escalation_level": data.get("escalation_level", ""),
        "logged_by": "System",
        "logged_date": datetime.now().strftime('%Y-%m-%d')
    })
    
    df.loc[idx, "interactions"] = json.dumps(interactions, indent=2)

    try:
        save_engagements_df(df)
        return True, "Interaction logged"
    except Exception as e:
        return False, str(e)

def update_milestone_status(engagement_id, status, user="System"):
    return log_interaction({
        "engagement_id": engagement_id,
        "last_interaction_date": datetime.now().date(),
        "interaction_type": "Status Change",
        "interaction_summary": f"Status → '{status}' by {user}",
        "milestone_status": status,
        "outcome_status": "Updated",
    })

@st.cache_data(ttl=600)
def get_lookup_values(field):
    _, config = load_db()
    return [str(v) for v in config.get(field, []) if v]

@st.cache_data
def get_engagement_analytics(df):
    if df.empty:
        return {"success_rates": pd.DataFrame(), "monthly_trends": pd.DataFrame()}

    # Success rates
    success = df.groupby('gics_sector').agg(
        total=('engagement_id', 'count'),
        completed=('is_complete', 'sum')
    ).reset_index()
    success['success_rate'] = (success['completed'] / success['total'] * 100).round(1)

    # Monthly trends
    trends = pd.DataFrame()
    if 'start_date' in df.columns:
        df['month'] = pd.to_datetime(df['start_date']).dt.to_period('M').dt.to_timestamp()
        trends = df.groupby('month').size().reset_index(name='new_engagements')

    return {"success_rates": success, "monthly_trends": trends}

def get_lookup_fields():
    _, config = load_db()
    return sorted(config.keys())

def get_database_info():
    df, config = load_db()
    return {"engagements": len(df), "config_fields": len(config)}

def render_metrics(metrics_data):
    if len(metrics_data) <= 3:
        cols = st.columns(len(metrics_data))
        for col, (label, value) in zip(cols, metrics_data):
            col.metric(label, value)
    else:
        for label, value in metrics_data:
            ui.metric_card(label, value)

def render_icon_header(icon, text, icon_size=30, text_size=28):
    st.markdown(
        f'<div style="margin:4px 0 12px 0;">'
        f'<span class="material-icons-outlined" style="vertical-align:middle;color:#333;font-size:{icon_size}px;">{icon}</span>'
        f'<span style="vertical-align:middle;font-size:{text_size}px;font-weight:600;margin-left:10px;">{text}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

def render_hr(margin_top=8, margin_bottom=12):
    st.markdown(f'<hr style="margin:{margin_top}px 0 {margin_bottom}px;border:1px solid #e0e0e0;">', unsafe_allow_html=True)

def create_dataframe_component(df, columns_to_display, key=None):
    if df.empty:
        st.info("No data to display")
        return
        
    df = df.copy()
    
    # Handle missing values
    for col in ['milestone', 'last_interaction_date', 'next_action_date', 'target_date']:
        if col in df.columns:
            df[col] = df[col].fillna(' ')
    
    # Add themes
    df['theme'] = df.apply(get_themes_for_row, axis=1)
    
    # Filter columns
    cols = [c for c in columns_to_display if c in df.columns]
    if not cols:
        st.warning("No valid columns")
        return
        
    df = df[cols]
    
    # Format dates
    date_fmt = Config.AGGRID_CONFIG["date_format"]
    for col in ['last_interaction_date', 'next_action_date', 'target_date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime(date_fmt).fillna(' ')
    
    # Configure columns
    config = {}
    rename = {}
    
    for col in df.columns:
        header = Config.AGGRID_COLUMN_HEADERS.get(col, col.replace('_', ' ').title())
        rename[col] = header
        
        width = "large" if col in ["company_name", "theme"] else "small" if col in ["milestone_status", "escalation_level"] else "medium"
        config[header] = st.column_config.TextColumn(header, width=width)
    
    st.dataframe(
        df.rename(columns=rename),
        use_container_width=True,
        hide_index=True,
        column_config=config,
        height=400
    )

def create_chart(data, chart_type="bar", title="", **kwargs):
    kwargs.pop('labels', None)
    colors = kwargs.get('colors', Config.CB_SAFE_PALETTE)
    
    if chart_type == "bar":
        fig = px.bar(x=data.index, y=data.values, color=data.index, color_discrete_sequence=colors) if isinstance(data, pd.Series) else px.bar(data, **kwargs)
    elif chart_type == "pie":
        fig = px.pie(values=data.values, names=data.index, color_discrete_sequence=colors) if isinstance(data, pd.Series) else px.pie(data, **kwargs)
    elif chart_type == "line":
        fig = px.line(data, **kwargs)
    elif chart_type == "scatter":
        fig = go.Figure(go.Scatter(**kwargs))
    elif chart_type == "choropleth":
        fig = px.choropleth(data, **kwargs)
    
    fig.update_layout(
        title=title,
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        margin=kwargs.get('margin', Config.CHART_DEFAULTS["margin"]),
        height=kwargs.get('height', Config.CHART_DEFAULTS["height"]),
        showlegend=kwargs.get('showlegend', Config.CHART_DEFAULTS["showlegend"]),
        xaxis_title="",
        yaxis_title=""
    )
    
    return fig

def create_esg_gauge(label, value, colour, percentage=None):
    tooltip = f"{label}<br/>Count: {value}"
    if percentage:
        tooltip += f"<br/>Share: {percentage}%"
        
    return {
        "tooltip": {"show": True, "formatter": tooltip},
        "series": [{
            "type": "gauge",
            "startAngle": 180,
            "endAngle": 0,
            "radius": "85%",
            "center": ["50%", "70%"],
            "itemStyle": {"color": colour},
            "progress": {"show": True, "width": 15},
            "axisLine": {"lineStyle": {"width": 15, "color": [[1, "#f0f2f6"]]}},
            "splitLine": {"show": False},
            "axisTick": {"show": False},
            "axisLabel": {"show": False},
            "pointer": {"show": False},
            "anchor": {"show": False},
            "min": 0,
            "max": 100,
            "data": [{"value": value, "name": label}],
            "title": {
                "show": True,
                "offsetCenter": [0, "-30%"],
                "fontSize": 14,
                "fontWeight": 600,
                "color": "#262730"
            },
            "detail": {
                "formatter": "{value}",
                "offsetCenter": [0, 5],
                "fontSize": 24,
                "fontWeight": 700,
                "color": "#262730",
            }
        }]
    }

def handle_task_date_display(task_date, today):
    try:
        if pd.notna(task_date):
            task_date = task_date.date() if hasattr(task_date, 'date') else pd.to_datetime(task_date).date()
            days = (task_date - today).days
            
            if days < 0:
                st.error(f"Overdue by {abs(days)} days")
            elif days == 0:
                st.error("Due today!")
            elif days <= 3:
                st.error(f"{days} days left")
            elif days <= 7:
                st.warning(f"{days} days left")
            else:
                st.info(f"{days} days left")
        else:
            st.info("No due date")
    except:
        st.caption("Date error")

def company_selector_widget(full_df, filtered_df):
    if full_df.empty or "company_name" not in full_df.columns:
        st.warning("No company data")
        return None

    if not filtered_df.empty and len(filtered_df) < len(full_df):
        companies = sorted(filtered_df["company_name"].unique())
        st.info(f"{len(companies)} companies match filters")
    else:
        companies = sorted(full_df["company_name"].unique())

    return st.selectbox("Select Company", companies, index=0) if companies else None

def display_interaction_history(engagement_id):
    try:
        interactions = get_interactions_for_company(engagement_id)
        if not interactions:
            st.info("No interactions recorded")
            return

        df = pd.DataFrame(interactions)
        df['interaction_date'] = pd.to_datetime(df['interaction_date'])
        df = df.sort_values('interaction_date', ascending=False)

        col1, col2 = st.columns(2)
        with col1:
            search = st.text_input("Search...")
        with col2:
            types = df['interaction_type'].dropna().unique().tolist()
            filter_types = st.multiselect("Filter by type", types, types)

        # Apply filters
        if search:
            df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]
        if filter_types:
            df = df[df['interaction_type'].isin(filter_types)]

        st.markdown("### Recent Interactions")
        if df.empty:
            st.info("No matches found")
        else:
            for _, row in df.iterrows():
                with st.container():
                    st.markdown(f"**{row.get('interaction_type', 'N/A')} - {row['interaction_date'].strftime('%Y-%m-%d')}**")
                    st.caption(f"Outcome: {row.get('outcome_status', 'N/A')} | Milestone: {row.get('milestone', 'N/A')}")
                    st.write(row.get("interaction_summary", "No summary"))
                    render_hr()
    except Exception as e:
        st.toast(f"Error: {e}", icon="❌")

def get_themes_for_row(row):
    themes = []
    theme_cols = {"Climate Change": "Climate Change", "Water": "Water", "Forests": "Forests", "Other": "Other"}
    for label, col in theme_cols.items():
        if col in row and str(row[col]).strip().upper() == 'Y':
            themes.append(label)
    return ', '.join(themes) or 'None'

def get_esg_selection(defaults=(True, True, True)):
    cols = st.columns(3)
    flags = []
    for i, (col, label, key) in enumerate(zip(cols, ["Environmental", "Social", "Governance"], ["e", "s", "g"])):
        if col.toggle(label, value=defaults[i], key=f"esg_{key}"):
            flags.append(key)
    return flags or ["e", "s", "g"]

def fix_column_names(df):
    if df.empty:
        return df
        
    targets = {'company_name', 'country'}
    normalize = lambda c: re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_')
    
    renames = {}
    for col in df.columns:
        norm = normalize(col)
        for target in targets:
            if norm == normalize(target) and col != target:
                renames[col] = target
                break
    
    return df.rename(columns=renames) if renames else df

def render_not_started_metric(count):
    st.metric("Not Started", count, delta=f"{count - 20} from last month", delta_color="inverse", border=True)

def render_geo_metrics(total, countries, most_active):
    st.metric("Total Engagements", total, border=True)
    st.metric("Countries Engaged", countries, border=True)
    st.metric("Most Active Country", most_active, border=True)