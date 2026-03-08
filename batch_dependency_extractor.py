#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
New Dependency Extractor
========================
Function: 

Usage:
  python new_extractor.py
  
  Optional arguments:
    --list <filename>   Specify theorem list file (default: theorems_lst.txt)
    --output <directory> Specify output directory (default: theorems_dependence_new)
    --skip-existing     Skip existing files
    --verbose           Show detailed processing information
    --single <name>     Analyze a single theorem

Output:
  Dependency analysis results saved to theorems_dependence_new/<theorem_name>.txt
  
Output format includes:
  - Bracket notation: 【name】 for Theorem-like, [name] for Lemma, (name) for Other
  - Source file location info
  - Complete dependency tree
"""

import sys
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict

sys.setrecursionlimit(10000)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_THEOREM_LIST = os.path.join(SCRIPT_DIR, 'theorems_lst.txt')
DEFAULT_DEPS_FILE = os.path.join(SCRIPT_DIR, 'theorem_deps.csv')
DEFAULT_CODE_INDEX = os.path.join(SCRIPT_DIR, 'code_index.txt')
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'theorems_dependence')


@dataclass(frozen=True)
class IndexEntry:
    kind: str
    file: str
    line: int
    line_end: int


THEOREM_LIKE_KINDS = {'Theorem', 'Proposition', 'Corollary', 'Fact'}
LEMMA_LIKE_KINDS = {'Lemma'}
AXIOM_LIKE_KINDS = {'Axiom', 'Axioms'}


def load_code_index(code_index_path: str) -> Dict[str, IndexEntry]:
    index: Dict[str, IndexEntry] = {}
    try:
        with open(code_index_path, 'r', encoding='utf-8') as f:
            for raw in f:
                raw = raw.rstrip('\n')
                if not raw:
                    continue
                parts = raw.split(',')
                if len(parts) < 6:
                    continue
                kind, name, _desc, file_name, line_no, line_end = parts[:6]
                kind = kind.strip()
                name = name.strip()
                file_name = file_name.strip()
                try:
                    lno = int(line_no)
                    lend = int(line_end)
                except ValueError:
                    continue
                if name:
                    index[name] = IndexEntry(kind=kind, file=file_name, line=lno, line_end=lend)
    except FileNotFoundError:
        return {}
    return index


def classify_kind_to_123(kind: str) -> int:
    if kind in THEOREM_LIKE_KINDS:
        return 1
    if kind in LEMMA_LIKE_KINDS:
        return 2
    return 3


def is_axiom_kind(kind: str) -> bool:
    return (kind or "").strip() in AXIOM_LIKE_KINDS


def get_brackets_for_name(
    name: str,
    code_index: Dict[str, IndexEntry],
    include_location: bool = False,
    mark_axiom: bool = False,
) -> str:
    entry = code_index.get(name)
    kind = entry.kind if entry else 'Unknown'
    t = classify_kind_to_123(kind)
    
    if t == 1:
        base = f"█{name}█"
    elif t == 2:
        base = f"░{name}░"
    else:
        base = f"[{name}]"

    if mark_axiom and is_axiom_kind(kind):
        base = f"►{base}◄"
    
    if include_location and entry:
        location = f"{entry.file},{entry.line},{entry.line_end}"
        return f"{base}{' ' * 20}{location}"
    
    return base


def load_theorem_dependencies(file_path):
    dependencies = {}
    theorem_positions = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                if '|' in line:
                    theorem, deps_str = line.split('|', 1)
                    theorem = theorem.strip()
                    
                    theorem_positions[theorem] = line_num
                    
                    if deps_str.strip():
                        deps = [dep.strip() for dep in deps_str.split(',')]
                        dependencies[theorem] = deps
                    else:
                        dependencies[theorem] = []
                else:
                    theorem = line.strip()
                    theorem_positions[theorem] = line_num
                    dependencies[theorem] = []
                    
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return None, None
    except Exception as e:
        print(f"Failed to read file: {e}")
        return None, None
        
    return dependencies, theorem_positions


def load_theorem_list(file_path):
    theorems = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) >= 6:
                    kind = parts[0]
                    name = parts[1]
                    description = parts[2]
                    file_path = parts[3]
                    start_line = parts[4]
                    end_line = parts[5]
                    theorems.append((kind, name, description, file_path, start_line, end_line))
                elif len(parts) >= 2:
                    kind = parts[0]
                    name = parts[1]
                    theorems.append((kind, name, "", "", "", ""))
                    
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return []
    except Exception as e:
        print(f"Failed to read theorem list: {e}")
        return []
    
    return theorems


def analyze_dependencies_longest(start_theorem, dependencies):
    if start_theorem not in dependencies:
        return {}

    best_levels = {}
    path_stack = set()

    def dfs(node, level):
        if node in path_stack:
            return

        prev_level = best_levels.get(node)
        if prev_level is not None and level <= prev_level:
            return

        best_levels[node] = level
        path_stack.add(node)

        for dep in dependencies.get(node, []):
            dfs(dep, level + 1)

        path_stack.remove(node)

    dfs(start_theorem, 0)

    levels = defaultdict(list)
    for theorem, level in best_levels.items():
        levels[level].append(theorem)

    for level in levels:
        levels[level].sort()

    return levels


def build_dependency_tree(start_theorem, dependencies, visited=None):
    if visited is None:
        visited = set()

    if start_theorem in visited:
        return {}

    visited.add(start_theorem)

    if start_theorem not in dependencies:
        return {}

    result = {}
    for dep in dependencies[start_theorem]:
        if dep not in visited:
            result[dep] = build_dependency_tree(dep, dependencies, visited)

    return result


def write_dependency_analysis(theorem_name, position, dep_tree, levels, output_file, 
                              code_index=None, kind="", description="", file_path="", start_line="", end_line=""):
    if code_index is None:
        code_index = {}
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Major Theorem Dependency Report\n")
            f.write("=" * 80 + "\n")
            f.write(f"Target theorem: {theorem_name}\n")
            if kind:
                f.write(f"Type: {kind}\n")
            if description:
                f.write(f"Description: {description}\n")
            if file_path:
                f.write(f"File: {file_path}\n")
            if start_line and end_line:
                f.write(f"Lines: {start_line}-{end_line}\n")
            f.write(f"Dependency file position: line {position}\n")
            f.write("\n")
            
            total_deps = sum(len(level_deps) for level, level_deps in levels.items() if level > 0)
            max_level = max((level for level in levels.keys() if level > 0), default=0)
            
            f.write("Statistics:\n")
            f.write(f"  - Total dependent theorems: {total_deps}\n")
            f.write(f"  - Maximum dependency depth: {max_level}\n")
            f.write("\n")
            
            f.write("Bracket notation:\n")
            f.write("  - █name█ : Theorem-like (Theorem/Proposition/Corollary/Fact)\n")
            f.write("  - ░name░ : Lemma\n")
            f.write("  - ►[name]◄ : Axiom (highlighted in the dependency tree)\n")
            f.write("  - [name] : Other (Definition/Fixpoint/Inductive/Axiom/...)\n")
            f.write("\n")
            
            f.write("Dependency levels:\n")
            for level in sorted(levels.keys()):
                level_deps = levels[level]
                f.write(f"Level {level} ({len(level_deps)} theorems):\n")
                for dep in sorted(level_deps):
                    f.write(f"  - {get_brackets_for_name(dep, code_index, include_location=True)}\n")
                f.write("\n")
            
            f.write("Dependency tree:\n")
            
            def print_tree(node, prefix="", is_last=True):
                if not node:
                    return
                    
                items = list(node.items())
                for i, (dep, children) in enumerate(items):
                    connector = "└── " if i == len(items) - 1 else "├── "
                    f.write(f"{prefix}{connector}{get_brackets_for_name(dep, code_index, mark_axiom=True)}\n")
                    
                    extension = "    " if is_last and i == len(items) - 1 else "│   "
                    print_tree(children, prefix + extension, i == len(items) - 1)
            
            print_tree(dep_tree)
            
        return True
    except Exception as e:
        print(f"  Failed to write file: {e}")
        return False


def process_theorem_batch(theorem_list, dependencies, theorem_positions, output_dir, 
                          code_index, skip_existing, verbose):
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    os.makedirs(output_dir, exist_ok=True)
    
    total = len(theorem_list)
    
    for idx, (kind, theorem_name, description, file_path, start_line, end_line) in enumerate(theorem_list, 1):
        output_file = os.path.join(output_dir, f"{theorem_name}.txt")
        
        if skip_existing and os.path.exists(output_file):
            if verbose:
                print(f"[{idx}/{total}] Skip {theorem_name} (file exists)")
            skip_count += 1
            continue
        
        position = theorem_positions.get(theorem_name)
        if position is None:
            if verbose:
                print(f"[{idx}/{total}] Warning: {theorem_name} not found in dependency file")
            fail_count += 1
            continue
        
        if theorem_name not in dependencies:
            if verbose:
                print(f"[{idx}/{total}] Warning: {theorem_name} has no dependencies")
            fail_count += 1
            continue
        
        levels = analyze_dependencies_longest(theorem_name, dependencies)
        
        dep_tree = build_dependency_tree(theorem_name, dependencies)
        
        if write_dependency_analysis(theorem_name, position, dep_tree, levels, output_file,
                                   code_index, kind, description, file_path, start_line, end_line):
            success_count += 1
            if verbose:
                print(f"[{idx}/{total}] Success: {theorem_name}")
        else:
            fail_count += 1
            if verbose:
                print(f"[{idx}/{total}] Failed: {theorem_name}")
    
    return success_count, skip_count, fail_count


def process_single_theorem(theorem_name, dependencies, theorem_positions, output_dir, 
                           code_index, verbose):
    os.makedirs(output_dir, exist_ok=True)
    
    position = theorem_positions.get(theorem_name)
    if position is None:
        print(f"Error: theorem '{theorem_name}' not found in dependency file")
        return False
    
    if theorem_name not in dependencies:
        print(f"Theorem '{theorem_name}' has no dependencies")
        return False
    
    if verbose:
        print(f"Analyzing theorem: {theorem_name}")
    
    levels = analyze_dependencies_longest(theorem_name, dependencies)
    dep_tree = build_dependency_tree(theorem_name, dependencies)
    
    output_file = os.path.join(output_dir, f"{theorem_name}.txt")
    
    if write_dependency_analysis(theorem_name, position, dep_tree, levels, output_file,
                               code_index=code_index):
        if verbose:
            print(f"Analysis saved to: {output_file}")
        return True
    else:
        return False


def main():
    args = sys.argv[1:]
    
    theorem_list_file = DEFAULT_THEOREM_LIST
    deps_file = DEFAULT_DEPS_FILE
    code_index_path = DEFAULT_CODE_INDEX
    output_dir = DEFAULT_OUTPUT_DIR
    skip_existing = False
    verbose = False
    single_theorem = None
    
    i = 0
    while i < len(args):
        if args[i] == '--list' and i + 1 < len(args):
            theorem_list_file = args[i + 1]
            i += 2
        elif args[i] == '--output' and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif args[i] == '--skip-existing':
            skip_existing = True
            i += 1
        elif args[i] == '--verbose':
            verbose = True
            i += 1
        elif args[i] == '--single' and i + 1 < len(args):
            single_theorem = args[i + 1]
            i += 2
        else:
            print(f"Unknown argument: {args[i]}")
            print("Usage: python new_extractor.py [--list <file>] [--output <dir>] [--skip-existing] [--verbose] [--single <theorem>]")
            sys.exit(1)
    
    print("=" * 80)
    print("New Dependency Extractor")
    print("=" * 80)
    print(f"Theorem list file: {theorem_list_file}")
    print(f"Dependency file: {deps_file}")
    print(f"Code index file: {code_index_path}")
    print(f"Output directory: {output_dir}")
    print(f"Skip existing: {'Yes' if skip_existing else 'No'}")
    print(f"Verbose: {'Yes' if verbose else 'No'}")
    print()
    
    print("Loading code index...")
    code_index = load_code_index(code_index_path)
    print(f"Loaded {len(code_index)} code index entries")
    
    if single_theorem:
        print("Loading dependencies...")
        dependencies, theorem_positions = load_theorem_dependencies(deps_file)
        if dependencies is None:
            print("Error: Failed to load dependencies")
            sys.exit(1)
        print(f"Loaded {len(dependencies)} dependency entries")
        print()
        
        success = process_single_theorem(single_theorem, dependencies, theorem_positions, 
                                         output_dir, code_index, verbose)
        if success:
            print(f"\nSingle theorem analysis completed!")
        else:
            print(f"\nSingle theorem analysis failed!")
        sys.exit(0 if success else 1)
    
    print("Loading theorem list...")
    theorem_list = load_theorem_list(theorem_list_file)
    if not theorem_list:
        print("Error: Theorem list is empty")
        sys.exit(1)
    
    print(f"Found {len(theorem_list)} theorems and corollaries")
    
    print("Loading dependencies...")
    dependencies, theorem_positions = load_theorem_dependencies(deps_file)
    if dependencies is None:
        print("Error: Failed to load dependencies")
        sys.exit(1)
    
    print(f"Loaded {len(dependencies)} dependency entries")
    print()
    
    print("Starting batch processing...")
    print("-" * 80)
    
    success_count, skip_count, fail_count = process_theorem_batch(
        theorem_list, dependencies, theorem_positions, output_dir, code_index, skip_existing, verbose
    )
    
    print("-" * 80)
    print()
    print("Processing completed!")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skip_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Total: {len(theorem_list)}")
    print(f"  Output directory: {output_dir}")


if __name__ == "__main__":
    main()
