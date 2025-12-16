import os
import pandas as pd
import logging
from sqlalchemy import create_engine, text
from typing import Optional
from dotenv import load_dotenv, dotenv_values

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)

def get_db_url():
    """Constructs the database URL from environment variables."""
    # Try to get read-only user from .env file directly to avoid system USER conflict
    config = dotenv_values(".env")
    user = config.get("USER")
    password = config.get("PASSWORD")
    
    if not user:
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

_engine = None

def get_engine():
    """Returns a singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_url = get_db_url()
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,  # Verify connection before usage
            pool_recycle=1800,   # Recycle connections after 30 minutes
        )
    return _engine

def run_query(query: str, params: Optional[dict] = None) -> pd.DataFrame:
    """
    Executes a SQL query and returns the result as a pandas DataFrame.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            if params:
                result = pd.read_sql(text(query), conn, params=params)
            else:
                result = pd.read_sql(text(query), conn)
            return result
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return pd.DataFrame()

def check_login(username, password):
    # This is a mock implementation. 
    # In a real app, you would hash the password and check against a database.
    # For now, we accept any username/password combination where username == password
    try:
        # Mock user check
        if username == "admin" and password == "admin":
             return True, "Login successful", "admin"
        else:
            return False, "User not found", None
    except Exception as e:
        logging.error("Error logging in: %s", str(e))
        return False, str(e), None

def get_max_position_timestamp() -> Optional[int]:
    """
    Get the latest indexed timestamp from quant__kamino_user_position_split.
    """
    engine = get_engine()
    try:
        query = "SELECT max(timestamp) FROM quant__kamino_user_position_split"
        with engine.connect() as conn:
            result = conn.execute(text(query))
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logging.error("Error fetching max timestamp: %s", str(e))
        return None

def get_pyusd_main_positions(timestamp: int) -> pd.DataFrame:
    query = """
    SELECT * 
    FROM quant__kamino_user_position_split 
    WHERE lending_market_name = 'Main' 
      AND (supply_symbol = 'PYUSD' OR borrow_symbol = 'PYUSD') 
      AND "timestamp" = :timestamp
    """
    return run_query(query, params={"timestamp": timestamp})

def get_asset_positions(timestamp: int, market_name: str, asset_symbol: str) -> pd.DataFrame:
    query = """
    SELECT obligation_id, owner, supply_symbol, supply_value, borrow_symbol, borrow_value 
    FROM quant__kamino_user_position_split 
    WHERE lending_market_name = :market_name 
      AND (supply_symbol = :asset_symbol OR borrow_symbol = :asset_symbol) 
      AND "timestamp" = :timestamp
    """
    return run_query(query, params={
        "timestamp": timestamp,
        "market_name": market_name,
        "asset_symbol": asset_symbol
    })

def get_debt_distribution(timestamp: int, market_name: str, asset_symbol: str) -> pd.DataFrame:
    """
    Row 1: Debt distribution backed by [ASSET] collateral.
    Returns: supply_symbol, supply_value, borrow_symbol
    """
    query = """
    SELECT supply_symbol, SUM(supply_value) as supply_value, borrow_symbol, SUM(borrow_value) as borrow_value
    FROM quant__kamino_user_position_split 
    WHERE lending_market_name = :market_name 
      AND supply_symbol = :asset_symbol 
      AND "timestamp" = :timestamp
      AND borrow_symbol IS NOT NULL 
      AND borrow_symbol != ''
    GROUP BY borrow_symbol, supply_symbol
    """
    return run_query(query, params={
        "timestamp": timestamp,
        "market_name": market_name,
        "asset_symbol": asset_symbol
    })

def get_collateral_distribution(timestamp: int, market_name: str, asset_symbol: str) -> pd.DataFrame:
    """
    Row 2: Collateral distribution backing [ASSET] debt.
    Returns: borrow_symbol, borrow_value, supply_symbol
    """
    query = """
    SELECT borrow_symbol, SUM(borrow_value) as borrow_value, supply_symbol, SUM(supply_value) as supply_value
    FROM quant__kamino_user_position_split 
    WHERE lending_market_name = :market_name 
      AND borrow_symbol = :asset_symbol 
      AND "timestamp" = :timestamp
    GROUP BY supply_symbol, borrow_symbol
    """
    return run_query(query, params={
        "timestamp": timestamp,
        "market_name": market_name,
        "asset_symbol": asset_symbol
    })

