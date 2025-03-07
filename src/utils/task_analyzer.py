#!/usr/bin/env python3
"""
Task Analyzer

This script analyzes task descriptions to identify the task type and suggest
appropriate subtask breakdowns for specialized task types.

Usage:
    python3 task_analyzer.py <task_id> "<task_description>"
"""

import re
import sys
import os
import json

# Define patterns for different types of tasks
TASK_PATTERNS = {
    "self_enhancement": [
        r'self.?enhancement',
        r'enhanc(e|ing).*capabilit(y|ies)',
        r'creat(e|ing) tool(s| kit)?',
        r'tool(s| kit)? (for|to) enhance',
        r'search.*internet',
        r'web search',
        r'coding sandbox',
        r'web brows(er|ing)',
        r'browse.*web',
        r'internet.*tool',
        r'internet.*search',
        r'search.*web',
        r'way to search',  # Very specific to our use case
        r'coding test',
        r'run coding',
        r'deploy.*main file',
        r'browser.*internet',
        r'way to browser',  # Common typo in our use case
    ],
    "data_analysis": [
        r'data analysis',
        r'analyze.*data',
        r'process.*dataset',
        r'dashboard',
        r'visualiz(e|ation)',
        r'statistic(s|al)'
    ],
    "frontend_development": [
        r'frontend',
        r'ui',
        r'user interface',
        r'web.*design',
        r'css',
        r'html',
        r'react',
        r'vue',
        r'angular'
    ],
    "backend_development": [
        r'backend',
        r'server',
        r'api',
        r'database',
        r'endpoint',
        r'rest',
        r'graphql'
    ]
}

# Define subtask templates for different task types
SUBTASK_TEMPLATES = {
    "self_enhancement": [
        {
            "description": "Develop a web search tool that allows Claude to search the internet for up-to-date information using search APIs",
            "agent": "agent3",
            "capabilities": "api,python,integration"
        },
        {
            "description": "Create a code sandbox environment that allows Claude to test code before deploying it to main files, including execution and validation features",
            "agent": "agent3",
            "capabilities": "python,api"
        },
        {
            "description": "Implement a web browsing interface that allows Claude to navigate websites, extract content, and interact with web pages",
            "agent": "agent2",
            "capabilities": "javascript,visualization"
        },
        {
            "description": "Create a unified user interface that integrates all enhancement tools with a clean, intuitive frontend",
            "agent": "agent1",
            "capabilities": "css,javascript"
        }
    ],
    "data_analysis": [
        {
            "description": "Load and clean the dataset, handling missing values and outliers",
            "agent": "agent2",
            "capabilities": "python,data_processing"
        },
        {
            "description": "Perform exploratory data analysis and generate statistical insights",
            "agent": "agent3",
            "capabilities": "python,analytics"
        },
        {
            "description": "Create data visualizations and charts to represent key findings",
            "agent": "agent1",
            "capabilities": "visualization,javascript"
        },
        {
            "description": "Prepare final report with insights and recommendations based on the analysis",
            "agent": "team_lead",
            "capabilities": "analytics,documentation"
        }
    ],
    "frontend_development": [
        {
            "description": "Design UI mockups and layout for the application",
            "agent": "agent1",
            "capabilities": "design,css"
        },
        {
            "description": "Implement core UI components and responsive design",
            "agent": "agent2",
            "capabilities": "javascript,css"
        },
        {
            "description": "Create client-side logic and data handling",
            "agent": "agent3",
            "capabilities": "javascript,api"
        }
    ],
    "backend_development": [
        {
            "description": "Design database schema and data models",
            "agent": "agent2",
            "capabilities": "database,python"
        },
        {
            "description": "Implement API endpoints and server logic",
            "agent": "agent3",
            "capabilities": "api,python"
        },
        {
            "description": "Create authentication and authorization system",
            "agent": "agent1",
            "capabilities": "security,api"
        }
    ]
}

