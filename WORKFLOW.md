# Coding Contest Workflow

## Quick Start

```powershell
python run_level.py <level_number>
```

## What Happens

### Step 1: Processing (Automatic)
1. ✅ Extracts `level{N}.zip` from Downloads
2. ✅ Extracts text from `Level {N}.pdf`
3. ✅ Creates an AI prompt in `level{N}_prompt.txt`
4. ✅ Moves `.in` files to `Inputs/`
5. ✅ Moves example `.out` files to `Outputs/`

### Step 2: PAUSE ⏸️
- **The script pauses here!**
- Open `level{N}_prompt.txt` to see the problem description
- Copy the prompt and give it to your AI assistant
- Create `level{N}.py` with your solution
- Press ENTER to continue

### Step 3: Solution Execution (Automatic)
1. ✅ Runs `level{N}.py`
2. ✅ Generates output files in `Outputs/`
3. ✅ Shows completion status

## File Structure

```
project/
├── run_level.py              # Main runner script
├── general/
│   └── process_level.py      # Level processor
├── Inputs/                   # Input files (.in)
├── Outputs/                  # Output files (.out)
├── level{N}_prompt.txt       # AI prompt (auto-generated)
└── level{N}.py               # Your solution (you create this)
```

## Example: Running Level 5

```powershell
python run_level.py 5
```

This will:
1. Process level 5 (extract, organize files)
2. Create `level5_prompt.txt` with the problem
3. **PAUSE** for you to create `level5.py`
4. Press ENTER when ready
5. Run `level5.py` to generate outputs

## Tips

- The AI prompt includes the full problem description from the PDF
- Input files are automatically organized in `Inputs/`
- Your solution should read from `Inputs/` and write to `Outputs/`
- Example template is included in the AI prompt
