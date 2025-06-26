from __future__ import annotations
import pandas as pd
import json
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import uuid
import re
import streamlit_shadcn_ui as ui

from config import Config

ENGAGEMENTS_CSV_PATH = Path("engagements.csv")
CONFIG_JSON_PATH = Path("configchoice.json")

class DataValidator:
    def __init__(self, choices: Dict):
        """Initializes the validator with pre-loaded choices."""
        self.choices = choices
        self.validation_rules = self._setup_validation_rules()

    def _setup_validation_rules(self) -> Dict[str, Dict]:
        """Sets up validation rules based on the provided choices."""
        rules = {}
        required_fields = [
            'gics_sector', 'region', 'program', 'country'
        ]
        for field, choice_list in self.choices.items():
            rules[field] = {
                'required': field in required_fields,
                'type': 'choice',
                'choices': choice_list
            }
        return rules

    def validate_field(self, field_name: str, value: any) -> Tuple[bool, Optional[str]]:
        """Validates a single field against its rule."""
        if field_name not in self.validation_rules:
            return True, None

        rule = self.validation_rules[field_name]
        if rule['required'] and (value is None or str(value).strip() == ''):
            return False, f"{field_name.replace('_', ' ').title()} is required."
        
        if not rule['required'] and (value is None or str(value).strip() == ''):
            return True, None

        if rule['type'] == 'choice' and value and value not in rule['choices']:
            return False, f"Invalid value '{value}' for {field_name}."
        
        return True, None
    
    def validate_record(self, record: Dict) -> Dict[str, List[str]]:
        """Validates a full data record."""
        errors = {}
        
        # Basic required fields
        if not record.get('company_name', '').strip():
            errors.setdefault('company_name', []).append("Company name is required.")
        
        # ESG flag validation - at least one must be true
        esg_flags = [record.get('e', False), record.get('s', False), record.get('g', False)]
        if not any(esg_flags):
            errors.setdefault('esg_flags', []).append("At least one ESG flag (E, S, or G) must be selected.")
        
        # Validate choice fields
        for field_name, value in record.items():
            if field_name in self.validation_rules:
                is_valid, error_msg = self.validate_field(field_name, value)
                if not is_valid:
                    errors.setdefault(field_name, []).append(error_msg)
        
        return errors

# --- DATA LOADING AND SAVING ---

@st.cache_data(ttl=300)  # Reduced TTL for more frequent updates
def load_db() -> tuple[pd.DataFrame, dict]:
    """Loads the engagements CSV and config JSON into memory."""
    df = pd.DataFrame()
    config = {}
    
    try:
        if ENGAGEMENTS_CSV_PATH.exists():
            df = pd.read_csv(ENGAGEMENTS_CSV_PATH, encoding='utf-8-sig')
            # Quick fix: Rename first column if it contains 'company_name' (BOM or weird chars)
            first_col = df.columns[0]
            if 'company_name' in first_col and first_col != 'company_name':
                df = df.rename(columns={first_col: 'company_name'})
            
            # Ensure proper data types
            date_cols = ["start_date", "target_date", "last_interaction_date", "next_action_date", "created_date"]
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
            
            # Ensure boolean columns are properly handled
            bool_cols = ['e', 's', 'g']
            for col in bool_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.lower().isin(['true', '1', 'yes', 'y'])
                    
            # Ensure interactions column exists
            if 'interactions' not in df.columns:
                df['interactions'] = '[]'
        else:
            st.warning(f"Engagements file '{ENGAGEMENTS_CSV_PATH}' not found. Starting with empty dataset.")
    except Exception as e:
        st.error(f"Error loading engagements CSV: {e}")

    try:
        if CONFIG_JSON_PATH.exists():
            with open(CONFIG_JSON_PATH, 'r') as f:
                config = json.load(f)
        else:
            st.warning(f"Config file '{CONFIG_JSON_PATH}' not found. Using default empty config.")
    except Exception as e:
        st.error(f"Error loading config JSON: {e}")

    return df, config

