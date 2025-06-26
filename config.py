from pathlib import Path

class Config:
    # Application settings
    APP_TITLE = "Engagement Tracking Platform"
    APP_ICON = "📊"
    APP_ICON_NAME = "travel_explore"  # Material icon for landing page
    
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
    
    # Task urgency thresholds (days)
    URGENT_DAYS = 3
    WARNING_DAYS = 7
    UPCOMING_DAYS = 14
    
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
        "region": "Geographic spread of engagements by region.",
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
        "filter": "tune"
    }
    
    # Column display configuration
    AGGRID_COLUMN_HEADERS = {
        'gics_sector': 'Sector',
        'aqr_id': 'AQR ID',
        'last_interaction_date': 'Last Interaction',
        'next_action_date': 'Next Action',
        'target_date': 'Completion Date'
    }
    
    # AG Grid column configuration for dashboard table
    AGGRID_COLUMNS = [
        "company_name",
        "aqr_id",
        "country",
        "region",
        "gics_sector",
        "program",
        "theme",
        "milestone",
        "last_interaction_date",
        "next_action_date",
        "target_date"
    ]

# Page and navigation configuration - Landing page is now first
PAGES_CONFIG = {
    "Dashboard": {"icon": "speedometer2", "function": "dashboard"},
    "Engagement Operations": {"icon": "folder-plus", "function": "engagement_management"},
    "Analytics": {"icon": "graph-up-arrow", "function": "analytics"},
    "Company Profiles": {"icon": "building", "function": "company_deep_dive"},
    "Task Management": {"icon": "list-check", "function": "task_management"},
}

# CSS styles
CSS_STYLES = """
<style>
    .stApp {
        background-color: #f8f9fa;
    }
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
</style>
"""

# Enhanced CSS styles
ENHANCED_CSS = CSS_STYLES + """
<style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    
    .chart-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #262730;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f0f2f6;
    }
    
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    .streamlit-expander {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
</style>
"""

# Landing page specific CSS
LANDING_CSS = """
<style>
    /* Force override ALL purple backgrounds */
    .stApp, .main, .block-container, .css-1d391kg, .css-18e3th9, .css-1lcbmhc {
        background-color: #f8f9fa !important;
        background-image: none !important;
        background: #f8f9fa !important;
    }
    
    /* Target ONLY the landing page button specifically */
    .landing-container button, .landing-container .stButton > button {
        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 16px !important;
        padding: 24px 60px !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        box-shadow: 0 12px 40px rgba(52, 152, 219, 0.4) !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        min-width: 500px !important;
        height: 80px !important;
        transition: all 0.3s ease !important;
    }
    
    .landing-container button:hover, .landing-container .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 16px 50px rgba(52, 152, 219, 0.6) !important;
        background: linear-gradient(135deg, #2980b9 0%, #3498db 100%) !important;
    }
    
    /* Draft banner styles */
    .draft-banner {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 40px;
        background: linear-gradient(90deg, #fff3cd 0%, #ffeaa7 50%, #fff3cd 100%);
        border: 2px solid #f39c12;
        border-left: none;
        border-right: none;
        z-index: 1000;
        overflow: hidden;
        display: flex;
        align-items: center;
    }
    
    .moving-text {
        white-space: nowrap;
        font-weight: 600;
        font-size: 14px;
        color: #856404;
        animation: scroll-left 20s linear infinite;
        padding: 0 20px;
    }
    
    @keyframes scroll-left {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    
    /* Landing page container */
    .landing-container {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 60px 20px 20px 20px;
        background-color: #f8f9fa !important;
    }
    
    /* Landing header */
    .landing-header {
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 80px;
        animation: fadeInUp 1s ease-out;
    }
    
    /* FORCE icon color */
    .landing-icon, .material-icons-outlined {
        font-size: 72px !important;
        color: #262730 !important;
        margin-right: 24px !important;
    }
    
    .landing-title {
        font-size: 4rem !important;
        font-weight: 600 !important;
        color: #262730 !important;
        margin: 0 !important;
        letter-spacing: -2px !important;
    }
    
    /* Feature columns */
    .landing-columns {
        width: 100%;
        max-width: 1200px;
        margin: 0 auto 60px auto;
        padding: 0 10%;
    }
    
    .feature-card {
        border-radius: 20px;
        padding: 40px 32px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        height: 280px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin: 0 16px;
        animation: fadeInUp 1s ease-out 0.3s both;
        border: 2px solid rgba(255,255,255,0.3);
    }
    
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 16px 48px rgba(0,0,0,0.15);
    }
    
    .feature-card.analytics {
        background: linear-gradient(135deg, #2E8B57 0%, #3DA66B 100%) !important;
    }
    
    .feature-card.global {
        background: linear-gradient(135deg, #4682B4 0%, #5A96C8 100%) !important;
    }
    
    .feature-card.workflow {
        background: linear-gradient(135deg, #9370DB 0%, #A584E0 100%) !important;
    }
    
    .feature-icon {
        font-size: 48px !important;
        margin-bottom: 24px !important;
        color: white !important;
    }
    
    .feature-card h3 {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        color: white !important;
        margin: 0 0 16px 0 !important;
    }
    
    .feature-card p {
        font-size: 1rem !important;
        line-height: 1.6 !important;
        color: rgba(255,255,255,0.9) !important;
        margin: 0 !important;
    }
    
    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .landing-title {
            font-size: 2.5rem !important;
        }
        
        .landing-icon {
            font-size: 48px !important;
            margin-right: 16px !important;
        }
        
        .feature-card {
            margin: 16px 0;
            height: auto;
            padding: 32px 24px;
        }
        
        button, .stButton > button {
            min-width: 90% !important;
            font-size: 1.2rem !important;
            padding: 20px 40px !important;
        }
    }
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

# Chart layout configurations
CHART_CONFIGS = {
    "bar": {
        "height": 400,
        "yaxis": {"tickformat": "d"},
        "margin": {"l": 50, "r": 20, "t": 60, "b": 50},
        "showlegend": False
    },
    "status": {
        "height": 140,
        "barmode": "stack",
        "margin": {"l": 10, "r": 10, "t": 40, "b": 10},
        "showlegend": True,
        "xaxis": {"tickformat": "d"}
    },
    "geographic": {
        "height": 700,
        "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
    }
}