class TaskAnalyzer:
    """Analyzes task descriptions and suggests appropriate subtask breakdowns."""
    
    def __init__(self, task_id, task_description):
        """Initialize with task ID and description."""
        self.task_id = task_id
        self.task_description = task_description
    
    def analyze_task(self):
        """
        Analyze the task description to determine its type and suggested subtasks.
        
        Returns:
            dict: Analysis results including task type and suggested subtasks
        """
        # Convert task description to lowercase for easier pattern matching
        task_lower = self.task_description.lower()
        
        # First check for explicit indicators of self-enhancement
        if ('enhance' in task_lower and ('capabilities' in task_lower or 'ability' in task_lower)) or \
           ('search' in task_lower and 'internet' in task_lower) or \
           ('coding' in task_lower and ('sandbox' in task_lower or 'test' in task_lower)) or \
           ('browser' in task_lower and 'internet' in task_lower):
            task_type = "self_enhancement"
        else:
            # Identify the task type using pattern matching
            task_type = self._identify_task_type(task_lower)
        
        # Get suggested subtasks based on the identified type
        subtasks = self._get_suggested_breakdown(task_type)
        
        # Generate breakdown commands
        commands = self.generate_breakdown_commands(subtasks)
        
        return {
            "task_id": self.task_id,
            "task_type": task_type,
            "subtasks": subtasks,
            "commands": commands
        }
    
    def _identify_task_type(self, task_lower):
        """
        Identify the type of task based on patterns in the description.
        
        Args:
            task_lower (str): Lowercase task description
            
        Returns:
            str: Identified task type or "general" if no specific type is identified
        """
        # Count matches for each task type
        type_scores = {}
        
        for task_type, patterns in TASK_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, task_lower):
                    # Prioritize self_enhancement patterns with a higher score
                    if task_type == "self_enhancement":
                        score += 2  # Double weight for self_enhancement matches
                    else:
                        score += 1
            
            type_scores[task_type] = score
        
        # Find the task type with the highest score
        if any(type_scores.values()):
            best_type = max(type_scores.items(), key=lambda x: x[1])
            if best_type[1] > 0:  # If there's at least one match
                return best_type[0]
        
        # If no specific type is identified
        return "general"
    
    def _get_suggested_breakdown(self, task_type):
        """
        Get suggested subtasks for the identified task type.
        
        Args:
            task_type (str): The identified task type
            
        Returns:
            list: List of subtask templates, or empty list if no templates exist
        """
        if task_type in SUBTASK_TEMPLATES:
            return SUBTASK_TEMPLATES[task_type]
        return []
    
    def generate_breakdown_commands(self, subtasks):
        """
        Generate commands to create subtasks.
        
        Args:
            subtasks (list): List of subtask templates
            
        Returns:
            list: Commands to create the subtasks
        """
        commands = []
        for subtask in subtasks:
            cmd = f"python3 $REPO_ROOT/src/cli/state_cli.py create_subtask \"{self.task_id}\" \"{subtask['description']}\" \"{subtask['agent']}\" --capabilities \"{subtask['capabilities']}\""
            commands.append(cmd)
        return commands

def main():
    """Main function to analyze a task from command line arguments."""
    if len(sys.argv) < 3:
        print("Usage: python3 task_analyzer.py <task_id> \"<task_description>\"")
        sys.exit(1)
    
    task_id = sys.argv[1]
    task_description = sys.argv[2]
    
    analyzer = TaskAnalyzer(task_id, task_description)
    analysis = analyzer.analyze_task()
    
    # Print analysis results
    print(f"Task Type: {analysis['task_type']}")
    print(f"Number of suggested subtasks: {len(analysis['subtasks'])}")
    
    if analysis['subtasks']:
        print("\nSuggested Subtasks:")
        for i, subtask in enumerate(analysis['subtasks'], 1):
            print(f"{i}. {subtask['description']} (Agent: {subtask['agent']}, Capabilities: {subtask['capabilities']})")
        
        print("\nBreakdown Commands:")
        for cmd in analysis['commands']:
            print(cmd)

if __name__ == "__main__":
    main() 