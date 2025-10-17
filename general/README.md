# General Utilities for Coding Contest

This folder contains utility scripts to help process coding contest levels efficiently.

## process_level.py

Automates the entire workflow for processing a contest level.

### What it does:

1. **Extracts** `level{N}.zip` to the `infos/` folder
2. **Organizes** files:
   - Moves all `.in` files → `Inputs/` folder
   - Moves example `.out` files → `Outputs/` folder
3. **Runs** your `solution.py` to generate output files
4. **Collects** generated `.out` files → `Outputs/` folder
5. **Cleans up** by deleting all `.in` and `.out` files from `infos/`

### Usage:

```bash
python general/process_level.py <level_number>
```

### Example:

```bash
python general/process_level.py 1
```

This will process `level1.zip` and organize everything automatically.

### Requirements:

- Have your `level{N}.zip` file in Downloads folder (or project root)
- Have your `level{N}.py` solution ready in the project root
- Python 3.6 or higher

### After running:

- Your input files will be in: `Inputs/`
- Your output files will be in: `Outputs/`
- Upload the files from `Outputs/` to the contest platform

### Folder Structure:

```
project/
├── general/
│   └── process_level.py     # This utility script
├── infos/                    # Temporary extraction (cleaned up)
├── Inputs/                   # Your input files
├── Outputs/                  # Your output files (to upload)
├── level1.py                 # Your level 1 solution
├── level2.py                 # Your level 2 solution
└── ...

Downloads/
└── level1.zip                # Contest zip file (auto-detected)
```