def save_engagements_df(df: pd.DataFrame):
    """Saves the engagements DataFrame back to CSV and clears relevant caches."""
    try:
        # Ensure directory exists
        ENGAGEMENTS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert boolean columns to string for CSV storage
        df_to_save = df.copy()
        bool_cols = ['e', 's', 'g']
        for col in bool_cols:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].astype(str)
        
        # Ensure interactions column exists
        if 'interactions' not in df_to_save.columns:
            df_to_save['interactions'] = '[]'
        
        df_to_save.to_csv(ENGAGEMENTS_CSV_PATH, index=False)
        
        # Clear cache to ensure fresh data is loaded
        load_db.clear()
        
    except Exception as e:
        st.toast(f"❌ Failed to save engagements data: {e}", icon="❌")
        raise e

# --- DATA RETRIEVAL AND COMPUTATION ---

def get_latest_view(df: pd.DataFrame) -> pd.DataFrame:
    """Computes dynamic fields on a given DataFrame. Not cached."""
    if df.empty:
        return pd.DataFrame()

    df_copy = df.copy()
    now = pd.to_datetime(datetime.now())

    # Ensure date columns are datetime objects for calculations
    date_cols = ['target_date', 'next_action_date', 'last_interaction_date', 'start_date']
    for col in date_cols:
        if col in df_copy.columns:
            df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')

    # Calculate dynamic fields
    df_copy["days_to_next_action"] = (df_copy["next_action_date"] - now).dt.days
    df_copy["is_complete"] = df_copy["milestone_status"].str.lower() == "complete"
    df_copy["on_time"] = df_copy["is_complete"] & (df_copy["target_date"] >= now)
    df_copy["late"] = df_copy["is_complete"] & (df_copy["target_date"] < now)
    df_copy["overdue"] = (df_copy["next_action_date"] < now) & (~df_copy["is_complete"])
    df_copy["urgent"] = df_copy["days_to_next_action"] <= 3

    return df_copy

def get_upcoming_tasks(df: pd.DataFrame, days: int = 14) -> pd.DataFrame:
    """Get tasks from a given dataframe due within the specified number of days."""
    if df.empty or 'next_action_date' not in df.columns:
        return pd.DataFrame()

    today = pd.to_datetime(datetime.now().date())
    future_date = today + timedelta(days=days)

    upcoming_mask = (
        (df['next_action_date'] >= today) &
        (df['next_action_date'] <= future_date) &
        (df['milestone_status'].str.lower() != 'complete')
    )
    return df[upcoming_mask].sort_values(by="next_action_date")

def get_interactions_for_company(engagement_id: int) -> List[Dict]:
    """Retrieves the interaction history for a specific engagement."""
    df, _ = load_db()
    if df.empty or 'interactions' not in df.columns:
        return []
    
    # Convert engagement_id to numeric for comparison
    try:
        engagement_id = int(engagement_id)
    except (ValueError, TypeError):
        return []
    
    record = df[pd.to_numeric(df['engagement_id'], errors='coerce') == engagement_id]
    if record.empty:
        return []

    interactions_json = record.iloc[0].get('interactions', '[]')
    try:
        # Handle cases where the JSON might be NaN or other non-string types
        if pd.isna(interactions_json) or interactions_json in ['', 'nan']:
            return []
        return json.loads(interactions_json)
    except (json.JSONDecodeError, TypeError):
        return []

# --- DATA MODIFICATION FUNCTIONS ---