def get_leverage_borrowed(timestamp: int, market_name: str, asset_symbol: str, min_value: float) -> pd.DataFrame:
    """
    Table 1: Pairs where [ASSET] is Borrowed
    """
    query = """
    SELECT borrow_symbol, supply_symbol, borrow_value/supply_value AS LTV 
    FROM ( 
        SELECT borrow_symbol, SUM(borrow_value) as borrow_value, supply_symbol, SUM(supply_value) as supply_value 
        FROM quant__kamino_user_position_split 
        WHERE lending_market_name = :market_name 
        AND borrow_symbol = :asset_symbol 
        AND "timestamp" = :timestamp
        GROUP BY supply_symbol, borrow_symbol 
    ) AS sub
    WHERE borrow_value >= :min_value
    """
    return run_query(query, params={
        "timestamp": timestamp,
        "market_name": market_name,
        "asset_symbol": asset_symbol,
        "min_value": min_value
    })

def get_historic_leverage_where_asset_is_collateral(market_name: str, asset_symbol: str, min_value: float) -> pd.DataFrame:
    """
    Historic LTV where [ASSET] is Collateral (supply_symbol = asset).
    Returns: timestamp, borrow_symbol, supply_symbol, LTV
    """
    query = """
    SELECT "timestamp", borrow_symbol, supply_symbol, borrow_value/supply_value AS LTV
    FROM (
        SELECT "timestamp", borrow_symbol, SUM(borrow_value) as borrow_value, supply_symbol, SUM(supply_value) as supply_value
        FROM quant__kamino_user_position_split
        WHERE lending_market_name = :market_name AND supply_symbol = :asset_symbol
        GROUP BY supply_symbol, "timestamp", borrow_symbol
    ) AS subquery
    WHERE borrow_value >= :min_value
    """
    return run_query(query, params={
        "market_name": market_name,
        "asset_symbol": asset_symbol,
        "min_value": min_value
    })

def get_historic_leverage_where_asset_is_borrowed(market_name: str, asset_symbol: str, min_value: float) -> pd.DataFrame:
    """
    Historic LTV where [ASSET] is Borrowed (borrow_symbol = asset).
    Returns: timestamp, borrow_symbol, supply_symbol, LTV
    """
    query = """
    SELECT "timestamp", borrow_symbol, supply_symbol, borrow_value/supply_value AS LTV
    FROM (
        SELECT "timestamp", borrow_symbol, SUM(borrow_value) as borrow_value, supply_symbol, SUM(supply_value) as supply_value
        FROM quant__kamino_user_position_split
        WHERE lending_market_name = :market_name AND borrow_symbol = :asset_symbol
        GROUP BY supply_symbol, "timestamp", borrow_symbol
    ) AS subquery
    WHERE borrow_value >= :min_value
    """
    return run_query(query, params={
        "market_name": market_name,
        "asset_symbol": asset_symbol,
        "min_value": min_value
    })

def get_leverage_collateral(timestamp: int, market_name: str, asset_symbol: str, min_value: float) -> pd.DataFrame:
    """
    Table 2: Pairs where [ASSET] is Collateral
    """
    query = """
    SELECT borrow_symbol, supply_symbol, borrow_value/supply_value AS LTV 
    FROM ( 
        SELECT supply_symbol, SUM(supply_value) as supply_value, borrow_symbol, SUM(borrow_value) as borrow_value 
        FROM quant__kamino_user_position_split 
        WHERE lending_market_name = :market_name 
          AND supply_symbol = :asset_symbol 
          AND "timestamp" = :timestamp
        GROUP BY supply_symbol, borrow_symbol 
    ) AS sub
    WHERE borrow_value >= :min_value
    """
    return run_query(query, params={
        "timestamp": timestamp,
        "market_name": market_name,
        "asset_symbol": asset_symbol,
        "min_value": min_value
    })

def get_liquidation_risk_data(timestamp: int, market_name: str, asset_symbol: str) -> pd.DataFrame:
    """
    Get data for liquidation risk analysis.
    """
    query = """
    SELECT borrow_symbol, borrow_value, supply_symbol, supply_value 
    , CASE WHEN supply_value = 0 THEN 0 ELSE borrow_value/supply_value END AS LTV 
    , CASE WHEN borrow_factor = 0 THEN 0 ELSE supply_lt/borrow_factor END AS LLTV 
    , CASE 
        WHEN supply_value = 0 OR borrow_factor = 0 OR supply_lt = 0 THEN NULL 
        ELSE 1-((borrow_value/supply_value)/(supply_lt/borrow_factor)) 
      END AS collateral_liquidation_price_shock 
    , CASE 
        WHEN supply_value = 0 OR borrow_value = 0 OR borrow_factor = 0 THEN NULL 
        ELSE ((supply_lt/borrow_factor)/(borrow_value/supply_value))-1 
      END AS borrow_liquidation_price_shock 
    FROM quant__kamino_user_position_split 
    WHERE lending_market_name = :market_name 
      AND "timestamp" = :timestamp 
      AND borrow_factor > 0 
      AND (borrow_symbol = :asset_symbol OR supply_symbol = :asset_symbol)
    """
    return run_query(query, params={
        "timestamp": timestamp,
        "market_name": market_name,
        "asset_symbol": asset_symbol
    })
