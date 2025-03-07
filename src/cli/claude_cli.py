#!/usr/bin/env python3
"""
Claude CLI - Command Line Interface for Claude API

This script provides a command line interface for interacting with the Claude API
with enhanced features like caching, proper configuration, and reasoning extraction.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.claude_api import claude
from src.core import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("claude_cli")

def main():
    """CLI entry point for Claude API"""
    
    # Create argument parser
    parser = argparse.ArgumentParser(description="Command line interface for Claude API")
    
    # Prompt can be provided as a positional argument or via stdin
    parser.add_argument("prompt", nargs="?", help="Prompt text to send to Claude")
    
    # Additional configuration options
    parser.add_argument("--model", help=f"Claude model to use (default: {config.CLAUDE_MODEL})")
    parser.add_argument("--max-tokens", type=int, default=4000, help="Maximum tokens in response")
    parser.add_argument("--temperature", type=float, default=0.7, help="Response temperature (0.0-1.0)")
    parser.add_argument("--system", help="Optional system prompt")
    parser.add_argument("--extract-reasoning", action="store_true", 
                      help="Extract and only display reasoning from Claude's response")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Get prompt from argument or stdin
    prompt = args.prompt
    if not prompt:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
        else:
            parser.print_help()
            sys.exit(1)
    
    try:
        # Call Claude API
        response = claude.call(
            prompt=prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            system_prompt=args.system
        )
        
        # Handle the response
        if args.extract_reasoning:
            # Extract and display only the reasoning
            reasoning = claude.extract_reasoning(response)
            print(reasoning)
        else:
            # Display the full response
            print(response)
            
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()