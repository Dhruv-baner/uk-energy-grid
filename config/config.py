"""
Main configuration file for the UK Energy Grid Dashboard.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
PREDICTIONS_DIR = DATA_DIR / "predictions"
LOGS_DIR = BASE_DIR / "logs"

# API Configuration
GRID_ESO_BASE_URL = "https://api.bmreports.com/BMRS"
GRID_ESO_API_KEY = os.getenv("GRID_ESO_API_KEY", "")  # Optional, check if needed

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'energy_grid.db'}"
)

# Data Collection Settings
DATA_REFRESH_INTERVAL = 1800  # 30 minutes in seconds
HISTORICAL_DAYS = 365  # Days of historical data to fetch initially
FUEL_TYPES = [
    "coal", "gas", "nuclear", "wind", "solar", 
    "hydro", "biomass", "imports", "other"
]

# Model Configuration
FORECAST_HORIZON = 24  # hours
MODEL_RETRAIN_INTERVAL = 7  # days
ANOMALY_THRESHOLD = 2.5  # standard deviations

# Dashboard Settings
DASHBOARD_UPDATE_INTERVAL = 30  # seconds
DASHBOARD_PORT = 8501

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "json"  # json or text

# Monitoring (Part 2)
ENABLE_MLFLOW = os.getenv("ENABLE_MLFLOW", "False").lower() == "true"
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "")
ENABLE_PROMETHEUS = os.getenv("ENABLE_PROMETHEUS", "False").lower() == "true"
