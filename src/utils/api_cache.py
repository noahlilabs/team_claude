#!/usr/bin/env python3
"""
Cache for Claude API calls to reduce costs and improve response times.
"""

import os
import json
import hashlib
import time
from pathlib import Path
import sys
import logging

# Add the parent directory to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("api_cache")

class ClaudeCache:
    """Cache for Claude API calls."""
    
    def __init__(self, cache_dir=None, expiry=None):
        """Initialize the cache."""
        self.cache_dir = cache_dir or config.CACHE_DIR
        self.expiry = expiry or config.CACHE_EXPIRY
        self.enabled = config.ENABLE_CACHE
        
        # Create cache directory if it doesn't exist
        if self.enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
            # Create a more organized structure for cached responses
            self.claude_cache_dir = Path(self.cache_dir) / "claude_responses"
            self.claude_cache_dir.mkdir(exist_ok=True)
            logger.info(f"Claude cache initialized at {self.claude_cache_dir}")
    
    def _get_cache_key(self, prompt, model, max_tokens, thinking_config):
        """Generate a unique cache key for an API call."""
        # Create a dictionary of all parameters
        params = {
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "thinking_configuration": thinking_config
        }
        
        # Convert to JSON and hash
        params_json = json.dumps(params, sort_keys=True)
        return hashlib.md5(params_json.encode()).hexdigest()
    
    def _get_cache_path(self, key):
        """Get the path to the cache file for a key."""
        return os.path.join(self.claude_cache_dir, f"{key}.json")
    
    def get(self, prompt, model, max_tokens, thinking_config):
        """Get cached response if available."""
        if not self.enabled:
            logger.debug("Cache is disabled, skipping cache lookup")
            return None
            
        key = self._get_cache_key(prompt, model, max_tokens, thinking_config)
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            logger.debug(f"Cache miss: {key[:8]}...")
            return None
            
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                
            # Check for expiry
            if time.time() - data["timestamp"] > self.expiry:
                # Cache expired
                logger.debug(f"Cache expired: {key[:8]}...")
                os.remove(cache_path)
                return None
                
            logger.info(f"Cache hit: {key[:8]}...")
            return data["response"]
        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None
    
    def save(self, prompt, model, max_tokens, thinking_config, response):
        """Save a response to the cache."""
        if not self.enabled:
            return
            
        key = self._get_cache_key(prompt, model, max_tokens, thinking_config)
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    "timestamp": time.time(),
                    "response": response,
                    "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt
                }, f, indent=2)
            logger.debug(f"Saved to cache: {key[:8]}...")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
    
    def list_cached_entries(self, max_entries=10):
        """List cached entries with timestamps."""
        if not self.enabled or not os.path.exists(self.claude_cache_dir):
            return []
        
        entries = []
        try:
            for cache_file in os.listdir(self.claude_cache_dir):
                if not cache_file.endswith('.json'):
                    continue
                    
                cache_path = os.path.join(self.claude_cache_dir, cache_file)
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                
                cache_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data["timestamp"]))
                entries.append({
                    "key": cache_file.replace('.json', ''),
                    "timestamp": cache_time,
                    "prompt_preview": data.get("prompt_preview", "No preview available"),
                    "file": cache_path
                })
            
            # Sort by timestamp (newest first) and limit
            return sorted(entries, key=lambda x: os.path.getmtime(x["file"]), reverse=True)[:max_entries]
        except Exception as e:
            logger.error(f"Error listing cache entries: {e}")
            return []
    
    def clear_cache(self, older_than=None):
        """
        Clear the cache.
        
        Args:
            older_than: Optional time in seconds. If provided, only clear entries
                      older than this many seconds.
        """
        if not self.enabled or not os.path.exists(self.claude_cache_dir):
            return 0
        
        removed = 0
        try:
            for cache_file in os.listdir(self.claude_cache_dir):
                if not cache_file.endswith('.json'):
                    continue
                    
                cache_path = os.path.join(self.claude_cache_dir, cache_file)
                
                # If older_than is provided, check file age
                if older_than is not None:
                    file_age = time.time() - os.path.getmtime(cache_path)
                    if file_age < older_than:
                        continue
                
                os.remove(cache_path)
                removed += 1
            
            logger.info(f"Removed {removed} cache entries")
            return removed
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

# Create a global cache instance
claude_cache = ClaudeCache()