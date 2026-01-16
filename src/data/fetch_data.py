
"""
Elexon API data fetcher for UK electricity generation data.
Fetches actual generation by fuel type from the Elexon Portal API.
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import time
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.config import RAW_DATA_DIR

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElexonDataFetcher:
    """
    Fetches UK electricity generation data from Elexon Portal API.
    
    API: https://data.elexon.co.uk/bmrs/api/v1/
    No API key required.
    """
    
    BASE_URL = 'https://data.elexon.co.uk/bmrs/api/v1'
    
    # Data quality thresholds
    MIN_TOTAL_GENERATION = 25000  # MW - UK typically generates >25GW
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'UK-Energy-Grid-Dashboard/1.0'
        })
        
    def fetch_generation_data(
        self, 
        start_date: datetime, 
        end_date: datetime,
        retry_attempts: int = 3
    ) -> pd.DataFrame:
        """
        Fetch actual generation by fuel type for a date range.
        
        Args:
            start_date: Start datetime for data fetch
            end_date: End datetime for data fetch
            retry_attempts: Number of retry attempts on failure
            
        Returns:
            DataFrame with columns: timestamp, fuel_type, generation_mw
        """
        logger.info(f'Fetching generation data from {start_date} to {end_date}')
        
        endpoint = f'{self.BASE_URL}/generation/actual/per-type'
        
        params = {
            'from': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'to': end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        for attempt in range(retry_attempts):
            try:
                response = self._make_request(endpoint, params)
                
                if response.status_code == 200:
                    df = self._parse_response(response.json())
                    logger.info(f'Successfully fetched {len(df)} records')
                    
                    # Data quality check
                    df = self._apply_quality_checks(df)
                    
                    return df
                else:
                    logger.warning(f'API returned status {response.status_code}')
                    
            except Exception as e:
                logger.error(f'Attempt {attempt + 1} failed: {str(e)}')
                if attempt < retry_attempts - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        raise Exception('Failed to fetch data after all retry attempts')
    
    def fetch_current_generation(self) -> pd.DataFrame:
        """
        Fetch the most recent generation data (last 24 hours).
        
        Returns:
            DataFrame with current generation mix
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=24)
        return self.fetch_generation_data(start_date, end_date)
    
    def fetch_historical_data(self, days: int = 7) -> pd.DataFrame:
        """
        Fetch historical generation data for specified number of days.
        
        Args:
            days: Number of days of historical data to fetch
            
        Returns:
            DataFrame with historical generation data
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Fetch in chunks to be respectful to API
        all_data = []
        chunk_size = 7  # days per request
        
        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + timedelta(days=chunk_size), end_date)
            
            logger.info(f'Fetching chunk: {current_start.date()} to {current_end.date()}')
            chunk_df = self.fetch_generation_data(current_start, current_end)
            all_data.append(chunk_df)
            
            current_start = current_end
            time.sleep(1)  # Rate limiting
        
        combined_df = pd.concat(all_data, ignore_index=True)
        logger.info(f'Fetched {len(combined_df)} total records over {days} days')
        
        return combined_df
    
    def _make_request(self, endpoint: str, params: Dict) -> requests.Response:
        """
        Make HTTP request to API with error handling and timing.
        """
        start_time = time.time()
        response = self.session.get(endpoint, params=params, timeout=30)
        latency = (time.time() - start_time) * 1000
        
        logger.info(f'API request completed in {latency:.2f}ms - Status: {response.status_code}')
        
        return response
    
    def _parse_response(self, data: Dict) -> pd.DataFrame:
        """
        Parse JSON response from Elexon API into DataFrame.
        
        Args:
            data: JSON response from API
            
        Returns:
            Parsed DataFrame with columns: timestamp, fuel_type, generation_mw
        """
        records = []
        
        for period in data.get('data', []):
            timestamp = period['startTime']
            
            for entry in period.get('data', []):
                records.append({
                    'timestamp': timestamp,
                    'fuel_type': entry['psrType'],
                    'generation_mw': entry['quantity']
                })
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def _apply_quality_checks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply data quality checks and filter out suspicious records.
        
        Known issue: API sometimes returns incomplete data where only renewables
        report generation, causing artificially high renewable percentages.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame with quality flags
        """
        if df.empty:
            return df
        
        # Calculate total generation per timestamp
        totals = df.groupby('timestamp')['generation_mw'].sum().reset_index()
        totals.columns = ['timestamp', 'total_generation']
        
        # Flag suspicious periods (total < 25 GW indicates incomplete data)
        totals['quality_flag'] = totals['total_generation'] >= self.MIN_TOTAL_GENERATION
        
        # Merge quality flags back
        df = df.merge(totals[['timestamp', 'total_generation', 'quality_flag']], on='timestamp')
        
        # Log quality issues
        bad_records = (~df['quality_flag']).sum()
        if bad_records > 0:
            logger.warning(f'Found {bad_records} records with quality issues (incomplete data)')
            bad_periods = df['timestamp'].nunique() - df[df['quality_flag']]['timestamp'].nunique()
            logger.warning(f'Filtering out {bad_periods} time periods')
        
        # Filter to only good quality data
        df_clean = df[df['quality_flag']].drop(columns=['quality_flag']).reset_index(drop=True)
        
        return df_clean
    
    def save_to_csv(self, df: pd.DataFrame, filename: str) -> Path:
        """
        Save DataFrame to CSV in raw data directory.
        
        Args:
            df: DataFrame to save
            filename: Name of CSV file
            
        Returns:
            Path to saved file
        """
        filepath = RAW_DATA_DIR / filename
        df.to_csv(filepath, index=False)
        logger.info(f'Data saved to {filepath}')
        return filepath
    
    def get_fuel_type_mapping(self) -> Dict[str, str]:
        """
        Returns standardized fuel type names and categories.
        """
        return {
            'Biomass': 'renewable',
            'Fossil Gas': 'fossil',
            'Fossil Hard coal': 'fossil',
            'Fossil Oil': 'fossil',
            'Hydro Pumped Storage': 'renewable',
            'Hydro Run-of-river and poundage': 'renewable',
            'Nuclear': 'nuclear',
            'Other': 'other',
            'Solar': 'renewable',
            'Wind Offshore': 'renewable',
            'Wind Onshore': 'renewable'
        }


# Convenience functions
def fetch_latest_data() -> pd.DataFrame:
    """Quick function to fetch latest generation data."""
    fetcher = ElexonDataFetcher()
    return fetcher.fetch_current_generation()


def fetch_historical(days: int = 7) -> pd.DataFrame:
    """Quick function to fetch historical data."""
    fetcher = ElexonDataFetcher()
    return fetcher.fetch_historical_data(days)


if __name__ == '__main__':
    # Test the fetcher
    print('Testing Elexon Data Fetcher...')
    
    fetcher = ElexonDataFetcher()
    
    # Test current data fetch
    print('\nFetching current generation data...')
    current_data = fetcher.fetch_current_generation()
    print(f'Fetched {len(current_data)} records')
    print(current_data.head(10))
    
    # Save to CSV
    if len(current_data) > 0:
        fetcher.save_to_csv(current_data, 'test_generation_data.csv')
        print('\nTest successful!')