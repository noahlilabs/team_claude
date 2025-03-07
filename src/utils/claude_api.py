#!/usr/bin/env python3
"""
Claude API Wrapper

This module provides a consistent interface to the Claude API with features
like caching, proper configuration, and error handling.
"""

import os
import sys
import json
import requests
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directory to path to allow importing project modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core import config
from src.utils.api_cache import claude_cache
from src.utils.env_loader import load_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("claude_api")

class ClaudeAPI:
    """
    A wrapper for interacting with the Claude API with enhanced features.
    """
    
    def __init__(self, api_key=None, model=None, max_retries=3, retry_delay=2):
        """
        Initialize the Claude API wrapper.
        
        Args:
            api_key: Optional API key (defaults to environment variable)
            model: Optional model name (defaults to config.CLAUDE_MODEL)
            max_retries: Maximum number of retry attempts for API calls
            retry_delay: Delay between retries in seconds
        """
        # Load environment variables if not already loaded
        load_env()
        
        # Set up API key, preferring passed value or environment variable
        self.api_key = api_key or os.environ.get(config.ANTHROPIC_API_KEY_ENV)
        if not self.api_key:
            logger.error(f"No API key found. Please set {config.ANTHROPIC_API_KEY_ENV} environment variable.")
        
        # Set up model defaults
        self.model = model or config.CLAUDE_MODEL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Headers for API requests - updated for current API
        self.headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": self.api_key
        }
        
        logger.info(f"Claude API initialized with model: {self.model}")
    
    def call(self, 
             prompt: str, 
             max_tokens: int = 1024, 
             temperature: float = 0.7,
             system_prompt: Optional[str] = None) -> str:
        """
        Call the Claude API with caching and retry logic.
        
        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum number of tokens in the response
            temperature: Sampling temperature (higher = more creative/random)
            system_prompt: Optional system prompt to set context
            
        Returns:
            Claude's response text
            
        Raises:
            Exception: If API call fails after max retries
        """
        # Check cache first
        cache_key = f"{prompt}_{max_tokens}_{temperature}_{system_prompt}"
        cached_response = claude_cache.get(prompt, self.model, max_tokens, {})
        if cached_response:
            logger.info("Using cached response")
            return cached_response
        
        # Prepare the API request
        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        # Add system prompt if provided
        if system_prompt:
            data["system"] = system_prompt
        
        # Make the API request with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Making API request (attempt {attempt+1}/{self.max_retries})")
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=self.headers,
                    json=data,
                    timeout=60  # Add a timeout to prevent hanging requests
                )
                
                # Check response
                if response.status_code == 200:
                    # Parse the response and extract the content
                    result = response.json()
                    content = ""
                    
                    # Handle content blocks (for newer API versions)
                    if "content" in result and isinstance(result["content"], list):
                        for block in result["content"]:
                            if block.get("type") == "text":
                                content += block.get("text", "")
                    else:
                        # Fallback for older API responses
                        content = result.get("content", "")
                    
                    # Cache the response
                    claude_cache.save(prompt, self.model, max_tokens, {}, content)
                    return content
                    
                elif response.status_code == 429:
                    # Rate limit - wait and retry
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry.")
                    time.sleep(wait_time)
                else:
                    # Other error - log and retry
                    logger.error(f"API request failed with status {response.status_code}: {response.text}")
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.error(f"Exception during API request: {str(e)}")
                time.sleep(self.retry_delay)
        
        # If we get here, all retries failed
        error_msg = f"Failed to get response from Claude API after {self.max_retries} attempts"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def extract_reasoning(self, response: str) -> str:
        """
        Extract reasoning from Claude's response.
        
        Args:
            response: The full response from Claude
            
        Returns:
            The extracted reasoning part of the response
        """
        # Check for structured reasoning tags
        if "<thinking>" in response and "</thinking>" in response:
            # Extract content between thinking tags
            start = response.find("<thinking>") + len("<thinking>")
            end = response.find("</thinking>")
            if start < end:
                return response[start:end].strip()
                
        elif "<reasoning>" in response and "</reasoning>" in response:
            # Extract content between reasoning tags
            start = response.find("<reasoning>") + len("<reasoning>")
            end = response.find("</reasoning>")
            if start < end:
                return response[start:end].strip()
        
        # Look for reasoning-like content if no tags
        reasoning_markers = [
            "I'm thinking", "Let me think", "Step by step", "Let me analyze",
            "Let me break this down", "Here's my reasoning", "My thought process"
        ]
        
        for marker in reasoning_markers:
            if marker in response:
                # Return a generous portion from the marker
                marker_pos = response.find(marker)
                return response[marker_pos:marker_pos + 2000].strip()
        
        # Default fallback - return the first part of the response
        return response[:1000].strip()

# Create a singleton instance
claude = ClaudeAPI()

def main():
    """Simple test function for the Claude API"""
    if len(sys.argv) < 2:
        print("Usage: python claude_api.py 'Your prompt here'")
        sys.exit(1)
    
    prompt = sys.argv[1]
    response = claude.call(prompt)
    print(response)

if __name__ == "__main__":
    main()