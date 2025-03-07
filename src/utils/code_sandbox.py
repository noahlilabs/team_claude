#!/usr/bin/env python3
"""
Code Sandbox

This module provides a secure sandbox for executing untrusted code generated
by agents, with resource limitations and security boundaries.
"""

import os
import sys
import json
import time
import uuid
import signal
import resource
import tempfile
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import traceback
import ast

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.structured_logger import get_logger

# Set up logger
logger = get_logger("CodeSandbox", log_dir="logs")

# Security constants
DEFAULT_TIMEOUT = 10  # seconds
MAX_MEMORY = 1024 * 1024 * 512  # 512MB
MAX_CPU_TIME = 5  # seconds
FORBIDDEN_IMPORTS = [
    "os.system", "subprocess", "socket", "requests", 
    "shutil", "pickle", "marshal", "__import__"
]


class CodeValidator:
    """Validates code before execution to prevent security risks."""
    
    @staticmethod
    def validate_python(code: str) -> Tuple[bool, str]:
        """
        Validate Python code for security issues.
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Parse the AST to check for prohibited constructs
            tree = ast.parse(code)
            
            # Create a visitor to check imports and calls
            for node in ast.walk(tree):
                # Check for imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for name in node.names:
                        module_name = name.name
                        for forbidden in FORBIDDEN_IMPORTS:
                            if module_name == forbidden or module_name.startswith(forbidden + "."):
                                return False, f"Prohibited import: {module_name}"
                
                # Check for exec or eval calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ["exec", "eval"]:
                            return False, f"Prohibited function call: {node.func.id}"
                
                # Check for attribute access that might be dangerous
                if isinstance(node, ast.Attribute):
                    full_name = ""
                    if isinstance(node.value, ast.Name):
                        full_name = f"{node.value.id}.{node.attr}"
                    
                    for forbidden in FORBIDDEN_IMPORTS:
                        if full_name == forbidden or full_name.startswith(forbidden + "."):
                            return False, f"Prohibited attribute access: {full_name}"
            
            # Code passed validation
            return True, "Code validation passed"
            
        except SyntaxError as e:
            return False, f"Invalid Python syntax: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"


class CodeSandbox:
    """
    Provides a secure environment for executing untrusted code.
    """
    
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_memory: int = MAX_MEMORY,
        max_cpu_time: int = MAX_CPU_TIME,
    ):
        """
        Initialize code sandbox.
        
        Args:
            timeout: Maximum execution time in seconds
            max_memory: Maximum memory usage in bytes
            max_cpu_time: Maximum CPU time in seconds
        """
        self.timeout = timeout
        self.max_memory = max_memory
        self.max_cpu_time = max_cpu_time
        logger.info("Code sandbox initialized", {
            "timeout": timeout,
            "max_memory": max_memory,
            "max_cpu_time": max_cpu_time
        })
    
    def execute_python(
        self, 
        code: str, 
        input_data: Optional[Dict[str, Any]] = None,
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute Python code in a sandbox.
        
        Args:
            code: Python code to execute
            input_data: Optional dictionary of input data for the code
            save_path: Optional path to save the code before execution
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        result = {
            "success": False,
            "output": "",
            "error": "",
            "execution_time": 0,
            "exit_code": None
        }
        
        # Validate code before execution
        is_valid, reason = CodeValidator.validate_python(code)
        if not is_valid:
            result["error"] = f"Code validation failed: {reason}"
            logger.warning("Code validation failed", {
                "reason": reason,
                "code_length": len(code)
            })
            return result
        
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file_path = temp_file.name
            
            # Add input data handling
            full_code = []
            full_code.append("import json, sys, os")
            full_code.append("import resource")
            full_code.append("import traceback")
            
            # Set resource limits
            full_code.append("# Set resource limits")
            full_code.append(f"resource.setrlimit(resource.RLIMIT_AS, ({self.max_memory}, {self.max_memory}))")
            full_code.append(f"resource.setrlimit(resource.RLIMIT_CPU, ({self.max_cpu_time}, {self.max_cpu_time}))")
            
            # Add input data
            if input_data:
                full_code.append(f"input_data = {json.dumps(input_data)}")
            else:
                full_code.append("input_data = {}")
            
            # Redirect stdout and stderr to capture output
            full_code.append("import io")
            full_code.append("sys.stdout = io.StringIO()")
            full_code.append("sys.stderr = io.StringIO()")
            
            # Add the user code wrapped in a try/except
            full_code.append("try:")
            for line in code.split("\n"):
                full_code.append(f"    {line}")
            
            # Capture the output
            full_code.append("except Exception as e:")
            full_code.append("    print('ERROR:', e)")
            full_code.append("    traceback.print_exc()")
            
            # Write outputs to files
            full_code.append("output = sys.stdout.getvalue()")
            full_code.append("error = sys.stderr.getvalue()")
            full_code.append("with open('output.txt', 'w') as f:")
            full_code.append("    f.write(output)")
            full_code.append("with open('error.txt', 'w') as f:")
            full_code.append("    f.write(error)")
            
            # Write the code to the temporary file
            temp_file.write("\n".join(full_code))
        
        # Save code to the specified path if requested
        if save_path:
            try:
                with open(save_path, 'w') as save_file:
                    save_file.write(code)
                logger.info(f"Saved code to {save_path}")
            except Exception as e:
                logger.error(f"Failed to save code to {save_path}", e)
        
        # Create output and error files
        output_file = os.path.join(os.path.dirname(temp_file_path), "output.txt")
        error_file = os.path.join(os.path.dirname(temp_file_path), "error.txt")
        
        try:
            # Execute the code in a subprocess with timeout
            process = subprocess.Popen(
                [sys.executable, temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            try:
                # Wait for the process to complete with timeout
                exit_code = process.wait(timeout=self.timeout)
                
                # Read output files
                try:
                    with open(output_file, 'r') as f:
                        result["output"] = f.read()
                except FileNotFoundError:
                    result["output"] = "<output capture failed>"
                
                try:
                    with open(error_file, 'r') as f:
                        result["error"] = f.read()
                except FileNotFoundError:
                    pass
                
                result["exit_code"] = exit_code
                result["success"] = exit_code == 0 and not result["error"]
                
            except subprocess.TimeoutExpired:
                process.kill()
                result["error"] = f"Execution timed out after {self.timeout} seconds"
                logger.warning("Code execution timed out", {
                    "timeout": self.timeout,
                    "code_length": len(code)
                })
        
        except Exception as e:
            result["error"] = f"Execution error: {str(e)}"
            logger.error("Code execution failed", {
                "error": str(e), 
                "traceback": traceback.format_exc()
            })
            
        finally:
            # Clean up
            try:
                os.unlink(temp_file_path)
                if os.path.exists(output_file):
                    os.unlink(output_file)
                if os.path.exists(error_file):
                    os.unlink(error_file)
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        
        # Calculate execution time
        result["execution_time"] = time.time() - start_time
        
        logger.info("Code execution completed", {
            "success": result["success"],
            "execution_time": result["execution_time"],
            "exit_code": result["exit_code"]
        })
        
        return result
    
    def execute_js(
        self, 
        code: str, 
        input_data: Optional[Dict[str, Any]] = None,
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute JavaScript code in a sandbox using Node.js.
        
        Args:
            code: JavaScript code to execute
            input_data: Optional dictionary of input data
            save_path: Optional path to save the code
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        result = {
            "success": False,
            "output": "",
            "error": "",
            "execution_time": 0,
            "exit_code": None
        }
        
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp_file:
            temp_file_path = temp_file.name
            
            # Prepare the code with input data and safety measures
            full_code = []
            
            # Add safety timeout
            full_code.append(`// Safety timeout
setTimeout(() => {
  console.error('Execution timed out');
  process.exit(1);
}, ${self.timeout * 1000});`)
            
            # Add input data
            if input_data:
                full_code.append(f"const input_data = {json.dumps(input_data)};")
            else:
                full_code.append("const input_data = {};")
            
            # Add the actual code
            full_code.append(code)
            
            # Write to the file
            temp_file.write("\n".join(full_code))
        
        # Save code to the specified path if requested
        if save_path:
            try:
                with open(save_path, 'w') as save_file:
                    save_file.write(code)
                logger.info(f"Saved code to {save_path}")
            except Exception as e:
                logger.error(f"Failed to save code to {save_path}", e)
        
        try:
            # Execute the code using Node.js
            process = subprocess.Popen(
                ["node", temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            try:
                # Wait for the process with timeout
                stdout, stderr = process.communicate(timeout=self.timeout)
                result["output"] = stdout
                result["error"] = stderr
                result["exit_code"] = process.returncode
                result["success"] = process.returncode == 0 and not stderr
                
            except subprocess.TimeoutExpired:
                process.kill()
                result["error"] = f"Execution timed out after {self.timeout} seconds"
                logger.warning("JavaScript execution timed out", {
                    "timeout": self.timeout,
                    "code_length": len(code)
                })
        
        except Exception as e:
            result["error"] = f"Execution error: {str(e)}"
            logger.error("JavaScript execution failed", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            
        finally:
            # Clean up
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        
        # Calculate execution time
        result["execution_time"] = time.time() - start_time
        
        logger.info("JavaScript execution completed", {
            "success": result["success"],
            "execution_time": result["execution_time"],
            "exit_code": result["exit_code"]
        })
        
        return result


# Example usage
if __name__ == "__main__":
    # Create a sandbox
    sandbox = CodeSandbox()
    
    # Example Python code to execute
    python_code = """
def add(a, b):
    return a + b

# Use input data
result = add(input_data.get('a', 0), input_data.get('b', 0))
print(f"The result is: {result}")
"""
    
    # Execute the code
    result = sandbox.execute_python(
        python_code, 
        input_data={'a': 5, 'b': 10}
    )
    
    print("Execution result:")
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    print(f"Error: {result['error']}")
    print(f"Execution time: {result['execution_time']:.4f} seconds")