def create_engagement(data: Dict) -> Tuple[bool, str]:
    """Creates a new engagement with all fields."""
    try:
        # Load current data
        df, _ = load_db()
        
        # Check for duplicate company (case-insensitive)
        if not df.empty and 'company_name' in df.columns:
            existing_companies = df['company_name'].str.lower().tolist()
            if data['company_name'].lower() in existing_companies:
                return False, f"Engagement with '{data['company_name']}' already exists."

        # Generate next ID
        next_id = (df['engagement_id'].max() + 1) if not df.empty and 'engagement_id' in df.columns else 1
        
        # Create new engagement record with all required fields including interactions
        new_engagement = {
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
            "Climate Change": "Y" if data.get("e", False) else "N",
            "Water": "Y" if data.get("e", False) else "N",
            "Forests": "Y" if data.get("e", False) else "N",
            "Other": "Y" if data.get("g", False) else "N",
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
            "interactions": "[]",  # FIXED: Always include interactions column
        }
        
        # Create new DataFrame and save
        new_df = pd.concat([df, pd.DataFrame([new_engagement])], ignore_index=True)
        save_engagements_df(new_df)
        
        return True, f"Engagement for {data['company_name']} created successfully (ID: {next_id})."
        
    except Exception as e:
        return False, f"Failed to create engagement: {str(e)}"

def log_interaction(data: Dict) -> Tuple[bool, str]:
    """Logs a detailed interaction for an engagement."""
    try:
        df, _ = load_db()
        engagement_id = data.get("engagement_id")
        
        # Find the engagement record
        idx = df[pd.to_numeric(df['engagement_id'], errors='coerce') == engagement_id].index
        if idx.empty:
            return False, "Engagement ID not found."
        idx = idx[0]

        # Update the main record with latest interaction info
        update_fields = [
            "last_interaction_date", "next_action_date", "milestone", 
            "milestone_status", "escalation_level", "outcome_status", "interaction_type"
        ]
        for key in update_fields:
            if key in data and data[key] is not None and data[key] != "":
                df.loc[idx, key] = data[key]
        
        # Update interaction summary
        if "interaction_summary" in data:
            df.loc[idx, "interaction_summary"] = data["interaction_summary"]
        
        # FIXED: Ensure interactions column exists before accessing
        if 'interactions' not in df.columns:
            df['interactions'] = '[]'
        
        # Append to interaction history
        try:
            current_interactions = df.loc[idx, "interactions"]
            if pd.isna(current_interactions) or current_interactions in ['', '[]']:
                interactions_list = []
            else:
                interactions_list = json.loads(current_interactions)
        except (json.JSONDecodeError, TypeError):
            interactions_list = []

        # Create new interaction record
        new_interaction = {
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
        }
        
        interactions_list.append(new_interaction)
        df.loc[idx, "interactions"] = json.dumps(interactions_list, indent=2)

        save_engagements_df(df)
        return True, "Interaction logged successfully."
        
    except Exception as e:
        return False, f"Failed to log interaction: {str(e)}"

def update_milestone_status(engagement_id: int, status: str, user: str = "System") -> Tuple[bool, str]:
    """Updates the milestone status, logging it as a formal interaction."""
    return log_interaction({
        "engagement_id": engagement_id,
        "last_interaction_date": datetime.now().date(),
        "interaction_type": "Status Change",
        "interaction_summary": f"Status changed to '{status}' by {user}.",
        "milestone_status": status,
        "outcome_status": "Updated",
    })

# --- LOOKUP AND ANALYTICS FUNCTIONS ---

@st.cache_data(ttl=600)
def get_lookup_values(field: str) -> List[str]:
    """Gets lookup values for a specific field from the config JSON."""
    _, config_data = load_db()
    values = config_data.get(field, [])
    return [str(v) for v in values if v]  # Ensure strings and filter out empty values

@st.cache_data
def get_engagement_analytics(df: pd.DataFrame) -> Dict:
    """Generates a full suite of analytics from a given DataFrame."""
    if df.empty:
        return {
            "success_rates": pd.DataFrame(), 
            "monthly_trends": pd.DataFrame()
        }

    # Success rates by sector
    success_rates = df.groupby('gics_sector').agg(
        total=('engagement_id', 'count'),
        completed=('is_complete', 'sum')
    ).reset_index()
    success_rates['success_rate'] = (success_rates['completed'] / success_rates['total'] * 100).round(1)

    # Monthly trends
    trends_df = df.copy()
    if 'start_date' in trends_df.columns:
        trends_df['month'] = pd.to_datetime(trends_df['start_date']).dt.to_period('M').dt.to_timestamp()
        monthly_trends = trends_df.groupby('month').agg(
            new_engagements=('engagement_id', 'count')
        ).reset_index()
    else:
        monthly_trends = pd.DataFrame()

    return {
        "success_rates": success_rates, 
        "monthly_trends": monthly_trends
    }

