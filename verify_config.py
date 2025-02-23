import logging
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_env_variables():
    """Check environment variables configuration"""
    load_dotenv()
    
    required_vars = {
        'TOS_API_KEY': os.getenv('TOS_API_KEY'),
        'TOS_ACCOUNT_ID': os.getenv('TOS_ACCOUNT_ID')
    }
    
    logger.info("\n=== Environment Variables ===")
    all_present = True
    
    for var, value in required_vars.items():
        if value:
            # Safely display API key
            if var == 'TOS_API_KEY':
                display_value = f"{value[:5]}...@AMER.OAUTHAP" if value else "Not Set"
            else:
                display_value = value
            logger.info(f"✓ {var}: {display_value}")
        else:
            logger.error(f"✗ {var} is not set")
            all_present = False
    
    return all_present

def check_token_file():
    """Check if token file exists and is valid"""
    token_path = Path('token.json')
    
    logger.info("\n=== Token File ===")
    
    if not token_path.exists():
        logger.warning("✗ token.json not found - will be created during authentication")
        return False
        
    try:
        with open(token_path) as f:
            token_data = json.load(f)
            
        # Check basic token structure
        required_fields = ['access_token', 'refresh_token', 'scope']
        missing_fields = [field for field in required_fields if field not in token_data]
        
        if missing_fields:
            logger.error(f"✗ Token file is missing fields: {', '.join(missing_fields)}")
            return False
            
        logger.info("✓ token.json exists and has valid structure")
        logger.info(f"  Scope: {token_data.get('scope', 'Not specified')}")
        return True
        
    except json.JSONDecodeError:
        logger.error("✗ token.json exists but is not valid JSON")
        return False
    except Exception as e:
        logger.error(f"✗ Error reading token.json: {e}")
        return False

def check_redirect_uri():
    """Verify redirect URI configuration"""
    logger.info("\n=== Redirect URI Configuration ===")
    redirect_uri = 'http://localhost:8080'
    
    logger.info(f"Current redirect URI: {redirect_uri}")
    logger.info("Please verify this matches your TD Ameritrade developer app settings")
    logger.info("\nImportant Notes:")
    logger.info("1. The redirect URI in your TD Ameritrade developer portal must exactly match:")
    logger.info("   http://localhost:8080")
    logger.info("2. The Schwab login page is expected due to TD Ameritrade integration")
    logger.info("3. Use your TD Ameritrade credentials when logging in")

def main():
    logger.info("Starting Configuration Verification\n")
    
    env_ok = check_env_variables()
    token_ok = check_token_file()
    check_redirect_uri()
    
    logger.info("\n=== Summary ===")
    logger.info(f"Environment Variables: {'✓ OK' if env_ok else '✗ Need attention'}")
    logger.info(f"Token File: {'✓ OK' if token_ok else '⚠ Will be created during auth'}")
    
    if not env_ok:
        logger.info("\nAction Required: Set up missing environment variables in .env file")
    if not token_ok:
        logger.info("\nNote: Token file will be created when you run authentication")
    
    logger.info("\nNext Steps:")
    logger.info("1. Run test_auth.py to authenticate")
    logger.info("2. When redirected to Schwab, use your TD Ameritrade credentials")
    logger.info("3. Wait for the authentication to complete")

if __name__ == "__main__":
    main()
