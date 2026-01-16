"""
Initialize database schema for UK Energy Grid Dashboard.
"""
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import DATABASE_URL

Base = declarative_base()

class GenerationData(Base):
    __tablename__ = 'generation_data'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    fuel_type = Column(String(50), nullable=False)
    generation_mw = Column(Float, nullable=False)
    data_source = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Prediction(Base):
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    prediction_timestamp = Column(DateTime(timezone=True), nullable=False)
    target_timestamp = Column(DateTime(timezone=True), nullable=False)
    fuel_type = Column(String(50), nullable=False)
    predicted_value = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ModelMetrics(Base):
    __tablename__ = 'model_metrics'
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(Float, nullable=False)
    evaluation_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DataQuality(Base):
    __tablename__ = 'data_quality'
    
    id = Column(Integer, primary_key=True)
    check_name = Column(String(100), nullable=False)
    check_result = Column(Boolean, nullable=False)
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def init_database():
    """Create all database tables."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    print(f"✅ Database initialized successfully at {DATABASE_URL}")

if __name__ == "__main__":
    init_database()