def get_lookup_fields() -> List[str]:
    _, config_data = load_db()
    return sorted(list(config_data.keys()))

def get_database_info() -> Dict:
    df, config = load_db()
    return {"engagements": len(df), "config_fields": len(config)}

# --- UI HELPER FUNCTIONS ---

def render_metrics(metrics_data):
    """Renders metrics using enhanced styling with proper spacing."""
    if len(metrics_data) <= 3:
        cols = st.columns(len(metrics_data))
        for col, (label, value) in zip(cols, metrics_data):
            with col:
                st.metric(label, value)
    else:
        # For more than 3 metrics, use vertical stacking
        for label, value in metrics_data:
            ui.metric_card(label, value)

def render_icon_header(icon, text, icon_size=30, text_size=28):
    """Renders a header with material icon and text."""
    return st.markdown(
        f'<div style="margin-top:8px; margin-bottom:8px;">'
        f'<span class="material-icons-outlined" style="vertical-align:middle;color:#333333;font-size:{icon_size}px;font-weight:100;">{icon}</span>'
        f'<span style="vertical-align:middle;font-size:{text_size}px;font-weight:600;margin-left:10px;">{text}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

def render_hr(margin_top=8, margin_bottom=12):
    """Renders a horizontal rule with consistent styling."""
    return st.markdown(
        f'<hr style="margin-top:{margin_top}px;margin-bottom:{margin_bottom}px;border:1px solid #e0e0e0;">',
        unsafe_allow_html=True
    )

def create_dataframe_component(df, columns_to_display, key=None):
    """Creates a native Streamlit dataframe with enhanced styling and proper column headers."""
    if df.empty:
        st.info("No data to display.")
        return
        
    # Create display DataFrame
    display_df = df.copy()
    
    # Handle missing values
    for col in ['milestone', 'last_interaction_date', 'next_action_date', 'target_date']:
        if col in display_df.columns:
            display_df[col] = display_df[col].fillna(' ')
    
    # Add theme column
    display_df['theme'] = display_df.apply(get_themes_for_row, axis=1)
    
    # Filter to desired columns that exist
    display_columns = [col for col in columns_to_display if col in display_df.columns]
    if not display_columns:
        st.warning("No valid columns to display.")
        return
        
    display_df = display_df[display_columns]
    
    # Format dates properly
    for date_col in ['last_interaction_date', 'next_action_date', 'target_date']:
        if date_col in display_df.columns:
            display_df[date_col] = pd.to_datetime(
                display_df[date_col], errors='coerce'
            ).dt.strftime(Config.AGGRID_CONFIG["date_format"]).fillna(' ')
    
    # FIXED: Apply column renaming properly
    column_config = {}
    renamed_columns = {}
    
    for col in display_df.columns:
        # Get the proper header name
        header_name = Config.AGGRID_COLUMN_HEADERS.get(col, col.replace('_', ' ').title())
        renamed_columns[col] = header_name
        
        # Configure column width
        if col in ["company_name", "theme"]:
            column_config[header_name] = st.column_config.TextColumn(
                header_name,
                width="large",
                help=f"Details for {header_name.lower()}"
            )
        elif col in ["milestone_status", "escalation_level"]:
            column_config[header_name] = st.column_config.TextColumn(
                header_name,
                width="small"
            )
        else:
            column_config[header_name] = st.column_config.TextColumn(
                header_name,
                width="medium"
            )
    
    # Rename the columns
    display_df_renamed = display_df.rename(columns=renamed_columns)
    
    # Display with enhanced configuration
    st.dataframe(
        display_df_renamed,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        height=400
    )

def create_chart(data, chart_type="bar", title="", **kwargs):
    """Creates various types of charts with consistent styling."""
    # Remove labels parameter if passed
    kwargs.pop('labels', None)
    
    if chart_type == "bar":
        if isinstance(data, pd.Series):
            fig = px.bar(x=data.index, y=data.values, 
                        color=data.index, 
                        color_discrete_sequence=kwargs.get('colors', Config.CB_SAFE_PALETTE))
        else:
            fig = px.bar(data, **kwargs)
    elif chart_type == "pie":
        if isinstance(data, pd.Series):
            fig = px.pie(values=data.values, names=data.index, 
                        color_discrete_sequence=kwargs.get('colors', Config.CB_SAFE_PALETTE))
        else:
            fig = px.pie(data, **kwargs)
    elif chart_type == "line":
        fig = px.line(data, **kwargs)
    elif chart_type == "scatter":
        fig = go.Figure()
        fig.add_trace(go.Scatter(**kwargs))
    elif chart_type == "choropleth":
        fig = px.choropleth(data, **kwargs)
    
    fig.update_layout(
        title=title,
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        margin=kwargs.get('margin', Config.CHART_DEFAULTS["margin"]),
        height=kwargs.get('height', Config.CHART_DEFAULTS["height"]),
        showlegend=kwargs.get('showlegend', Config.CHART_DEFAULTS["showlegend"])
    )
    
    fig.update_xaxes(title="")
    fig.update_yaxes(title="")
        
    return fig

def create_esg_gauge(label, value, colour, percentage=None):
    """Creates an ESG gauge chart configuration with absolute numbers and a tooltip."""
    tooltip_text = f"{label}<br/>Count: {value}"
    if percentage is not None:
        tooltip_text += f"<br/>Share: {percentage}%"
    return {
        "tooltip": {
            "show": True,
            "formatter": tooltip_text
        },
        "series": [
            {
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "radius": "100%",
                "center": ["50%", "75%"],
                "itemStyle": {"color": colour},
                "progress": {"show": True, "width": 18},
                "axisLine": {"lineStyle": {"width": 18, "color": [[1, "#f0f2f6"]]}},
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
                    "offsetCenter": [0, "-40%"],
                    "fontSize": 16,
                    "fontWeight": 600,
                    "color": "#262730"
                },
                "detail": {
                    "formatter": "{value}",
                    "offsetCenter": [0, 0],
                    "fontSize": 28,
                    "fontWeight": 700,
                    "color": "#262730",
                },
            }
        ]
    }

