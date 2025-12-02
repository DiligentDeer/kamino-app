import logging
import os
from typing import Dict, Optional, Tuple

import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# Load environment variables from .env file
load_dotenv()


def get_database_url():
    """
    Get database URL from environment variables.

    Returns:
        str: Database connection URL
    """
    # You can customize these environment variable names as needed
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "itb_quant_database")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def update_last_login(user_id: int) -> None:
    """
    Update the last login timestamp for a user.

    Parameters:
        user_id (int): User's ID
    """
    database_url = get_database_url()

    try:
        engine = create_engine(database_url)

        query = """
        UPDATE quant__euler_vaults_dashboard__users 
        SET last_login = CURRENT_TIMESTAMP 
        WHERE _id = :user_id
        """

        with engine.connect() as conn:
            conn.execute(text(query), {"user_id": user_id})
            conn.commit()

    except Exception as e:
        logging.error("Error updating last login: %s", str(e))
    finally:
        if "engine" in locals():
            engine.dispose()


def login_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Authenticate a user with email and password.

    Parameters:
        email (str): User's email address
        password (str): User's password

    Returns:
        Tuple[bool, str, Optional[Dict]]: (success, message, user_data)
    """
    database_url = get_database_url()

    try:
        engine = create_engine(database_url)

        query = """
        SELECT _id, email, password_hash, first_name, last_name, is_active, is_admin, last_login
        FROM quant__euler_vaults_dashboard__users 
        WHERE email = :email
        """

        with engine.connect() as conn:
            result = conn.execute(text(query), {"email": email.lower()})
            user = result.fetchone()

        if not user:
            return False, "Invalid email or password", None

        # Check if user is active
        if not user.is_active:
            return False, "Account is deactivated", None

        # Verify password
        stored_hash = user.password_hash.encode("utf-8")
        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return False, "Invalid email or password", None

        # Update last login
        update_last_login(user._id)

        # Return user data (excluding password hash)
        user_data = {
            "id": user._id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
            "last_login": user.last_login,
        }

        logging.info("Successful login for user: %s", email)
        return True, "Login successful", user_data

    except Exception as e:
        logging.error("Error during login: %s", str(e))
        return False, f"Login failed: {str(e)}", None
    finally:
        if "engine" in locals():
            engine.dispose()


def is_email_whitelisted(email: str) -> Tuple[bool, bool]:
    """
    Check if an email is whitelisted for registration and return additional info.

    Parameters:
        email (str): Email address to check

    Returns:
        Tuple[bool, bool]: (is_whitelisted, is_admin)
    """
    database_url = get_database_url()

    try:
        engine = create_engine(database_url)

        query = """
        SELECT is_admin
        FROM quant__euler_vaults_dashboard__email_whitelist 
        WHERE email = :email AND is_active = TRUE
        """

        with engine.connect() as conn:
            result = conn.execute(text(query), {"email": email.lower()})
            row = result.fetchone()

        if row:
            is_admin = row[0] if row[0] is not None else False
            return True, is_admin
        else:
            return False, False

    except Exception as e:
        logging.error("Error checking email whitelist: %s", str(e))
        return False, False
    finally:
        if "engine" in locals():
            engine.dispose()


def user_exists(email: str) -> bool:
    """
    Check if a user with the given email already exists.

    Parameters:
        email (str): Email address to check

    Returns:
        bool: True if user exists, False otherwise
    """
    database_url = get_database_url()

    try:
        engine = create_engine(database_url)

        query = """
        SELECT COUNT(*) as count 
        FROM quant__euler_vaults_dashboard__users 
        WHERE email = :email
        """

        with engine.connect() as conn:
            result = conn.execute(text(query), {"email": email.lower()})
            count = result.fetchone()[0]

        return count > 0

    except Exception as e:
        logging.error("Error checking if user exists: %s", str(e))
        return False
    finally:
        if "engine" in locals():
            engine.dispose()


def register_user(
    email: str, password: str, first_name: str = None, last_name: str = None
) -> Tuple[bool, str]:
    """
    Register a new user with secure password hashing.

    Parameters:
        email (str): User's email address
        password (str): User's password (will be hashed)
        first_name (str, optional): User's first name
        last_name (str, optional): User's last name

    Returns:
        Tuple[bool, str]: (success, message)
    """
    database_url = get_database_url()

    try:
        # Check if email is whitelisted
        is_whitelisted, is_admin = is_email_whitelisted(email)
        if not is_whitelisted:
            return False, "Email is not whitelisted for registration"

        # Check if user already exists
        if user_exists(email):
            return False, "User with this email already exists"

        # Hash the password
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        engine = create_engine(database_url)

        query = """
        INSERT INTO quant__euler_vaults_dashboard__users (email, password_hash, first_name, last_name, is_admin)
        VALUES (:email, :password_hash, :first_name, :last_name, :is_admin)
        """

        with engine.connect() as conn:
            conn.execute(
                text(query),
                {
                    "email": email.lower(),
                    "password_hash": password_hash.decode("utf-8"),
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_admin": is_admin,
                },
            )
            conn.commit()

        logging.info("Successfully registered user: %s", email)
        return True, "User registered successfully"

    except Exception as e:
        logging.error("Error registering user: %s", str(e))
        return False, f"Registration failed: {str(e)}"
    finally:
        if "engine" in locals():
            engine.dispose()


def some_db_query():
    """
    Some database query.

    Returns:
        str: Result of the query
    """
    return "Some database query"
