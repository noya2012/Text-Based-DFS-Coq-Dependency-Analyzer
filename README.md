# Text-Based DFS Coq Dependency Analyzer

A text-based dependency analysis tool using regex pattern matching and DFS traversal for Coq theorem proving projects. This tool provides essential dependency extraction, code simplification, and single theorem analysis.

## Technical Overview

The analyzer employs the following core techniques for Coq element decomposition:

- **Keyword-Based Declaration Extraction**: Uses regex patterns to identify 20+ Coq declaration types (Theorem, Lemma, Definition, Fixpoint, Inductive, etc.) at line-level granularity
- **Nested Comment Parsing**: Handles deeply nested `(* ... *)` comment blocks to associate documentation with declarations
- **Token-Based Dependency Resolution**: Extracts identifiers from statement signatures and proof bodies, filtering local variables via `intros` pattern analysis
- **Depth-First Search (DFS) Traversal**: Computes dependency levels and builds dependency trees using recursive DFS with cycle detection
- **Multi-Pass Architecture**: Stage 1 scans and indexes declarations; Stage 2 resolves cross-file dependencies using the global name table

## Features

- **Dependency Extraction**: Automatically scan Coq source files and extract all top-level declarations
- **Dependency Graph Generation**: Create forward and reverse dependency graphs
- **Single Theorem Analysis**: Detailed analysis of individual theorem dependencies
- **Simplified Code Generation**: Generate code without proofs for quick browsing

## Project Structure

```
full_dependency_analysis/
├── dependency_extractor.py      # Extract declarations and dependencies
├── code_lite_generator.py      # Generate simplified code without proofs
├── major_theorem_dependency_analyzer.py  # Analyze single theorem dependencies
├── run_lite_analysis.cmd        # Windows batch script (runs all tools)
├── prj_files.txt                # List of Coq source files to analyze
├── code_index.txt               # Complete index of all declarations
├── namelist.txt                 # List of all declaration names
├── theorem_deps.csv             # Forward dependency relationships
├── theorem_reverse_deps.csv     # Reverse dependency relationships
├── theorem_deps.dot             # Graphviz DOT visualization
├── code_lite.txt                # Simplified code without proofs
└── theorem_with_deps/           # Individual theorem dependency trees
```

## Quick Start

### Windows Batch Script
```powershell
e:\collatz\full_dependency_analysis\run_lite_analysis.cmd
```

### Manual Execution
```powershell
# Step 1: Extract dependencies
python dependency_extractor.py

# Step 2: Generate simplified code
python code_lite_generator.py

# Step 3: Analyze specific theorem
python major_theorem_dependency_analyzer.py "theorem_name" --to-file
```

## Output Files

| File | Description |
|------|-------------|
| `code_index.txt` | Complete index: kind, name, description, file, line_start, line_end |
| `namelist.txt` | List of all declaration names |
| `theorem_deps.csv` | Forward dependencies: `name|dep1,dep2,...` |
| `theorem_reverse_deps.csv` | Reverse dependencies: `name|user1,user2,...` |
| `theorem_deps.dot` | Graphviz DOT format for visualization |
| `code_lite.txt` | Coq code with proof sections removed |
| `theorem_with_deps/<name>.txt` | Dependency tree for specific theorem |

## Supported Declaration Types

**Theorems and Proofs:**
- Theorem, Lemma, Proposition, Corollary, Fact, Remark

**Definitions:**
- Definition, Program Definition, Fixpoint, CoFixpoint

**Types:**
- Inductive, CoInductive, Record, Structure, Variant, Class

**Axioms and Parameters:**
- Axiom, Parameter, Variable, Hypothesis

## Configuration

### Project File List (Required)
Before running any analysis, configure `prj_files.txt` to specify Coq source files:

```powershell
# Generate file list (adjust path to your project directory)
Get-ChildItem -Path "YourProjectPath" -Filter "*.v" -Recurse | Select-Object -ExpandProperty FullName > prj_files.txt
```

**Important: Path Configuration Notes**

The paths in `prj_files.txt` are relative to the script execution directory (`full_dependency_analysis/`). Choose the appropriate format based on your project structure:

**If .v files are in a parent directory (use `../` prefix):**
```
../log2_p.v
../collatz_part_1.v
../collatz_part_2.v
...
```

**If .v files are in the same directory:**
```
log2_p.v
collatz_part_1.v
collatz_part_2.v
...
```

**If .v files are in a subdirectory:**
```
../your_subdir/log2_p.v
../your_subdir/collatz_part_1.v
...
```

**Note**: The order matters—files that are depended upon should appear earlier in the list.

## Dependencies

- Python 3.6+
- Standard library modules only (no external dependencies)
- Graphviz (optional, for visualization)

## Compatibility

### Tested Environment
This project has been tested and verified with **Coq 8.10.2**. The design is generic and can be applied to analyze dependencies in similar theorem proving codebases. However, it has not been tested on newer versions such as Rocq (the successor to Coq).

### Tested Project
This toolchain has been successfully tested on the Coq project [collatz-formalization-coq](https://github.com/noya2012/collatz-formalization-coq).

## Example Output

### Dependency Tree
```
Dependency tree:
├── █helper_lemma1█
│   └── [basic_definition]
├── ░helper_lemma2░
│   └── [utility_function]
└── [core_definition]

Bracket notation:
  - █name█ : Theorem-like (Theorem/Proposition/Corollary/Fact)
  - ░name░ : Lemma
  - [name] : Other (Definition/Fixpoint/Inductive/Axiom/...)
```

## Troubleshooting

### Encoding Issues
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

### File Not Found
- Ensure `prj_files.txt` contains valid file paths
- Check current working directory: `Get-Location`

## License

This project is licensed under the MIT License.
