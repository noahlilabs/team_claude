#!/usr/bin/env python3
"""
Claude Computer Use - Meta Orchestrator Agent

This script implements a meta orchestrator agent that uses Claude's vision capabilities
to work with the multi-agent Claude team and control cursor interactions in the user's environment.
The agent can take screenshots, analyze them with Claude's vision capabilities, and execute
actions based on the analysis.
"""

import os
import sys
import json
import time
import base64
import logging
import argparse
import subprocess
import requests
from io import BytesIO
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from PIL import Image
import pyautogui

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("claude_computer_use.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("claude_computer_use")

def check_dependencies():
    """
    Check if all required dependencies are installed and report any missing ones.
    """
    missing = []
    
    # Check required modules
    required_modules = {
        "PIL": "pillow", 
        "pyautogui": "pyautogui",
        "anthropic": "anthropic"
    }
    
    for module_name, package_name in required_modules.items():
        try:
            __import__(module_name) if module_name != "PIL" else __import__("PIL")
        except ImportError:
            missing.append(package_name)
    
    if missing:
        logger.error(f"Missing required dependencies: {', '.join(missing)}")
        print(f"Error: Missing required dependencies: {', '.join(missing)}")
        print(f"Please install them using: pip install {' '.join(missing)}")
        sys.exit(1)
    
    # If using anthropic, check version compatibility
    try:
        import anthropic
        if hasattr(anthropic, "version") and hasattr(anthropic.version, "__version__"):
            version = anthropic.version.__version__
            logger.info(f"Anthropic SDK version: {version}")
        else:
            logger.warning("Could not detect Anthropic SDK version")
    except ImportError:
        pass  # Already checked above

# Read API key directly from .env file
def read_env_file(file_path='.env'):
    env_vars = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
        return env_vars
    except Exception as e:
        logger.error(f"Error reading .env file: {str(e)}")
        return {}

# Load environment variables
env_vars = read_env_file()

class ClaudeComputerUse:
    """
    Meta orchestrator agent that uses Claude's vision capabilities to control 
    the computer and work with the multi-agent Claude team.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Claude Computer Use agent.
        
        Args:
            api_key: Anthropic API key. If not provided, it will be read from ANTHROPIC_API_KEY environment variable.
        """
        self.api_key = api_key or env_vars.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set it as ANTHROPIC_API_KEY in your environment or .env file.")
        
        # We'll use the Anthropic API directly instead of the SDK
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        self.model = "claude-3-7-sonnet-20250219"  # Using Claude 3.7 Sonnet
        self.conversation_history = []
        self.system_prompt = """
        You are Claude Computer Use, a meta orchestrator agent that can see the screen and control the computer 
        to work with a team of Claude agents. Your purpose is to:

        1. Take screenshots of the current state of the computer
        2. Analyze what you see using your vision capabilities
        3. Decide what actions to take based on the analysis
        4. Control the cursor and keyboard to perform these actions
        5. Coordinate with the multi-agent Claude team running in the environment
        
        You can see what's on screen, interpret it, and take actions to help the user accomplish tasks.
        When interacting with the multi-agent system, you should:
        
        - Read the state of the agents
        - Understand the current tasks and their status
        - Use the view_agent_activity.py script to monitor agent communications
        - Use meta_task.py to assign new high-level tasks
        - Help coordinate between specialized agents
        
        Be thoughtful, careful, and make sure to explain your reasoning before taking actions.
        """
        
        # Track screen state
        self.current_screenshot = None
        self.screen_width, self.screen_height = pyautogui.size()
        
        logger.info(f"Initialized Claude Computer Use with screen size: {self.screen_width}x{self.screen_height}")
    
    def capture_screenshot(self) -> Image.Image:
        """
        Capture a screenshot of the current screen.
        
        Returns:
            The screenshot as a PIL Image.
        """
        screenshot = pyautogui.screenshot()
        self.current_screenshot = screenshot
        logger.info(f"Captured screenshot with dimensions: {screenshot.width}x{screenshot.height}")
        return screenshot
    
    def encode_image_to_base64(self, image: Image.Image) -> str:
        """
        Encode a PIL Image to base64 for sending to Claude API.
        
        Args:
            image: The PIL Image to encode.
            
        Returns:
            Base64 encoded string of the image.
        """
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    def analyze_screen(self, prompt: str) -> Dict:
        """
        Analyze the current screen with Claude's vision capabilities.
        
        Args:
            prompt: The specific question or instruction for Claude about the screen.
            
        Returns:
            Claude's response as a dictionary.
        """
        if not self.current_screenshot:
            self.capture_screenshot()
        
        base64_image = self.encode_image_to_base64(self.current_screenshot)
        
        # Call Claude API directly without using the SDK
        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "temperature": 0,
            "system": self.system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        }
        
        try:
            logger.info("Sending request to Claude API")
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Extract text from response
            response_text = result.get("content", [{}])[0].get("text", "No response received")
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            response_text = f"Error: {str(e)}"
        
        response = {
            "text": response_text,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        }
        
        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })
        
        self.conversation_history.append({
            "role": "assistant",
            "content": response["text"]
        })
        
        logger.info(f"Screen analysis completed for prompt: {prompt[:50]}...")
        return response
    
    def control_cursor(self, x: int, y: int, click: bool = False) -> None:
        """
        Move the cursor to the specified position and optionally click.
        
        Args:
            x: X coordinate.
            y: Y coordinate.
            click: Whether to click at the position.
        """
        pyautogui.moveTo(x, y, duration=0.5)
        logger.info(f"Moved cursor to position: ({x}, {y})")
        
        if click:
            pyautogui.click()
            logger.info(f"Clicked at position: ({x}, {y})")
    
    def type_text(self, text: str) -> None:
        """
        Type the specified text.
        
        Args:
            text: The text to type.
        """
        pyautogui.typewrite(text, interval=0.05)
        logger.info(f"Typed text: {text[:50]}...")
    
    def run_terminal_command(self, command: str) -> str:
        """
        Run a terminal command and return its output.
        
        Args:
            command: The command to run.
            
        Returns:
            The command output.
        """
        logger.info(f"Running terminal command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Command failed with return code {result.returncode}: {result.stderr}")
        
        logger.info(f"Command output: {result.stdout[:100]}...")
        return result.stdout
    
    def coordinate_with_agents(self, task: str) -> str:
        """
        Submit a meta task to the multi-agent Claude team.
        
        Args:
            task: The task description.
            
        Returns:
            The output from the meta task submission.
        """
        logger.info(f"Submitting meta task: {task}")
        result = self.run_terminal_command(f'./meta_task.py "{task}"')
        return result
    
    def view_agent_activity(self, timeout: int = 10) -> str:
        """
        View the current agent activity for a specified duration.
        
        Args:
            timeout: How long to monitor activity in seconds.
            
        Returns:
            Captured agent activity.
        """
        logger.info(f"Viewing agent activity for {timeout} seconds")
        
        # Use timeout command to limit duration
        cmd = f"timeout {timeout} ./view_agent_activity.py"
        result = self.run_terminal_command(cmd)
        return result
    
    def identify_ui_elements(self, element_type: str = None) -> List[Dict]:
        """
        Identify UI elements in the current screenshot.
        
        Args:
            element_type: Optional filter for specific types of elements (buttons, inputs, etc.)
            
        Returns:
            List of identified UI elements with their positions and descriptions.
        """
        prompt = f"Identify all {element_type if element_type else 'UI'} elements visible on screen. " \
                 f"For each element, provide its approximate coordinates, type, and description."
        
        analysis = self.analyze_screen(prompt)
        
        # In a production system, you'd want to parse this more robustly
        # This is a simplified version that assumes Claude returns a well-structured response
        return analysis
    
    def execute_workflow(self, goal: str) -> Dict:
        """
        Execute a complete workflow to achieve a specified goal.
        
        Args:
            goal: The goal to achieve.
            
        Returns:
            Result of the workflow execution.
        """
        logger.info(f"Executing workflow for goal: {goal}")
        
        # 1. Analyze current screen state
        screen_analysis = self.analyze_screen(f"What is currently visible on the screen? Particularly focus on the state of the multi-agent system and any relevant information for achieving the goal: {goal}")
        
        # 2. Plan actions to achieve the goal
        plan_prompt = f"""
        Based on what you see on the screen, create a step-by-step plan to achieve this goal: {goal}
        
        For each step, specify:
        1. What action to take (look, click, type, run command)
        2. Exact parameters for the action (coordinates, text, command)
        3. What you expect to happen after the action
        
        Format your response as a structured list of steps.
        """
        
        plan = self.analyze_screen(plan_prompt)
        
        # 3. Execute the plan (simplified version - in production this would parse the plan more carefully)
        result = {
            "goal": goal,
            "initial_analysis": screen_analysis,
            "plan": plan,
            "execution": []
        }
        
        # This is where the actual step execution would happen
        # For safety, we're just logging that we would execute the plan
        logger.info(f"Would execute plan for goal: {goal}")
        
        return result