def handle_task_date_display(task_date, today):
    """Displays task date with appropriate styling based on urgency."""
    try:
        if pd.notna(task_date):
            if hasattr(task_date, 'date'):
                task_date = task_date.date()
            else:
                task_date = pd.to_datetime(task_date).date()

            days_left = (task_date - today).days
            if days_left < 0:
                st.error(f"Overdue by {abs(days_left)} days")
            elif days_left == 0:
                st.error("Due today!")
            elif days_left <= 3:
                st.error(f"{days_left} days left")
            elif days_left <= 7:
                st.warning(f"{days_left} days left")
            else:
                st.info(f"{days_left} days left")
        else:
            st.info("No due date set")
    except Exception:
        st.caption("Date error")

def company_selector_widget(full_df, filtered_df):
    """Renders a company selection dropdown based on current filters."""
    if full_df.empty or "company_name" not in full_df.columns:
        st.warning("No company data available.")
        return None

    if not filtered_df.empty and len(filtered_df) < len(full_df):
        available_companies = sorted(filtered_df["company_name"].unique())
        st.info(f"Showing {len(available_companies)} companies based on current filters. Clear filters to see all companies.")
    else:
        available_companies = sorted(full_df["company_name"].unique())

    if not available_companies:
        st.warning("No companies available.")
        return None

    default_index = 0  # Default to first company
    return st.selectbox("Select Company", available_companies, index=default_index)

