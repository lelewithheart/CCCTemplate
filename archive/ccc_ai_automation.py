"""
AI Automation System for CCC - Automatically generate solutions using AI.

This module provides automated AI-assisted solution generation by:
1. Sending prompts to GitHub Copilot Chat via VS Code API
2. Processing AI responses to generate solution files
3. Validating and testing generated solutions
"""

import os
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from ccc_core import CCCCore


class AIAutomation:
    """AI automation system for generating coding contest solutions."""
    
    def __init__(self, core: CCCCore):
        self.core = core
        self.level_number = core.level_number
        
    def generate_solution(self) -> bool:
        """
        Generate a solution using AI automation.
        
        Returns:
            True if solution was generated successfully, False otherwise
        """
        self.core.log("Starting AI-assisted solution generation...", "STEP")
        
        # Get the AI prompt
        prompt_file = self.core.get_prompt_file_path()
        if not prompt_file.exists():
            self.core.log("AI prompt file not found", "ERROR")
            return False
        
        # Read the prompt
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_text = f.read()
        
        # Try different AI automation methods
        methods = [
            self._try_vscode_copilot_api,
            self._try_copilot_cli,
            self._try_direct_ai_request,
            self._try_template_generation
        ]
        
        for method in methods:
            self.core.log(f"Trying method: {method.__name__.replace('_try_', '').replace('_', ' ').title()}")
            
            try:
                if method(prompt_text):
                    return True
            except Exception as e:
                self.core.log(f"Method failed: {e}", "WARNING")
                continue
        
        self.core.log("All AI automation methods failed", "ERROR")
        return False
    
    def _try_vscode_copilot_api(self, prompt: str) -> bool:
        """Try to use VS Code Copilot API directly."""
        try:
            # Create a temporary file with the prompt
            temp_prompt_file = Path("temp_ai_request.md")
            
            with open(temp_prompt_file, 'w', encoding='utf-8') as f:
                f.write(f"""# AI Request for Level {self.level_number}

Please generate a complete Python solution for this coding challenge.

{prompt}

## Requirements:
- Save the solution as `level{self.level_number}.py`
- Make sure it reads from Inputs/ and writes to Outputs/
- Follow the exact format specified in the prompt
- Include error handling and proper file I/O
""")
            
            self.core.log(f"Created AI request file: {temp_prompt_file}")
            self.core.log("Please copy the content to GitHub Copilot Chat to generate the solution")
            
            # Wait for user to process the AI request
            print(f"\n{'='*60}")
            print("🤖 AI AUTOMATION - MANUAL STEP REQUIRED")
            print(f"{'='*60}")
            print(f"1. Open the file: {temp_prompt_file}")
            print("2. Copy the entire content")  
            print("3. Paste it into GitHub Copilot Chat")
            print(f"4. Save the generated solution as: level{self.level_number}.py")
            print("5. Press ENTER when the solution file is ready...")
            
            input()
            
            # Check if solution was created
            solution_path = self.core.find_level_script()
            if solution_path and solution_path.exists():
                self.core.log(f"Solution file found: {solution_path}", "SUCCESS")
                
                # Clean up temp file
                if temp_prompt_file.exists():
                    temp_prompt_file.unlink()
                
                return True
            else:
                self.core.log("Solution file not found after AI request", "WARNING")
                return False
                
        except Exception as e:
            self.core.log(f"VS Code Copilot API method failed: {e}", "ERROR")
            return False
    
    def _try_copilot_cli(self, prompt: str) -> bool:
        """Try to use GitHub Copilot CLI if available."""
        try:
            # Check if gh copilot is available
            result = subprocess.run(['gh', 'copilot', '--version'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                self.core.log("GitHub Copilot CLI not available", "WARNING")
                return False
            
            self.core.log("Using GitHub Copilot CLI...")
            
            # Create prompt file for CLI
            cli_prompt = f"""Generate a Python solution for this coding challenge:

{prompt}

Requirements:
- Read input files from Inputs/ folder
- Write output files to Outputs/ folder  
- Handle multiple input files with pattern level{self.level_number}_*.in
- Generate corresponding .out files
"""
            
            # Use copilot CLI to generate code
            cmd = ['gh', 'copilot', 'suggest', '-t', 'shell', cli_prompt]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                solution_code = result.stdout
                return self._save_and_validate_solution(solution_code)
            else:
                self.core.log("Copilot CLI request failed", "WARNING")
                return False
                
        except FileNotFoundError:
            self.core.log("GitHub CLI not installed", "WARNING")
            return False
        except Exception as e:
            self.core.log(f"Copilot CLI method failed: {e}", "ERROR")
            return False
    
    def _try_direct_ai_request(self, prompt: str) -> bool:
        """Try to make a direct AI request (placeholder for future API integration)."""
        self.core.log("Direct AI request method not implemented yet", "WARNING")
        return False
    
    def _try_template_generation(self, prompt: str) -> bool:
        """Generate a solution template based on the prompt analysis."""
        try:
            self.core.log("Generating solution template...")
            
            # Analyze prompt to extract key information
            template_info = self._analyze_prompt(prompt)
            
            # Generate template code
            solution_code = self._generate_template_code(template_info)
            
            # Save the template
            solution_path = Path(f"level{self.level_number}.py")
            with open(solution_path, 'w', encoding='utf-8') as f:
                f.write(solution_code)
            
            self.core.log(f"Generated solution template: {solution_path}", "SUCCESS")
            self.core.log("⚠️  Template generated - you may need to implement the solve() function", "WARNING")
            
            return True
            
        except Exception as e:
            self.core.log(f"Template generation failed: {e}", "ERROR")
            return False
    
    def _analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze the prompt to extract key information for template generation."""
        # Basic analysis - in a real implementation this could be more sophisticated
        info = {
            'has_multiple_inputs': 'multiple' in prompt.lower() or 'each' in prompt.lower(),
            'input_format': 'text',  # Default assumption
            'output_format': 'text', # Default assumption
            'level_number': self.level_number
        }
        
        # Try to detect input/output patterns
        if 'integer' in prompt.lower() or 'number' in prompt.lower():
            info['input_format'] = 'numbers'
        
        if 'line' in prompt.lower():
            info['line_based'] = True
        
        return info
    
    def _generate_template_code(self, info: Dict[str, Any]) -> str:
        """Generate template code based on analyzed prompt information."""
        template = f'''"""
Solution for Level {info["level_number"]} - Auto-generated template

TODO: Implement the solve() function based on the problem requirements.
"""

from pathlib import Path


def solve(input_data):
    """
    Solve the problem for given input data.
    
    Args:
        input_data (str): The input data as a string
        
    Returns:
        str: The solution output
    """
    # TODO: Implement your solution logic here
    lines = input_data.strip().split('\\n')
    
    # Example processing - replace with actual logic
    result = "0"  # Placeholder result
    
    return result


def main():
    """Main function to process all input files."""
    input_folder = Path("Inputs")
    output_folder = Path("Outputs")
    output_folder.mkdir(exist_ok=True)
    
    # Find all input files for this level
    pattern = f"level{info["level_number"]}_*.in"
    input_files = sorted(input_folder.glob(pattern))
    
    if not input_files:
        print(f"No input files found matching pattern: {{pattern}}")
        return
    
    print(f"Processing {{len(input_files)}} input files...")
    
    for input_file in input_files:
        print(f"Processing {{input_file.name}}...")
        
        # Read input
        with open(input_file, 'r', encoding='utf-8') as f:
            input_data = f.read().strip()
        
        # Solve the problem
        result = solve(input_data)
        
        # Write output
        output_file = output_folder / input_file.name.replace('.in', '.out')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(result))
        
        print(f"Generated {{output_file.name}}")
    
    print("All input files processed successfully!")


if __name__ == "__main__":
    main()
'''
        return template
    
    def _save_and_validate_solution(self, solution_code: str) -> bool:
        """Save and validate the generated solution code."""
        try:
            solution_path = Path(f"level{self.level_number}.py")
            
            with open(solution_path, 'w', encoding='utf-8') as f:
                f.write(solution_code)
            
            # Basic validation - check if it's valid Python
            try:
                compile(solution_code, str(solution_path), 'exec')
                self.core.log(f"Generated valid Python solution: {solution_path}", "SUCCESS")
                return True
            except SyntaxError as e:
                self.core.log(f"Generated code has syntax errors: {e}", "ERROR")
                return False
                
        except Exception as e:
            self.core.log(f"Failed to save solution: {e}", "ERROR")
            return False


def create_ai_workflow_file(level_number: int, core: CCCCore):
    """Create a workflow file for manual AI assistance."""
    workflow_file = Path(f"level{level_number}_ai_workflow.md")
    
    prompt_file = core.get_prompt_file_path()
    
    workflow_content = f"""# Level {level_number} - AI Workflow

## Step 1: Copy the Prompt
Copy the content from: `{prompt_file}`

## Step 2: Send to AI
Paste the prompt into:
- GitHub Copilot Chat in VS Code
- ChatGPT, Claude, or your preferred AI
- Any coding assistant

## Step 3: Generate Solution  
Ask the AI to:
1. Generate a complete Python solution
2. Save it as `level{level_number}.py`
3. Make sure it reads from `Inputs/` and writes to `Outputs/`

## Step 4: Test
Run: `python level{level_number}.py`

## Step 5: Continue Automation
Run: `python run_level.py {level_number}` to complete the process

---
*This workflow was auto-generated by CCC AI Automation*
"""
    
    with open(workflow_file, 'w', encoding='utf-8') as f:
        f.write(workflow_content)
    
    core.log(f"Created AI workflow guide: {workflow_file}", "SUCCESS")
    return workflow_file