def main():
    """Main function to run the Claude Computer Use agent."""
    # Check dependencies first
    check_dependencies()
    
    parser = argparse.ArgumentParser(description="Claude Computer Use - Meta Orchestrator Agent")
    parser.add_argument("--goal", type=str, help="Goal to achieve")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze the screen without taking actions")
    args = parser.parse_args()
    
    try:
        agent = ClaudeComputerUse()
        
        if args.analyze_only:
            screenshot = agent.capture_screenshot()
            analysis = agent.analyze_screen("What do you see on the screen? Describe the current state of the applications, windows, and any visible content.")
            print(json.dumps(analysis, indent=2))
        elif args.goal:
            result = agent.execute_workflow(args.goal)
            print(json.dumps(result, indent=2))
        else:
            print("Interactive mode:")
            while True:
                command = input("\nEnter command (screenshot, analyze, task, activity, quit): ")
                
                if command == "quit":
                    break
                elif command == "screenshot":
                    agent.capture_screenshot()
                    print("Screenshot captured")
                elif command == "analyze":
                    prompt = input("Enter analysis prompt: ")
                    analysis = agent.analyze_screen(prompt)
                    print(analysis["text"])
                elif command == "task":
                    task = input("Enter task description: ")
                    result = agent.coordinate_with_agents(task)
                    print(result)
                elif command == "activity":
                    duration = int(input("Enter monitoring duration (seconds): "))
                    activity = agent.view_agent_activity(duration)
                    print(activity)
                else:
                    print("Unknown command")
    
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 