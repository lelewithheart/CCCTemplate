"""
Run a specific level by executing the general processor and then the level script.

Usage:
    python run_level.py <level_number>
    
Example:
    python run_level.py 5
"""

import sys
import subprocess
import os


def run_level(level_number):
    """Run the general processor and then the specific level script."""
    
    print(f"=" * 60)
    print(f"Running Level {level_number}")
    print(f"=" * 60)
    
    # Step 1: Run general/process_level.py
    print(f"\nStep 1: Running general/process_level.py {level_number}...")
    print("-" * 60)
    
    process_script = os.path.join("general", "process_level.py")
    result1 = subprocess.run([sys.executable, process_script, str(level_number)], 
                            capture_output=False)
    
    if result1.returncode != 0:
        print(f"\n❌ Error running general/process_level.py (exit code: {result1.returncode})")
        return result1.returncode
    
    print(f"\n✓ general/process_level.py completed successfully")
    
    # Pause to allow user to create the level file
    print(f"\n" + "=" * 60)
    print(f"⏸️  PAUSED - Create level{level_number}.py now")
    print(f"=" * 60)
    print(f"\nThe AI prompt has been saved to: level{level_number}_prompt.txt")
    print(f"Input files are ready in: Inputs/")
    print(f"\nNext step: Create level{level_number}.py to solve the problem")
    print(f"\nPress ENTER when you're ready to run level{level_number}.py...")
    input()
    
    # Step 2: Run level{LevelNumber}.py
    print(f"\nStep 2: Running level{level_number}.py...")
    print("-" * 60)
    
    level_script = f"level{level_number}.py"
    if not os.path.exists(level_script):
        print(f"\n❌ Error: {level_script} not found!")
        print(f"Please create the file and try again.")
        return 1
    
    result2 = subprocess.run([sys.executable, level_script], 
                            capture_output=False)
    
    if result2.returncode != 0:
        print(f"\n❌ Error running {level_script} (exit code: {result2.returncode})")
        return result2.returncode
    
    print(f"\n✓ {level_script} completed successfully")
    
    print(f"\n" + "=" * 60)
    print(f"Level {level_number} completed successfully!")
    print(f"=" * 60)
    
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_level.py <level_number>")
        print("Example: python run_level.py 5")
        sys.exit(1)
    
    try:
        level_num = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid integer")
        sys.exit(1)
    
    exit_code = run_level(level_num)
    sys.exit(exit_code)
