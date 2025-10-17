"""
Enhanced CCC Main Runner - Fully automated coding contest workflow.

This is the new main entry point that provides a complete automated solution for 
coding contests with AI assistance, optimization, and enhanced workflow management.

Usage:
    python ccc_runner.py <level_number> [options]
    
Options:
    --auto          Full automation with AI assistance
    --interactive   Interactive mode (manual solution creation) 
    --process-only  Only process files, don't run solution
    --template      Generate solution template
    --help          Show help information

Examples:
    python ccc_runner.py 5                    # Interactive mode (default)
    python ccc_runner.py 5 --auto            # Full AI automation
    python ccc_runner.py 5 --process-only    # Just extract and organize
    python ccc_runner.py 5 --template        # Generate solution template
"""

import sys
import argparse
from pathlib import Path
from ccc_core import CCCCore, validate_level_number, check_python_dependencies
from ccc_ai_automation import AIAutomation, create_ai_workflow_file


class CCCRunner:
    """Enhanced CCC runner with full automation capabilities."""
    
    def __init__(self, level_number: int):
        self.level_number = level_number
        self.core = CCCCore(level_number)
    
    def run_full_automation(self) -> int:
        """Run with full AI automation."""
        self.core.print_header(f"🤖 CCC Level {self.level_number} - Full Automation Mode")
        
        # Step 1: Process files
        if not self._run_processing_pipeline():
            return 1
        
        # Step 2: AI-assisted solution generation
        self.core.log("Starting AI-assisted solution generation...", "STEP")
        ai_automation = AIAutomation(self.core)
        
        if ai_automation.generate_solution():
            self.core.log("AI solution generated successfully", "SUCCESS")
        else:
            self.core.log("AI automation failed, creating workflow guide...", "WARNING")
            workflow_file = create_ai_workflow_file(self.level_number, self.core)
            self.core.log(f"Please follow the guide in: {workflow_file}")
            
            # Wait for manual solution creation
            print(f"\nPress ENTER after creating level{self.level_number}.py...")
            input()
        
        # Step 3: Run solution
        return self._run_solution()
    
    def run_interactive(self) -> int:
        """Run in interactive mode with manual solution creation."""
        self.core.print_header(f"👤 CCC Level {self.level_number} - Interactive Mode")
        
        # Step 1: Process files
        if not self._run_processing_pipeline():
            return 1
        
        # Step 2: Create AI workflow guide
        workflow_file = create_ai_workflow_file(self.level_number, self.core)
        
        # Step 3: Pause for manual work
        self.core.print_header(f"⏸️  PAUSED - Create level{self.level_number}.py now")
        
        prompt_file = self.core.get_prompt_file_path()
        self.core.log(f"📋 AI prompt: {prompt_file}")
        self.core.log(f"📖 Workflow guide: {workflow_file}")
        self.core.log("📁 Input files ready in: Inputs/")
        self.core.log(f"🎯 Create solution: level{self.level_number}.py")
        
        print(f"\\nPress ENTER when level{self.level_number}.py is ready...")
        input()
        
        # Step 4: Run solution
        return self._run_solution()
    
    def run_process_only(self) -> int:
        """Only process files without running solution."""
        self.core.print_header(f"📦 CCC Level {self.level_number} - Process Only Mode")
        
        if self._run_processing_pipeline():
            workflow_file = create_ai_workflow_file(self.level_number, self.core)
            
            self.core.print_header("Processing Complete!")
            self.core.log(f"📋 AI prompt: {self.core.get_prompt_file_path()}")
            self.core.log(f"📖 Workflow guide: {workflow_file}")
            self.core.log("📁 Input files in: Inputs/")
            self.core.log(f"🎯 Next: Create level{self.level_number}.py")
            
            return 0
        return 1
    
    def run_template_generation(self) -> int:
        """Generate solution template."""
        self.core.print_header(f"📝 CCC Level {self.level_number} - Template Generation")
        
        # Step 1: Process files
        if not self._run_processing_pipeline():
            return 1
        
        # Step 2: Generate template
        self.core.log("Generating solution template...", "STEP")
        ai_automation = AIAutomation(self.core)
        
        if ai_automation._try_template_generation(""):
            self.core.log(f"Template generated: level{self.level_number}.py", "SUCCESS")
            self.core.log("⚠️  Please implement the solve() function", "WARNING")
            
            # Step 3: Optionally run the template
            print(f"\\nRun the template now? [y/N]: ", end="")
            if input().lower() in ['y', 'yes']:
                return self._run_solution()
            
            return 0
        else:
            self.core.log("Template generation failed", "ERROR")
            return 1
    
    def _run_processing_pipeline(self) -> bool:
        """Run the file processing pipeline."""
        self.core.log("Starting processing pipeline...", "STEP")
        
        # Clear previous data
        self.core.clear_folder(self.core.directories['inputs'], "Inputs")
        self.core.clear_folder(self.core.directories['outputs'], "Outputs")
        
        # Extract ZIP
        if not self.core.extract_zip():
            return False
        
        # Process PDF and create prompt  
        pdf_text = self.core.extract_pdf_text()
        if pdf_text:
            self.core.create_ai_prompt(pdf_text)
        else:
            self.core.log("PDF processing failed - manual prompt needed", "WARNING")
        
        # Organize files
        self.core.organize_files()
        
        self.core.log("Processing pipeline completed", "SUCCESS")
        return True
    
    def _run_solution(self) -> int:
        """Find and run the level solution."""
        self.core.print_separator()
        self.core.log(f"Running level{self.level_number}.py...", "STEP")
        
        solution_path = self.core.find_level_script()
        if not solution_path:
            self.core.log(f"level{self.level_number}.py not found!", "ERROR")
            return 1
        
        # Run solution
        exit_code = self.core.run_python_script(solution_path)
        
        if exit_code != 0:
            self.core.log(f"Solution failed (exit code: {exit_code})", "ERROR")
            return exit_code
        
        # Verify outputs
        output_count = self.core.count_output_files()
        self.core.log(f"Generated {output_count} output files", "SUCCESS")
        
        # Cleanup
        self.core.cleanup_infos()
        
        # Final summary
        self.core.print_header(f"🎉 Level {self.level_number} Completed Successfully!")
        self.core.log("📁 Output files ready in: Outputs/")
        self.core.log("🚀 Ready for submission!")
        
        return 0


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Enhanced CCC Runner with AI automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ccc_runner.py 5                    # Interactive mode (default)
  python ccc_runner.py 5 --auto            # Full AI automation  
  python ccc_runner.py 5 --process-only    # Just extract and organize
  python ccc_runner.py 5 --template        # Generate solution template
        """
    )
    
    parser.add_argument('level_number', type=int, 
                       help='Level number to process')
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--auto', action='store_true',
                      help='Full automation with AI assistance')
    group.add_argument('--interactive', action='store_true', 
                      help='Interactive mode (manual solution creation)')
    group.add_argument('--process-only', action='store_true',
                      help='Only process files, don\'t run solution')  
    group.add_argument('--template', action='store_true',
                      help='Generate solution template')
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Check dependencies
    check_python_dependencies()
    
    # Initialize runner
    runner = CCCRunner(args.level_number)
    
    # Determine mode
    if args.auto:
        exit_code = runner.run_full_automation()
    elif args.process_only:
        exit_code = runner.run_process_only()
    elif args.template:
        exit_code = runner.run_template_generation()
    else:  # Default to interactive
        exit_code = runner.run_interactive()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()