def display_interaction_history(engagement_id):
    """Fetches and displays the interaction history for an engagement, with search and filter."""
    try:
        interactions = get_interactions_for_company(engagement_id)

        if not interactions:
            st.info("No interactions recorded for this company.")
            return

        interactions_df = pd.DataFrame(interactions)
        interactions_df['interaction_date'] = pd.to_datetime(interactions_df['interaction_date'])
        interactions_df = interactions_df.sort_values(by='interaction_date', ascending=False)

        # --- Search and Filter UI ---
        col1, col2 = st.columns(2)
        with col1:
            search_query = st.text_input("Search interactions...")
        with col2:
            type_options = interactions_df['interaction_type'].dropna().unique().tolist()
            type_filter = st.multiselect("Filter by type...", options=type_options, default=type_options)

        filtered_df = interactions_df.copy()
        if search_query:
            mask = filtered_df.apply(lambda row: search_query.lower() in str(row.values).lower(), axis=1)
            filtered_df = filtered_df[mask]
        if type_filter:
            filtered_df = filtered_df[filtered_df['interaction_type'].isin(type_filter)]

        st.markdown("### Recent Interactions")
        if filtered_df.empty:
            st.info("No interactions match your search/filter.")
        else:
            for _, interaction in filtered_df.iterrows():
                with st.container():
                    st.markdown(f"**{interaction.get('interaction_type', 'N/A')} on {interaction['interaction_date'].strftime('%Y-%m-%d')}**")
                    st.caption(f"Outcome: {interaction.get('outcome_status', 'N/A')} | Milestone: {interaction.get('milestone', 'N/A')}")
                    st.write(interaction.get("interaction_summary", "No summary available."))
                    render_hr()
    except Exception as e:
        st.toast(f"❌ Error loading interaction data: {e}", icon="❌")

def get_themes_for_row(row):
    """Returns a comma-separated string of themes for which the row has a 'Y' in the corresponding columns."""
    theme_map = [
        ("Climate Change", "Climate Change"),
        ("Water", "Water"),
        ("Forests", "Forests"),
        ("Other", "Other")
    ]
    themes = []
    for label, col in theme_map:
        if col in row and str(row[col]).strip().upper() == 'Y':
            themes.append(label)
    return ', '.join(themes) if themes else 'None'

def get_esg_selection(default_values=(True, True, True)):
    """Renders ESG toggle selection and returns selected flags."""
    col_e, col_s, col_g = st.columns(3)
    with col_e:
        env = st.toggle("Environmental", value=default_values[0], key="esg_e")
    with col_s:
        soc = st.toggle("Social", value=default_values[1], key="esg_s")
    with col_g:
        gov = st.toggle("Governance", value=default_values[2], key="esg_g")
    
    selected = []
    if env:
        selected.append("e")
    if soc:
        selected.append("s")
    if gov:
        selected.append("g")
    
    return selected if selected else ["e", "s", "g"]  # Default to all if none selected

def fix_column_names(df):
    """Renames any column similar to 'company_name' or 'country' to the correct name to fix Excel encoding issues."""
    if df.empty:
        return df
        
    targets = ['company_name', 'country']
    def normalize(col):
        # Lowercase, remove non-alphanumeric, replace multiple underscores/spaces
        return re.sub(r'[^a-z0-9]+', '_', col.lower()).strip('_')
    
    norm_targets = {normalize(t): t for t in targets}
    rename_dict = {}
    
    for col in df.columns:
        norm_col = normalize(col)
        if norm_col in norm_targets and col != norm_targets[norm_col]:
            rename_dict[col] = norm_targets[norm_col]
    
    if rename_dict:
        df = df.rename(columns=rename_dict)
    
    return df

def render_not_started_metric(not_started_count: int):
    """Renders a Streamlit metric card for 'Not Started' with a border and green delta for a decrease from 20 last month."""
    st.metric(
        label="Not Started",
        value=not_started_count,
        delta=f"{not_started_count - 20} from last month",
        delta_color="inverse",  # Green for negative change
        border=True
    )

def render_geo_metrics(total_engagements: int, countries_engaged: int, most_active_country: str):
    """Displays three Streamlit metric cards for geo stats vertically down the page, with borders."""
    st.metric("Total Engagements", total_engagements, border=True)
    st.metric("Countries Engaged", countries_engaged, border=True)
    st.metric("Most Active Country", most_active_country, border=True)