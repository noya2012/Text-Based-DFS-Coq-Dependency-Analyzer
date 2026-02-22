#!/usr/bin/env python3
import sys
import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict

sys.setrecursionlimit(10000)


@dataclass(frozen=True)
class IndexEntry:
    kind: str
    file: str
    line: int
    line_end: int

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
        print(f"Error: file not found - {file_path}")
        return None, None
    except Exception as e:
        print(f"Failed to read file: {e}")
        return None, None
        
    return dependencies, theorem_positions


def load_code_index(code_index_path: str) -> Dict[str, IndexEntry]:
    """Load name -> (kind, file, line, line_end) from code_index.txt."""
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


THEOREM_LIKE_KINDS = {
    'Theorem', 'Proposition', 'Corollary', 'Fact'
}
LEMMA_LIKE_KINDS = {
    'Lemma',
}


def classify_kind_to_123(kind: str) -> int:
    """Classify Coq element kind into 1(Theorem-like)/2(Lemma)/3(Other)."""
    if kind in THEOREM_LIKE_KINDS:
        return 1
    if kind in LEMMA_LIKE_KINDS:
        return 2
    return 3


def get_brackets_for_name(name: str, code_index: Dict[str, IndexEntry], include_location: bool = False) -> str:
    """Get brackets for a name based on its type.
    
    Args:
        name: The name of the theorem/definition
        code_index: The code index dictionary
        include_location: Whether to include source location info
    """
    entry = code_index.get(name)
    kind = entry.kind if entry else 'Unknown'
    t = classify_kind_to_123(kind)
    
    if t == 1:
        base = f"█{name}█"
    elif t == 2:
        base = f"░{name}░"
    else:
        base = f"[{name}]"
    
    if include_location and entry:
        location = f"{entry.file},{entry.line},{entry.line_end}"
        return f"{base}{' ' * 20}{location}"
    
    return base

def find_theorem_position(theorem_name, theorem_positions):
    if theorem_name in theorem_positions:
        return theorem_positions[theorem_name]
    else:
        return None

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

def analyze_dependencies_recursive(theorem_name, dependencies, visited=None, level=0):
    if visited is None:
        visited = set()
        
    if theorem_name in visited:
        return {}
        
    visited.add(theorem_name)
    
    if theorem_name not in dependencies:
        return {}
        
    result = {}
    direct_deps = dependencies.get(theorem_name, [])
    
    for dep in direct_deps:
        if dep not in visited:
            result[dep] = analyze_dependencies_recursive(dep, dependencies, visited, level + 1)
    
    return result

def flatten_dependencies(dep_tree):
    levels = defaultdict(list)
    
    def traverse(node, current_level=0):
        for dep, children in node.items():
            levels[current_level].append(dep)
            traverse(children, current_level + 1)
    
    traverse(dep_tree)
    return levels

def find_shortest_path_lengths(start_theorem, dependencies, target_theorems):
    from collections import deque
    
    shortest_paths = {}
    visited = set()
    queue = deque([(start_theorem, 0)])
    
    while queue:
        theorem, path_length = queue.popleft()
        
        if theorem in visited:
            continue
            
        visited.add(theorem)
        
        if theorem in target_theorems and theorem not in shortest_paths:
            shortest_paths[theorem] = path_length

        if len(shortest_paths) == len(target_theorems):
            break

        if theorem in dependencies:
            for dep in dependencies[theorem]:
                if dep not in visited:
                    queue.append((dep, path_length + 1))
    
    return shortest_paths

def print_dependency_analysis(theorem_name, position, dep_tree, levels, code_index=None, output_file=None):
    if code_index is None:
        code_index = {}
    
    output_lines = []
    
    def add_line(line):
        output_lines.append(line)
        if output_file:
            output_file.write(line + '\n')
        else:
            print(line)
    
    add_line("=" * 80)
    add_line("Major Theorem Dependency Report")
    add_line("=" * 80)
    add_line(f"Target theorem: {theorem_name}")
    add_line(f"File position: line {position}")
    add_line("")
    
    total_deps = sum(len(level_deps) for level, level_deps in levels.items() if level > 0)
    max_level = max((level for level in levels.keys() if level > 0), default=0)

    add_line("Statistics:")
    add_line(f"  - Total dependent theorems: {total_deps}")
    add_line(f"  - Maximum dependency depth: {max_level}")
    add_line("")
    add_line("Bracket notation:")
    add_line("  - █name█ : Theorem-like (Theorem/Proposition/Corollary/Fact)")
    add_line("  - ░name░ : Lemma")
    add_line("  - [name] : Other (Definition/Fixpoint/Inductive/Axiom/...)")
    add_line("")
    
    add_line("Dependency levels:")
    for level in sorted(levels.keys()):
        level_deps = levels[level]
        add_line(f"Level {level} ({len(level_deps)} theorems):")
        for dep in sorted(level_deps):
            add_line(f"  - {get_brackets_for_name(dep, code_index, include_location=True)}")
        add_line("")
    
    add_line("Dependency tree:")
    
    def print_tree(node, prefix="", is_last=True):
        if not node:
            return
            
        items = list(node.items())
        for i, (dep, children) in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            add_line(f"{prefix}{connector}{get_brackets_for_name(dep, code_index)}")
            
            extension = "    " if is_last and i == len(items) - 1 else "│   "
            print_tree(children, prefix + extension, i == len(items) - 1)
    
    print_tree(dep_tree)
    
    return output_lines

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python major_theorem_dependency_analyzer.py <theorem> [--to-file]")
        print("Example: python major_theorem_dependency_analyzer.py build_k_steps_numeric_canonical")
        print("Example: python major_theorem_dependency_analyzer.py build_k_steps_numeric_canonical --to-file")
        sys.exit(1)
    
    theorem_name = sys.argv[1]
    output_to_file = len(sys.argv) == 3 and sys.argv[2] == "--to-file"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "theorem_deps.csv")
    code_index_path = os.path.join(script_dir, "code_index.txt")
    output_dir = os.path.join(script_dir, "theorem_with_deps")
    if output_to_file:
        os.makedirs(output_dir, exist_ok=True)
    
    print(f"Analyzing theorem: {theorem_name}")
    print(f"Dependency file: {file_path}")
    if output_to_file:
        print(f"Output mode: write to file {os.path.join(output_dir, theorem_name + '.txt')}")
    print()
    dependencies, theorem_positions = load_theorem_dependencies(file_path)
    if dependencies is None:
        sys.exit(1)
    position = find_theorem_position(theorem_name, theorem_positions)
    if position is None:
        print(f"Error: theorem '{theorem_name}' not found")
        sys.exit(1)
    if theorem_name not in dependencies:
        print(f"Theorem '{theorem_name}' has no dependencies")
        sys.exit(0)
    print("Computing longest dependency depth...")
    levels = analyze_dependencies_longest(theorem_name, dependencies)
    dep_tree = {theorem_name: build_dependency_tree(theorem_name, dependencies)}

    code_index = load_code_index(code_index_path)
    if output_to_file:
        output_filename = os.path.join(output_dir, f"{theorem_name}.txt")
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                print_dependency_analysis(theorem_name, position, dep_tree[theorem_name], levels, code_index, f)
            print(f"Analysis saved to: {output_filename}")
        except Exception as e:
            print(f"Failed to save file: {e}")
            print_dependency_analysis(theorem_name, position, dep_tree[theorem_name], levels, code_index)
    else:
        print_dependency_analysis(theorem_name, position, dep_tree[theorem_name], levels, code_index)

if __name__ == "__main__":
    main()
