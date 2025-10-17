"""
Optimized CCC Level Processor - Extract, organize and prepare level files.

Usage:
    python general/process_level.py <level_number>
    
Example:
    python general/process_level.py 1

This script will:
1. Extract level{LevelNumber}.zip from Downloads folder (or current directory)
2. Extract text from Level {LevelNumber}.pdf and create AI prompt
3. Move .in files to Inputs/ folder
4. Move example .out files to Outputs/ folder
5. Optionally run level{LevelNumber}.py to generate output files
6. Clean up: delete all files from infos/
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import ccc_core
sys.path.append(str(Path(__file__).parent.parent))
from ccc_core import CCCCore, validate_level_number, check_python_dependencies


def extract_zip(level_number, zip_path=None):
    """Extract the level zip file to infos/ folder."""
    if zip_path is None:
        # Try multiple locations for the zip file
        zip_filename = f"level{level_number}.zip"
        
        # Check in Downloads folder first
        downloads_path = Path.home() / "Downloads" / zip_filename
        if downloads_path.exists():
            zip_path = str(downloads_path)
            print(f"Found {zip_filename} in Downloads folder")
        # Check in current directory
        elif os.path.exists(zip_filename):
            zip_path = zip_filename
        else:
            print(f"Error: {zip_filename} not found in Downloads or current directory!")
            print(f"  Checked: {downloads_path}")
            print(f"  Checked: {os.path.abspath(zip_filename)}")
            return False
    
    if not os.path.exists(zip_path):
        print(f"Error: {zip_path} not found!")
        return False
    
    print(f"Extracting {zip_path}...")
    
    # Create infos folder if it doesn't exist
    os.makedirs("infos", exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall("infos")
    
    print(f"✓ Extracted to infos/")
    return True


def extract_pdf_text(level_number):
    """Extract text from Level X.pdf and create AI prompt."""
    if not PDF_AVAILABLE:
        print("\n⚠ Skipping PDF extraction (pdfplumber not installed)")
        return None
    
    print("\nExtracting text from PDF...")
    
    # Look for PDF file with various naming patterns
    pdf_patterns = [
        f"Level {level_number}.pdf",
        f"level{level_number}.pdf",
        f"Level{level_number}.pdf",
        f"level {level_number}.pdf"
    ]
    
    pdf_file = None
    
    # First, check Downloads folder
    downloads_path = Path.home() / "Downloads"
    for pattern in pdf_patterns:
        potential_file = downloads_path / pattern
        if potential_file.exists():
            pdf_file = potential_file
            print(f"  Found PDF in Downloads: {pdf_file.name}")
            break
    
    # If not found in Downloads, check infos folder
    if pdf_file is None:
        infos_path = Path("infos")
        for pattern in pdf_patterns:
            potential_file = infos_path / pattern
            if potential_file.exists():
                pdf_file = potential_file
                print(f"  Found PDF in infos: {pdf_file.name}")
                break
        
        # If still not found with specific patterns, look for any PDF in infos
        if pdf_file is None:
            pdf_files = list(infos_path.glob("*.pdf"))
            if pdf_files:
                pdf_file = pdf_files[0]
                print(f"  Found PDF: {pdf_file.name}")
    
    if pdf_file is None:
        print("  ⚠ No PDF file found in infos/")
        return None
    
    try:
        # Extract text from PDF
        full_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    full_text += f"\n--- Page {i+1} ---\n{text}\n"
        
        print(f"✓ Extracted text from {pdf_file.name} ({len(full_text)} characters)")
        
        # Create AI prompt
        prompt = f"""# Coding Challenge - Level {level_number}

## Problem Description (from PDF):

{full_text}

## Task:
Create a Python solution that:
1. Reads input files from the Inputs/ folder
2. Processes each input according to the problem description
3. Writes output files to the Outputs/ folder with the same name but .out extension

## Input Files:
- Located in: Inputs/
- Format: level{level_number}_*.in

## Output Files:
- Should be written to: Outputs/
- Format: level{level_number}_*.out

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
    
    for input_file in sorted(input_folder.glob("level{level_number}_*.in")):
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

