"""
Optimized CCC Level Runner - Run a specific level with enhanced automation.

Usage:
    python run_level.py <level_number> [--auto]
    
Examples:
    python run_level.py 5        # Interactive mode (pauses for manual solution creation)
    python run_level.py 5 --auto # Automated mode (attempts AI-assisted solution)
"""

import sys
import os
from pathlib import Path
from ccc_core import CCCCore, validate_level_number, check_python_dependencies


def run_level_interactive(core: CCCCore):
    """Run level in interactive mode with manual solution creation."""
    core.log("Running level processing...")
    
    # Step 1: Run the processing pipeline
    success = run_processing_pipeline(core)
    if not success:
        return 1
    
    # Step 2: Pause for manual solution creation
    core.print_header(f"⏸️  PAUSED - Create level{core.level_number}.py now")
    
    prompt_file = core.get_prompt_file_path()
    core.log(f"AI prompt saved to: {prompt_file}")
    core.log("Input files are ready in: Inputs/")
    core.log(f"Next step: Create level{core.level_number}.py to solve the problem")
    
    print(f"\nPress ENTER when you're ready to run level{core.level_number}.py...")
    input()
    
    # Step 3: Run the solution
    return run_solution(core)


def run_level_automated(core: CCCCore):
    """Run level in automated mode with AI assistance."""
    core.log("Running automated level processing with AI assistance...")
    
    # Step 1: Run the processing pipeline
    success = run_processing_pipeline(core)
    if not success:
        return 1
    
    # Step 2: Attempt automated AI solution generation
    from ccc_ai_automation import AIAutomation
    
    ai_automation = AIAutomation(core)
    success = ai_automation.generate_solution()
    
    if not success:
        core.log("AI automation failed, falling back to interactive mode", "WARNING")
        return run_level_interactive(core)
    
    # Step 3: Run the generated solution
    return run_solution(core)


def run_processing_pipeline(core: CCCCore) -> bool:
    """Run the processing pipeline (extract, organize, create prompt)."""
    
    # Clear previous run data
    core.clear_folder(core.directories['inputs'], "Inputs")
    core.clear_folder(core.directories['outputs'], "Outputs")
    
    # Extract ZIP file
    if not core.extract_zip():
        core.log("Failed to extract ZIP file", "ERROR")
        return False
    
    # Extract PDF and create prompt
    pdf_text = core.extract_pdf_text()
    if pdf_text:
        core.create_ai_prompt(pdf_text)
    else:
        core.log("Could not extract PDF text - you'll need to create the prompt manually", "WARNING")
    
    # Organize files
    core.organize_files()
    
    core.log("Processing pipeline completed successfully", "SUCCESS")
    return True


def run_solution(core: CCCCore) -> int:
    """Find and run the level solution script."""
    core.print_separator()
    core.log(f"Running level{core.level_number}.py...")
    
    # Find the solution script
    solution_path = core.find_level_script()
    if not solution_path:
        core.log(f"level{core.level_number}.py not found!", "ERROR")
        core.log("Please create the file and try again.")
        return 1
    
    # Run the solution
    exit_code = core.run_python_script(solution_path)
    
    if exit_code != 0:
        core.log(f"Error running {solution_path.name} (exit code: {exit_code})", "ERROR")
        return exit_code
    
    core.log(f"{solution_path.name} completed successfully", "SUCCESS")
    
    # Verify outputs
    output_count = core.count_output_files()
    core.log(f"Generated {output_count} output files in Outputs/", "SUCCESS")
    
    # Cleanup
    core.cleanup_infos()
    
    core.print_header(f"Level {core.level_number} completed successfully!")
    return 0
    
def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python run_level.py <level_number> [--auto]")
        print("Examples:")
        print("  python run_level.py 5        # Interactive mode")
        print("  python run_level.py 5 --auto # Automated mode with AI")
        sys.exit(1)
    
    # Parse arguments
    level_num = validate_level_number(sys.argv[1])
    auto_mode = "--auto" in sys.argv
    
    # Check dependencies
    check_python_dependencies()
    
    # Initialize core
    core = CCCCore(level_num)
    core.print_header(f"CCC Level {level_num} Runner")
    
    # Run in appropriate mode
    if auto_mode:
        try:
            exit_code = run_level_automated(core)
        except ImportError:
            core.log("AI automation module not available, falling back to interactive mode", "WARNING")
            exit_code = run_level_interactive(core)
    else:
        exit_code = run_level_interactive(core)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
