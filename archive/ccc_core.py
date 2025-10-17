"""
Core utilities and shared functionality for the CCC automation system.

This module contains common functions used by both run_level.py and process_level.py
to eliminate code duplication and improve maintainability.
"""

import os
import sys
import subprocess
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
import importlib.util

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class CCCCore:
    """Core class for CCC automation system."""
    
    def __init__(self, level_number: int):
        self.level_number = level_number
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary directories."""
        self.directories = {
            'inputs': Path("Inputs"),
            'outputs': Path("Outputs"), 
            'infos': Path("infos"),
            'prompts': Path("prompts"),
            'levels': Path("levels")
        }
        
        for directory in self.directories.values():
            directory.mkdir(exist_ok=True)
    
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with formatting."""
        symbols = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️", 
            "ERROR": "❌",
            "STEP": "📋"
        }
        symbol = symbols.get(level, "•")
        print(f"{symbol} {message}")
    
    def print_header(self, title: str, width: int = 60):
        """Print formatted header."""
        print(f"\n{'=' * width}")
        print(f"{title}")
        print(f"{'=' * width}")
    
    def print_separator(self, width: int = 60):
        """Print separator line."""
        print(f"{'-' * width}")
    
    def clear_folder(self, folder_path: Path, description: str = "folder"):
        """Clear all files from a folder."""
        if folder_path.exists():
            files_removed = 0
            for file in folder_path.glob("*"):
                if file.is_file():
                    file.unlink()
                    files_removed += 1
            if files_removed > 0:
                self.log(f"Cleared {files_removed} files from {description}")
    
    def find_zip_file(self) -> Optional[Path]:
        """Find the level zip file in Downloads or current directory."""
        zip_filename = f"level{self.level_number}.zip"
        
        # Check Downloads folder first
        downloads_path = Path.home() / "Downloads" / zip_filename
        if downloads_path.exists():
            self.log(f"Found {zip_filename} in Downloads folder")
            return downloads_path
        
        # Check current directory
        current_path = Path(zip_filename)
        if current_path.exists():
            self.log(f"Found {zip_filename} in current directory")
            return current_path
        
        self.log(f"ZIP file {zip_filename} not found", "ERROR")
        return None
    
    def extract_zip(self) -> bool:
        """Extract the level zip file."""
        zip_path = self.find_zip_file()
        if not zip_path:
            return False
        
        self.log(f"Extracting {zip_path.name}...")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.directories['infos'])
            self.log("ZIP file extracted successfully", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Error extracting ZIP: {e}", "ERROR")
            return False
    
    def find_pdf_file(self) -> Optional[Path]:
        """Find the PDF file with various naming patterns."""
        pdf_patterns = [
            f"Level {self.level_number}.pdf",
            f"level{self.level_number}.pdf", 
            f"Level{self.level_number}.pdf",
            f"level {self.level_number}.pdf"
        ]
        
        # Check Downloads folder first
        downloads_path = Path.home() / "Downloads"
        for pattern in pdf_patterns:
            potential_file = downloads_path / pattern
            if potential_file.exists():
                self.log(f"Found PDF in Downloads: {potential_file.name}")
                return potential_file
        
        # Check infos folder
        for pattern in pdf_patterns:
            potential_file = self.directories['infos'] / pattern
            if potential_file.exists():
                self.log(f"Found PDF in infos: {potential_file.name}")
                return potential_file
        
        # Look for any PDF in infos
        pdf_files = list(self.directories['infos'].glob("*.pdf"))
        if pdf_files:
            self.log(f"Found PDF: {pdf_files[0].name}")
            return pdf_files[0]
        
        return None
    
    def extract_pdf_text(self) -> Optional[str]:
        """Extract text from PDF and create AI prompt."""
        if not PDF_AVAILABLE:
            self.log("pdfplumber not installed - skipping PDF extraction", "WARNING")
            return None
        
        pdf_file = self.find_pdf_file()
        if not pdf_file:
            self.log("No PDF file found", "WARNING")
            return None
        
        try:
            full_text = ""
            with pdfplumber.open(pdf_file) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        full_text += f"\n--- Page {i+1} ---\n{text}\n"
            
            self.log(f"Extracted text from {pdf_file.name} ({len(full_text)} characters)", "SUCCESS")
            return full_text
        
        except Exception as e:
            self.log(f"Error extracting PDF text: {e}", "ERROR")
            return None
    
    def create_ai_prompt(self, pdf_text: str) -> str:
        """Create AI prompt from PDF text."""
        prompt = f"""# Coding Challenge - Level {self.level_number}

## Problem Description (from PDF):

{pdf_text}

## Task:
Create a Python solution that:
1. Reads input files from the Inputs/ folder
2. Processes each input according to the problem description
3. Writes output files to the Outputs/ folder with the same name but .out extension

## Input Files:
- Located in: Inputs/
- Format: level{self.level_number}_*.in

## Output Files:
- Should be written to: Outputs/
- Format: level{self.level_number}_*.out

## Example Structure:
```python
from pathlib import Path

def solve(input_data):
    # Your solution logic here
    pass

def main():
    input_folder = Path("Inputs")
    output_folder = Path("Outputs")
    output_folder.mkdir(exist_ok=True)
    
    for input_file in sorted(input_folder.glob("level{self.level_number}_*.in")):
        with open(input_file, 'r') as f:
            data = f.read().strip()
        
        result = solve(data)
        
        output_file = output_folder / input_file.name.replace('.in', '.out')
        with open(output_file, 'w') as f:
            f.write(str(result))

if __name__ == "__main__":
    main()
```

Please provide a complete Python solution for this problem.

The file should be named: level{self.level_number}.py
"""
        
        # Save prompt to file
        prompt_file = self.directories['prompts'] / f"level{self.level_number}_prompt.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        self.log(f"AI prompt saved to: {prompt_file}", "SUCCESS")
        return prompt
    
    def organize_files(self) -> Tuple[int, int]:
        """Move .in files to Inputs/ and .out files to Outputs/."""
        self.log("Organizing files...")
        
        # Move .in files to Inputs/
        in_files = list(self.directories['infos'].glob("*.in"))
        for in_file in in_files:
            dest = self.directories['inputs'] / in_file.name
            shutil.move(str(in_file), str(dest))
            self.log(f"Moved {in_file.name} -> Inputs/")
        
        # Move example .out files to Outputs/
        example_out_files = list(self.directories['infos'].glob("*example*.out"))
        for out_file in example_out_files:
            dest = self.directories['outputs'] / out_file.name
            shutil.move(str(out_file), str(dest))
            self.log(f"Moved {out_file.name} -> Outputs/")
        
        self.log(f"Organized {len(in_files)} input files and {len(example_out_files)} example output files", "SUCCESS")
        return len(in_files), len(example_out_files)
    
    def run_python_script(self, script_path: Path, capture_output: bool = False) -> int:
        """Run a Python script and return exit code."""
        try:
            result = subprocess.run([sys.executable, str(script_path)], 
                                  capture_output=capture_output)
            return result.returncode
        except Exception as e:
            self.log(f"Error running {script_path}: {e}", "ERROR")
            return 1
    
    def find_level_script(self) -> Optional[Path]:
        """Find the level solution script."""
        script_name = f"level{self.level_number}.py"
        
        # Check in current directory first
        current_path = Path(script_name)
        if current_path.exists():
            return current_path
        
        # Check in levels directory
        levels_path = self.directories['levels'] / script_name
        if levels_path.exists():
            return levels_path
        
        return None
    
    def count_output_files(self) -> int:
        """Count .out files in Outputs/ folder."""
        out_files = list(self.directories['outputs'].glob("*.out"))
        return len(out_files)
    
    def cleanup_infos(self):
        """Clean up the infos/ folder."""
        self.log("Cleaning up infos/ folder...")
        files_removed = 0
        
        for file in self.directories['infos'].glob("*"):
            if file.is_file():
                file.unlink()
                files_removed += 1
        
        if files_removed > 0:
            self.log(f"Cleaned up {files_removed} files from infos/", "SUCCESS")
    
    def get_prompt_file_path(self) -> Path:
        """Get the path to the AI prompt file."""
        return self.directories['prompts'] / f"level{self.level_number}_prompt.txt"


def validate_level_number(level_str: str) -> int:
    """Validate and convert level number string to integer."""
    try:
        return int(level_str)
    except ValueError:
        print(f"❌ Error: '{level_str}' is not a valid integer")
        sys.exit(1)


def check_python_dependencies():
    """Check if required Python packages are installed."""
    missing_packages = []
    
    if not PDF_AVAILABLE:
        missing_packages.append("pdfplumber")
    
    if missing_packages:
        print("⚠️  Missing optional dependencies:")
        for package in missing_packages:
            print(f"   pip install {package}")
        print()