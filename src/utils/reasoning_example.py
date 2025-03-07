#!/usr/bin/env python3
"""
Claude Extended Thinking Example with AWS Bedrock

This script demonstrates how to use Claude's extended thinking capabilities
with AWS Bedrock, allowing for detailed step-by-step reasoning for complex tasks.
"""

import os
import sys
import json
import boto3
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core import config
from src.utils.env_loader import load_env

# Load environment variables
load_env()

def reasoning_example(prompt: str):
    """
    Demonstrate Claude's extended thinking using AWS Bedrock.
    
    Args:
        prompt: The prompt to send to Claude
        
    Returns:
        A tuple of (thinking, final_answer)
    """
    # Create a Bedrock runtime client
    bedrock_runtime = boto3.client(
        'bedrock-runtime', 
        region_name='us-east-1',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )
    
    # Define the message to Claude
    messages = [
        {"role": "user", "content": prompt}
    ]
    
    # Configure the reasoning parameters
    reasoning_config = {
        "type": "enabled",
        "budget_tokens": 8000  # Adjust based on complexity
    }
    
    # Set max tokens to include prompt length and thinking budget
    max_tokens = 12000  # Ensure this includes both prompt length and thinking budget
    
    # Send the request with reasoning enabled
    try:
        response = bedrock_runtime.converse(
            modelId='anthropic.claude-3-7-sonnet-20250219',
            messages=messages,
            additionalModelRequestFields={
                "thinking": reasoning_config
            },
            maxTokens=max_tokens
        )
        
        # Extract the reasoning and final answer
        thinking = response.get('thinking', {}).get('content', 'No reasoning provided')
        final_answer = response['output']['message']['content']
        
        return thinking, final_answer
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None

def main():
    """Run a demonstration of Claude's extended thinking capabilities."""
    
    # Example prompt that requires reasoning
    prompt = "Solve this math problem step by step: If a train travels at 60 miles per hour for 2.5 hours, how far does it go?"
    
    print("===== Claude Extended Thinking Example =====")
    print(f"Sending prompt: {prompt}\n")
    
    thinking, answer = reasoning_example(prompt)
    
    if thinking and answer:
        print("===== REASONING PROCESS =====")
        print(thinking)
        print("\n===== FINAL ANSWER =====")
        print(answer)
    else:
        print("Failed to get a response from Claude.")
    
    print("\nTo use this with your own prompts:")
    print("python reasoning_example.py \"Your prompt here\"")

if __name__ == "__main__":
    # Check if a custom prompt was provided
    if len(sys.argv) > 1:
        custom_prompt = sys.argv[1]
        print("===== Claude Extended Thinking Example =====")
        print(f"Sending prompt: {custom_prompt}\n")
        
        thinking, answer = reasoning_example(custom_prompt)
        
        if thinking and answer:
            print("===== REASONING PROCESS =====")
            print(thinking)
            print("\n===== FINAL ANSWER =====")
            print(answer)
        else:
            print("Failed to get a response from Claude.")
    else:
        # Run the default example
        main() 