from pathlib import Path

class Config:
    ENGAGEMENTS_CSV_PATH = Path("engagements.csv")
    CONFIG_JSON_PATH = Path("configchoice.json")
    APP_TITLE = "Engagement Tracker"
    APP_ICON = "📊"
    
    COLORS = {"primary": "#3498db", "success": "#2ecc71", "warning": "#f39c12", "danger": "#e74c3c"}
    CB_SAFE_PALETTE = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854"]
    ESG_COLORS = {"Climate": "#2E8B57", "Water": "#4682B4", "Forests": "#9370DB", "Other": "#FF6B6B"}
    
    URGENT_DAYS = 3
    WARNING_DAYS = 7
    
    CHART_DEFAULTS = {"margin": {"l": 10, "r": 10, "t": 30, "b": 10}, "height": 400, "showlegend": False, 
                      "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)"}
    
    COUNTRY_ISO_MAP = {
        'USA': 'USA', 'United States': 'USA', 'UK': 'GBR', 'United Kingdom': 'GBR', 'Germany': 'DEU', 
        'France': 'FRA', 'Japan': 'JPN', 'Canada': 'CAN', 'Australia': 'AUS', 'China': 'CHN', 'India': 'IND', 
        'Brazil': 'BRA', 'Italy': 'ITA', 'Spain': 'ESP', 'Netherlands': 'NLD', 'Switzerland': 'CHE', 
        'Sweden': 'SWE', 'Norway': 'NOR', 'Denmark': 'DNK', 'Finland': 'FIN', 'Belgium': 'BEL', 
        'Austria': 'AUT', 'South Korea': 'KOR', 'Mexico': 'MEX', 'Russia': 'RUS', 'South Africa': 'ZAF', 
        'Singapore': 'SGP', 'Hong Kong': 'HKG', 'New Zealand': 'NZL', 'Ireland': 'IRL', 'Nigeria': 'NGA'
    }
    
    CHART_CONTEXTS = {
        "sector": "Distribution of engagements across different GICS sectors.",
        "outcome": "Current outcome status across all engagements showing progress stages."
    }
    
    COLUMNS = ["company_name", "country", "region", "gics_sector", "program", "theme", "outcome", "last_interaction_date"]

ENGAGEMENT_FORM_CONFIG = [
    {'name': 'company_name', 'label': 'Company Name *', 'type': 'text_input', 'required': True, 'col': 1, 'cols': 2},
    {'name': 'gics_sector', 'label': 'GICS Sector *', 'type': 'selectbox', 'options': 'gics_sector', 'required': True, 'col': 2},
    {'name': 'isin', 'label': 'ISIN', 'type': 'text_input', 'required': False, 'col': 1, 'cols': 3},
    {'name': 'aqr_id', 'label': 'AQR ID', 'type': 'text_input', 'required': False, 'col': 2},
    {'name': 'program', 'label': 'Program *', 'type': 'selectbox', 'options': 'program', 'required': True, 'col': 3},
    {'name': 'country', 'label': 'Country *', 'type': 'selectbox', 'options': 'country', 'required': True, 'col': 1, 'cols': 3},
    {'name': 'region', 'label': 'Region *', 'type': 'selectbox', 'options': 'region', 'required': True, 'col': 2},
    {'name': 'theme', 'label': 'Theme', 'type': 'selectbox', 'options': 'theme', 'required': False, 'col': 3},
    {'name': 'objective', 'label': 'Objective', 'type': 'selectbox', 'options': 'objective', 'required': False, 'col': 1, 'cols': 1},
]

PAGES_CONFIG = {"Dashboard": {"icon": "speedometer2"}, "Engagement Log": {"icon": "folder-plus"}, "Calendar": {"icon": "list-check"}}

NAV_STYLES = {
    "container": {"margin": "0px !important", "padding": "0!important", "align-items": "stretch", "background-color": "#fafafa"},
    "icon": {"color": "black", "font-size": "14px"},
    "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
    "nav-link-selected": {"background-color": Config.COLORS["primary"], "font-size": "14px", "font-weight": "bold", "color": "white"},
}