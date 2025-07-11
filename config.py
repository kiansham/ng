from pathlib import Path

# File paths
ENGAGEMENTS_CSV_PATH = Path("engagements.csv")
CONFIG_JSON_PATH = Path("configchoice.json")

class Config:
    # Application settings
    APP_TITLE = "Engagement Tracking Platform"
    APP_ICON = "📊"
    
    # Color palette
    COLORS = {
        "primary": "#3498db", "success": "#2ecc71",
        "warning": "#f39c12", "danger": "#e74c3c",
    }
    CB_SAFE_PALETTE = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854"]
    
    # ESG Theme Colors
    ESG_COLORS = {
        "Climate Change": "#2E8B57",
        "Water": "#4682B4",
        "Forests": "#9370DB",
        "Other": "#FF6B6B"
    }
    
    URGENT_DAYS = 3
    WARNING_DAYS = 7
    
    # Default chart configurations
    CHART_DEFAULTS = {
        "margin": {"l": 10, "r": 10, "t": 30, "b": 10},
        "height": 400,
        "showlegend": False,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)"
    }
    
    # Country ISO mapping
    COUNTRY_ISO_MAP = {
        'USA': 'USA', 'United States': 'USA',
        'UK': 'GBR', 'United Kingdom': 'GBR',
        'Germany': 'DEU', 'France': 'FRA',
        'Japan': 'JPN', 'Canada': 'CAN',
        'Australia': 'AUS', 'China': 'CHN',
        'India': 'IND', 'Brazil': 'BRA',
        'Italy': 'ITA', 'Spain': 'ESP',
        'Netherlands': 'NLD', 'Switzerland': 'CHE',
        'Sweden': 'SWE', 'Norway': 'NOR',
        'Denmark': 'DNK', 'Finland': 'FIN',
        'Belgium': 'BEL', 'Austria': 'AUT',
        'South Korea': 'KOR', 'Mexico': 'MEX',
        'Russia': 'RUS', 'South Africa': 'ZAF',
        'Singapore': 'SGP', 'Hong Kong': 'HKG',
        'New Zealand': 'NZL', 'Ireland': 'IRL'
    }
    
    # Chart context descriptions
    CHART_CONTEXTS = {
        "sector": "Distribution of engagements across different GICS sectors.",
        "milestone": "Current milestone stages across all live engagements through their lifecycle."
    }
    
    # Icon mappings for headers
    HEADER_ICONS = {
        "metrics": "query_stats",
        "esg": "center_focus_strong", 
        "table": "table_chart",
        "sector": "domain",
        "region": "public",
        "geo": "location_on",
        "milestone": "emoji_events",
        "app_title": "travel_explore",
        "filter": "tune",
        "insights": "lightbulb",
        "pie_chart": "pie_chart",
        "eco": "eco",
        "business": "business",
        "apartment": "apartment",
        "camera_alt": "camera_alt",
        "history": "history",
        "bookmark_manager": "bookmark_manager",
        "add_business": "add_business",
        "edit_note": "edit_note",
        "description": "description",
        "flag": "flag",
        "schedule": "schedule",
        "calendar_month": "calendar_month",
        "timeline": "timeline"
    }
    

    
    # Column display configuration
    AGGRID_COLUMN_HEADERS = {
        'gics_sector': 'Sector',
        'aqr_id': 'AQR ID',
        'last_interaction_date': 'Last Interaction',
        'next_action_date': 'Next Action',
        'target_date': 'Completion Date'
    }
    

    
    AGGRID_COLUMNS = [
        "company_name", "aqr_id", "country", "region", "gics_sector", "program",
        "theme", "milestone", "last_interaction_date", "next_action_date", "target_date"
    ]

PAGES_CONFIG = {
    "Dashboard": {"icon": "speedometer2", "function": "dashboard"},
    "Engagement Log": {"icon": "folder-plus", "function": "engagement_management"},
    "Calendar": {"icon": "list-check", "function": "task_management"},
}

ENHANCED_CSS = """
<style>
    .stApp { background-color: #f8f9fa; }
    .alert-urgent { 
        background-color: #ffe6e6; border-left: 4px solid #e74c3c; 
        padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; 
    }
    .alert-warning { 
        background-color: #fff3cd; border-left: 4px solid #f39c12; 
        padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; 
    }
    .validation-error { 
        background-color: #fee; border-left: 4px solid #c00; 
        padding: 0.5rem; border-radius: 0.25rem; margin: 0.5rem 0; 
    }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e9ecef; padding: 16px;
        border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); transform: translateY(-1px);
    }
    .chart-title {
        font-size: 1.2rem; font-weight: 600; color: #262730; margin-bottom: 1rem;
        padding-bottom: 0.5rem; border-bottom: 2px solid #f0f2f6;
    }
    .sidebar-section {
        background-color: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 10px;
    }
    .streamlit-expander { border: 1px solid #e0e0e0; border-radius: 8px; }
</style>
"""

NAV_STYLES = {
    "container": {"padding": "2px 0 2px 0!important", "background-color": "#f0f2f6", "margin-top": "10px", "margin-bottom": "6px"},
    "icon": {"font-size": "1.1rem"},
    "nav-link": {
        "font-size": "14px", "font-weight": "600", "text-align": "left", "margin":"5px",
        "--hover-color": "#e8f4fd"
    },
    "nav-link-selected": {"background-color": Config.COLORS["primary"]},
}

CHART_CONFIGS = {
    "bar": {
        "height": 400, "yaxis": {"tickformat": "d"},
        "margin": {"l": 50, "r": 20, "t": 60, "b": 50}, "showlegend": False
    },
    "status": {
        "height": 140, "barmode": "stack", "margin": {"l": 10, "r": 10, "t": 40, "b": 10},
        "showlegend": True, "xaxis": {"tickformat": "d"}
    },
    "geographic": {"height": 700, "margin": {"l": 0, "r": 0, "t": 0, "b": 0}},
}

CALENDAR_OPTIONS = {
    "height": "600px", "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today", "center": "title", "right": "dayGridMonth,multiMonthYear"
    }
}

CALENDAR_STYLES = f"""
    .fc-button {{
        background-color: {Config.COLORS['primary']}; color: white !important; border: none !important;
        border-radius: 0.4rem !important; padding: 0.25rem 0.75rem !important; font-weight: 500 !important;
        font-size: 0.9rem !important; transition: background-color 0.3s ease; text-transform: capitalize;
    }}
    .fc-button:hover {{ background-color: #2980b9 !important; }}
    .fc-button-primary:disabled {{ background-color: #a9a9a9 !important; color: #e0e0e0 !important; }}
    .fc-button-active {{ background-color: #2980b9 !important; }}
    .fc-toolbar-title {{ font-size: 1.5rem; }}
    .event-urgent {{ background-color: {Config.COLORS['danger']} !important; border-color: #c0392b !important; }}
    .event-warning {{ background-color: {Config.COLORS['warning']} !important; border-color: #d68910 !important; }}
    .event-upcoming {{ background-color: {Config.COLORS['primary']} !important; border-color: #2980b9 !important; }}
"""