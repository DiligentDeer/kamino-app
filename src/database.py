import logging
import os
from typing import Dict, Optional, Tuple

import bcrypt
import pandas as pd
from dotenv import load_dotenv, dotenv_values
from sqlalchemy import create_engine, text

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
load_dotenv()


def get_database_url():
    """
    Get database URL from environment variables.
    """
    config = dotenv_values(".env")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "itb_quant_database")
    db_user = config.get("USER") or os.getenv("POSTGRES_USER", "postgres")
    db_password = config.get("PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def get_analytics_database_url():
    """
    Get database URL for analytics queries (potentially read-only).
    """
    # Reuse the same connection logic as we don't have separate read-only credentials explicitly available in context
    # If specific read-only credentials were set in .env, they should be accessed here if known.
    # For now, we fallback to the main database URL to ensure connectivity.
    return get_database_url()

def register_user(email, password, first_name, last_name):
    database_url = get_database_url()
    try:
        engine = create_engine(database_url)
        # hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = """
        INSERT INTO quant__euler_vaults_dashboard__users (email, password_hash, first_name, last_name, is_admin)
        VALUES (:email, :password_hash, :first_name, :last_name, FALSE)
        """
        with engine.connect() as conn:
            conn.execute(text(query), {
                "email": email, 
                "password_hash": password_hash, 
                "first_name": first_name, 
                "last_name": last_name
            })
            conn.commit()
        return True, "User registered successfully"
    except Exception as e:
        logging.error("Error registering user: %s", str(e))
        return False, str(e)
    finally:
        if "engine" in locals():
            engine.dispose()

def login_user(email, password):
    database_url = get_database_url()
    try:
        engine = create_engine(database_url)
        query = "SELECT password_hash, first_name, last_name, is_admin FROM quant__euler_vaults_dashboard__users WHERE email = :email"
        with engine.connect() as conn:
            result = conn.execute(text(query), {"email": email})
            user = result.fetchone()
            
        if user:
            stored_hash = user[0]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                user_data = {
                    "email": email,
                    "first_name": user[1],
                    "last_name": user[2],
                    "is_admin": user[3]
                }
                return True, "Login successful", user_data
            else:
                return False, "Invalid password", None
        else:
            return False, "User not found", None
    except Exception as e:
        logging.error("Error logging in: %s", str(e))
        return False, str(e), None
    finally:
        if "engine" in locals():
            engine.dispose()

def get_max_position_timestamp() -> Optional[int]:
    """
    Get the latest indexed timestamp from quant__kamino_user_position_split.
    """
    database_url = get_analytics_database_url()
    try:
        engine = create_engine(database_url)
        query = "SELECT max(timestamp) FROM quant__kamino_user_position_split"
        with engine.connect() as conn:
            result = conn.execute(text(query))
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logging.error("Error fetching max timestamp: %s", str(e))
        return None
    finally:
        if "engine" in locals():
            engine.dispose()

def get_pyusd_main_positions(timestamp: int) -> pd.DataFrame:
    database_url = get_analytics_database_url()
    try:
        engine = create_engine(database_url)
        query = """
        SELECT * 
        FROM quant__kamino_user_position_split 
        WHERE lending_market_name = 'Main' 
          AND (supply_symbol = 'PYUSD' OR borrow_symbol = 'PYUSD') 
          AND "timestamp" = :timestamp
        """
        return pd.read_sql(text(query), engine, params={"timestamp": timestamp})
    except Exception as e:
        logging.error("Error fetching PYUSD positions: %s", str(e))
        return pd.DataFrame()
    finally:
        if "engine" in locals():
            engine.dispose()

def get_asset_positions(timestamp: int, market_name: str, asset_symbol: str) -> pd.DataFrame:
    database_url = get_analytics_database_url()
    try:
        engine = create_engine(database_url)
        query = """
        SELECT obligation_id, supply_symbol, supply_value, borrow_symbol, borrow_value 
        FROM quant__kamino_user_position_split 
        WHERE lending_market_name = :market_name 
          AND (supply_symbol = :asset_symbol OR borrow_symbol = :asset_symbol) 
          AND "timestamp" = :timestamp
        """
        return pd.read_sql(
            text(query), 
            engine, 
            params={
                "timestamp": timestamp,
                "market_name": market_name,
                "asset_symbol": asset_symbol
            }
        )
    except Exception as e:
        logging.error("Error fetching asset positions for %s in %s: %s", asset_symbol, market_name, str(e))
        return pd.DataFrame()
    finally:
        if "engine" in locals():
            engine.dispose()

def get_debt_distribution(timestamp: int, market_name: str, asset_symbol: str) -> pd.DataFrame:
    """
    Row 1: Debt distribution backed by [ASSET] collateral.
    Returns: supply_symbol, supply_value, borrow_symbol
    """
    database_url = get_analytics_database_url()
    try:
        engine = create_engine(database_url)
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
        return pd.read_sql(
            text(query), 
            engine, 
            params={
                "timestamp": timestamp,
                "market_name": market_name,
                "asset_symbol": asset_symbol
            }
        )
    except Exception as e:
        logging.error("Error fetching debt distribution for %s in %s: %s", asset_symbol, market_name, str(e))
        return pd.DataFrame()
    finally:
        if "engine" in locals():
            engine.dispose()

def get_collateral_distribution(timestamp: int, market_name: str, asset_symbol: str) -> pd.DataFrame:
    """
    Row 2: Collateral distribution backing [ASSET] debt.
    Returns: borrow_symbol, borrow_value, supply_symbol
    """
    database_url = get_analytics_database_url()
    try:
        engine = create_engine(database_url)
        query = """
        SELECT borrow_symbol, SUM(borrow_value) as borrow_value, supply_symbol, SUM(supply_value) as supply_value
        FROM quant__kamino_user_position_split 
        WHERE lending_market_name = :market_name 
          AND borrow_symbol = :asset_symbol 
          AND "timestamp" = :timestamp
        GROUP BY supply_symbol, borrow_symbol
        """
        return pd.read_sql(
            text(query), 
            engine, 
            params={
                "timestamp": timestamp,
                "market_name": market_name,
                "asset_symbol": asset_symbol
            }
        )
    except Exception as e:
        logging.error("Error fetching collateral distribution for %s in %s: %s", asset_symbol, market_name, str(e))
        return pd.DataFrame()
    finally:
        if "engine" in locals():
            engine.dispose()

def get_leverage_borrowed(timestamp: int, market_name: str, asset_symbol: str, min_value: float) -> pd.DataFrame:
    """
    Table 1: Pairs where [ASSET] is Borrowed
    """
    database_url = get_analytics_database_url()
    try:
        engine = create_engine(database_url)
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
        return pd.read_sql(
            text(query), 
            engine, 
            params={
                "timestamp": timestamp,
                "market_name": market_name,
                "asset_symbol": asset_symbol,
                "min_value": min_value
            }
        )
    except Exception as e:
        logging.error("Error fetching leverage borrowed for %s in %s: %s", asset_symbol, market_name, str(e))
        return pd.DataFrame()
    finally:
        if "engine" in locals():
            engine.dispose()

def get_leverage_collateral(timestamp: int, market_name: str, asset_symbol: str, min_value: float) -> pd.DataFrame:
    """
    Table 2: Pairs where [ASSET] is Collateral
    """
    database_url = get_analytics_database_url()
    try:
        engine = create_engine(database_url)
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
        return pd.read_sql(
            text(query), 
            engine, 
            params={
                "timestamp": timestamp,
                "market_name": market_name,
                "asset_symbol": asset_symbol,
                "min_value": min_value
            }
        )
    except Exception as e:
        logging.error("Error fetching leverage collateral for %s in %s: %s", asset_symbol, market_name, str(e))
        return pd.DataFrame()
    finally:
        if "engine" in locals():
            engine.dispose()
