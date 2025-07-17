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
    
    COLUMNS = ["company_name", "country", "region", "gics_sector", "program", "theme", "outcome", "last_interaction_date"]

PAGES_CONFIG = {"Dashboard": {"icon": "speedometer2"}, "Engagement Log": {"icon": "folder-plus"}, "Calendar": {"icon": "list-check"}}

NAV_STYLES = {
    "container": {"margin": "0px !important", "padding": "0!important", "align-items": "stretch", "background-color": "#fafafa"},
    "icon": {"color": "black", "font-size": "14px"},
    "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
    "nav-link-selected": {"background-color": Config.COLORS["primary"], "font-size": "14px", "font-weight": "bold", "color": "white"},
}