#!/usr/bin/env python3
"""
Environment Variable Loader

This module handles loading environment variables from .env files,
ensuring API keys and configuration settings are properly loaded.
"""

import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("env_loader")

def find_dotenv(start_path=None):
    """
    Find the .env file by searching upwards from the current directory.
    
    Args:
        start_path: Path to start searching from (defaults to current directory)
        
    Returns:
        Path to the .env file if found, None otherwise
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)
    
    path = start_path.absolute()
    
    # Search for .env in this directory and parent directories
    while path != path.parent:
        env_path = path / ".env"
        if env_path.exists():
            return env_path
        path = path.parent
    
    return None

def load_env(dotenv_path=None):
    """
    Load environment variables from .env file.
    
    Args:
        dotenv_path: Optional path to .env file
        
    Returns:
        True if variables were loaded, False otherwise
    """
    if dotenv_path is None:
        dotenv_path = find_dotenv()
    
    if dotenv_path is None or not Path(dotenv_path).exists():
        logger.warning("No .env file found")
        return False
    
    logger.info(f"Loading environment from {dotenv_path}")
    
    try:
        # Parse the .env file manually
        with open(dotenv_path) as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Handle export statements (like "export KEY=value")
                if line.startswith('export '):
                    line = line[7:]  # Remove 'export ' prefix
                
                # Split on first equals sign
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove surrounding quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    # Set the environment variable
                    os.environ[key] = value
        
        # Check if ANTHROPIC_API_KEY is loaded
        if 'ANTHROPIC_API_KEY' in os.environ:
            api_key = os.environ['ANTHROPIC_API_KEY']
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
            logger.info(f"Loaded ANTHROPIC_API_KEY: {masked_key}")
        else:
            logger.warning("ANTHROPIC_API_KEY not found in .env file")
        
        return True
    
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
        return False

if __name__ == "__main__":
    # When run directly, attempt to load environment variables
    success = load_env()
    
    if success:
        print("Environment variables loaded successfully")
    else:
        print("Failed to load environment variables")