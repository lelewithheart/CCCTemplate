"""
Optimized CCC Level Processor - Extract, organize and prepare level files.

Usage:
    python general/process_level.py <level_number> [--run-solution]
    
Examples:
    python general/process_level.py 1                # Process only
    python general/process_level.py 1 --run-solution # Process and run solution

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


def process_level(level_number: int, run_solution: bool = False) -> int:
    """
    Process a level: extract, organize files, create prompt.
    
    Args:
        level_number: The level number to process
        run_solution: Whether to also run the solution script
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    core = CCCCore(level_number)
    core.print_header(f"Processing Level {level_number}")
    
    try:
        # Step 0: Clear previous data
        core.log("Clearing previous data...")
        core.clear_folder(core.directories['inputs'], "Inputs")
        core.clear_folder(core.directories['outputs'], "Outputs")
        
        # Step 1: Extract ZIP file
        core.log("Step 1: Extracting ZIP file...", "STEP")
        if not core.extract_zip():
            core.log("Failed to extract ZIP file", "ERROR")
            return 1
        
        # Step 2: Extract PDF text and create prompt
        core.log("Step 2: Processing PDF and creating AI prompt...", "STEP")
        pdf_text = core.extract_pdf_text()
        if pdf_text:
            prompt = core.create_ai_prompt(pdf_text)
            
            # Display the prompt
            core.print_header(f"AI PROMPT FOR LEVEL {level_number}")
            print(prompt)
            core.print_separator()
        else:
            core.log("Could not extract PDF text - manual prompt creation needed", "WARNING")
        
        # Step 3: Organize files
        core.log("Step 3: Organizing input and output files...", "STEP")
        in_count, out_count = core.organize_files()
        
        # Step 4: Optionally run solution
        if run_solution:
            core.log("Step 4: Running solution script...", "STEP")
            solution_path = core.find_level_script()
            
            if solution_path:
                exit_code = core.run_python_script(solution_path)
                if exit_code == 0:
                    core.log("Solution executed successfully", "SUCCESS")
                    output_count = core.count_output_files()
                    core.log(f"Generated {output_count} output files", "SUCCESS")
                else:
                    core.log(f"Solution failed with exit code {exit_code}", "ERROR")
            else:
                core.log(f"Solution script level{level_number}.py not found", "WARNING")
        
        # Step 5: Cleanup
        core.log("Step 5: Cleaning up temporary files...", "STEP")
        core.cleanup_infos()
        
        # Summary
        core.print_header(f"Level {level_number} processing complete!")
        core.log(f"Input files: {in_count} moved to Inputs/")
        core.log(f"Example outputs: {out_count} moved to Outputs/")
        
        if pdf_text:
            prompt_file = core.get_prompt_file_path()
            core.log(f"AI prompt saved to: {prompt_file}")
        
        core.log("Ready for solution development!")
        
        return 0
        
    except Exception as e:
        core.log(f"Unexpected error during processing: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python general/process_level.py <level_number> [--run-solution]")
        print("Examples:")
        print("  python general/process_level.py 1                # Process only")
        print("  python general/process_level.py 1 --run-solution # Process and run solution")
        sys.exit(1)
    
    # Parse arguments
    level_number = validate_level_number(sys.argv[1])
    run_solution = "--run-solution" in sys.argv
    
    # Check dependencies
    check_python_dependencies()
    
    # Process the level
    exit_code = process_level(level_number, run_solution)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()