The file created should be named: level{level_number}.py and saved in the levels/ folder
"""
        
        # Save prompt to file in prompts/ folder
        os.makedirs("prompts", exist_ok=True)
        prompt_file = f"prompts/level{level_number}_prompt.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        print(f"✓ AI prompt saved to: {prompt_file}")
        print(f"\n{'='*60}")
        print(f"📋 AI PROMPT FOR LEVEL {level_number}")
        print(f"{'='*60}")
        print(prompt)
        print(f"{'='*60}\n")
        
        return prompt
        
    except Exception as e:
        print(f"✗ Error extracting PDF text: {e}")
        import traceback
        traceback.print_exc()
        return None


def organize_files(level_number):
    """Move .in files to Inputs/ and example .out files to Outputs/."""
    print("\nOrganizing files...")
    
    # Create folders
    os.makedirs("Inputs", exist_ok=True)
    os.makedirs("Outputs", exist_ok=True)
    
    infos_path = Path("infos")
    
    # Move all .in files to Inputs/
    in_files = list(infos_path.glob("*.in"))
    for in_file in in_files:
        dest = Path("Inputs") / in_file.name
        shutil.move(str(in_file), str(dest))
        print(f"  Moved {in_file.name} -> Inputs/")
    
    # Move example .out files to Outputs/ (if they exist)
    example_out_files = list(infos_path.glob("*example*.out"))
    for out_file in example_out_files:
        dest = Path("Outputs") / out_file.name
        shutil.move(str(out_file), str(dest))
        print(f"  Moved {out_file.name} -> Outputs/")
    
    print(f"✓ Organized {len(in_files)} input files and {len(example_out_files)} example output files")
    return len(in_files)


def run_solution(level_number):
    """Run the level{N}.py script from levels/ folder."""
    solution_file = f"level{level_number}.py"
    
    print(f"\nRunning {solution_file}...")
    
    # Get absolute path to solution file (should be in levels/ directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    solution_path = project_root / "levels" / solution_file
    
    if not solution_path.exists():
        print(f"✗ Error: {solution_path} not found!")
        print(f"  Looked in: {solution_path}")
        return False
    
    # Change to project root directory before running solution
    old_cwd = os.getcwd()
    os.chdir(project_root)
    
    try:
        # Import and run the solution
        import importlib.util
        spec = importlib.util.spec_from_file_location("solution", str(solution_path))
        solution = importlib.util.module_from_spec(spec)
        
        # Temporarily change sys.argv to prevent issues
        old_argv = sys.argv
        sys.argv = [str(solution_path)]
        
        try:
            spec.loader.exec_module(solution)
            print(f"✓ {solution_file} executed successfully")
            return True
        except Exception as e:
            print(f"✗ Error running {solution_file}: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            sys.argv = old_argv
    finally:
        # Restore original working directory
        os.chdir(old_cwd)


def collect_outputs():
    """Verify output files are in Outputs/ folder."""
    print("\nVerifying output files...")
    
    outputs_path = Path("Outputs")
    
    # Count .out files in Outputs/
    out_files = list(outputs_path.glob("*.out"))
    
    print(f"✓ Found {len(out_files)} output files in Outputs/")
    for out_file in out_files:
        print(f"  {out_file.name}")
    
    return len(out_files)


def cleanup():
    """Delete all files from infos/ folder."""
    print("\nCleaning up infos/ folder...")
    
    infos_path = Path("infos")
    
    # Delete all .in files
    in_files = list(infos_path.glob("*.in"))
    for in_file in in_files:
        in_file.unlink()
        print(f"  Deleted {in_file.name}")
    
    # Delete all remaining files (should be none if everything worked)
    all_files = list(infos_path.glob("*"))
    for file in all_files:
        if file.is_file():
            file.unlink()
            print(f"  Deleted {file.name}")
    
    total_deleted = len(all_files)
    print(f"✓ Cleaned up {total_deleted} files from infos/")


def clear_folders():
    """Clear Inputs and Outputs folders at the start."""
    print("\nClearing Inputs and Outputs folders...")
    
    folders_to_clear = ["Inputs", "Outputs"]
    
    for folder in folders_to_clear:
        if os.path.exists(folder):
            # Remove all files in the folder
            for file in Path(folder).glob("*"):
                if file.is_file():
                    file.unlink()
                    print(f"  Deleted {file.name} from {folder}/")
    
    print("✓ Folders cleared")


def main():
    if len(sys.argv) < 2:
        print("Usage: python general/process_level.py <level_number>")
        print("Example: python general/process_level.py 1")
        sys.exit(1)
    
    level_number = sys.argv[1]
    
    print(f"{'='*60}")
    print(f"Processing Level {level_number}")
    print(f"{'='*60}")
    
    # Step 0: Clear Inputs and Outputs folders
    clear_folders()
    
    # Step 1: Extract zip
    if not extract_zip(level_number):
        print("\n✗ Failed to extract zip file")
        return
    
    # Step 2: Extract PDF text and create prompt
    extract_pdf_text(level_number)
    
    # Step 3: Organize files
    organize_files(level_number)
    
    # Step 4: Run solution
    if not run_solution(level_number):
        print("\n✗ Failed to run solution")
        return
    
    # Step 5: Collect outputs
    collect_outputs()
    
    # Step 6: Cleanup
    cleanup()
    
    print(f"\n{'='*60}")
    print(f"✓ Level {level_number} processing complete!")
    print(f"{'='*60}")
    print(f"\nInput files are in:  Inputs/")
    print(f"Output files are in: Outputs/")
    print(f"\nYou can now upload the output files to the contest platform.")


if __name__ == "__main__":
    main()
