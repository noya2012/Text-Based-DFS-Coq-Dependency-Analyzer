#!/usr/bin/env python3
"""
Coq Dependency Extractor
Extracts declarations and computes dependencies from Coq source files.

Usage:
    python dependency_extractor.py [--no-deps] [--deps-only]

Compatibility Notes:
    This project has been tested and verified with Coq 8.10.2.
    The design is generic and can be applied to analyze dependencies in similar
    theorem proving codebases. However, it has not been tested on newer versions
    such as Rocq (the successor to Coq). Users working with Rocq or later Coq
    versions may need to adapt the keyword patterns and parsing logic accordingly.
"""

from __future__ import annotations
import sys, re, os
from typing import List, Tuple, Optional, Set, Dict
from dataclasses import dataclass
import tkinter as tk
from tkinter import filedialog

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PRJ_FILES_TXT = os.path.join(SCRIPT_DIR, 'prj_files.txt')
CODE_INDEX_FILE = os.path.join(SCRIPT_DIR, 'code_index.txt')
NAMELIST_FILE   = os.path.join(SCRIPT_DIR, 'namelist.txt')
DEPS_FILE       = os.path.join(SCRIPT_DIR, 'theorem_deps.csv')
DEPS_DOT_FILE   = os.path.join(SCRIPT_DIR, 'theorem_deps.dot')
REVERSE_DEPS_FILE = os.path.join(SCRIPT_DIR, 'theorem_reverse_deps.csv')

KEYWORD_MAP = {
    'Lemma': 'Lemma','Theorem': 'Theorem','Proposition': 'Proposition','Corollary': 'Corollary','Fact': 'Fact','Remark': 'Remark',
    'Definition': 'Definition','Program Definition': 'Program Definition','Fixpoint': 'Fixpoint','CoFixpoint': 'CoFixpoint','Inductive': 'Inductive',
    'CoInductive': 'CoInductive','Record': 'Record','Structure': 'Structure','Variant': 'Variant','Class': 'Class','Axiom': 'Axiom',
    'Axioms': 'Axiom','Hypothesis': 'Hypothesis','Hypotheses': 'Hypothesis','Variable': 'Variable','Variables': 'Variable','Parameter': 'Parameter','Parameters': 'Parameter'
}
START_KEYWORDS = [
    'Program Definition','Lemma','Theorem','Proposition','Corollary','Fact','Remark','Definition','Fixpoint','CoFixpoint',
    'Inductive','CoInductive','Record','Structure','Variant','Class','Axiom','Axioms','Hypothesis','Hypotheses','Variable',
    'Variables','Parameter','Parameters'
]
KEYWORD_PATTERN = re.compile(r"^\s*(" + '|'.join(re.escape(k) for k in sorted(START_KEYWORDS, key=lambda x: -len(x))) + r")\b")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*$")
MULTI_NAME_SET = {'Axiom','Axioms','Hypothesis','Hypotheses','Variable','Variables','Parameter','Parameters'}

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
PROOF_END_RE = re.compile(r"^\s*(Qed|Defined|Admitted|Abort)\.(?:\s*(?:\(\*.*)?)*\s*$")
INTROS_RE = re.compile(r"\bintros?\b([^.]*)\.")

@dataclass
class Decl:
    kind: str
    raw_kind: str
    name: str
    file: str
    line: int
    line_end: int

def extract_comment_blocks(text: str) -> List[Tuple[int,int,str]]:
    blocks: List[Tuple[int,int,str]] = []
    i = 0; n = len(text); line = 1; depth = 0
    start_line: Optional[int] = None
    buf: List[str] = []
    while i < n:
        if text.startswith('(*', i):
            if depth == 0:
                start_line = line
            depth += 1
            i += 2
            continue
        if text.startswith('*)', i) and depth > 0:
            depth -= 1
            i += 2
            if depth == 0 and start_line is not None:
                content = ''.join(buf)
                end_line = line
                cleaned = cleanup_comment_content(content)
                blocks.append((start_line, end_line, cleaned))
                buf = []
                start_line = None
            continue
        ch = text[i]
        if ch == '\n':
            if depth>0: buf.append(ch)
            line += 1; i += 1
        else:
            if depth>0: buf.append(ch)
            i += 1
    return blocks

def cleanup_comment_content(raw: str) -> str:
    lines = [ln.strip() for ln in raw.splitlines()]
    while lines and lines[0] == '': lines.pop(0)
    while lines and lines[-1] == '': lines.pop()
    return re.sub(r"\s+", ' ', ' '.join(lines)).strip()

def tokenize_decl_names(keyword: str, remainder: str) -> List[str]:
    names: List[str] = []
    cleaned = remainder.replace('(', ' ').replace(')', ' ')
    tokens = cleaned.split()
    if keyword in MULTI_NAME_SET:
        for tok in tokens:
            if ':' in tok or ':=' in tok:
                break
            if tok.endswith('.') and tok[:-1]:
                core = tok[:-1]
                if IDENT_RE.match(core):
                    names.append(core)
                break
            if IDENT_RE.match(tok):
                names.append(tok)
        return names
    else:
        for tok in tokens:
            if tok.startswith('{') and tok.endswith('}'): continue
            if ':' in tok or ':=' in tok: break
            candidate = tok.rstrip('.;')
            if IDENT_RE.match(candidate):
                names.append(candidate); break
        return names

def find_decls(lines: List[str]):
    decls = []
    for idx, ln in enumerate(lines, start=1):
        m = KEYWORD_PATTERN.match(ln)
        if not m: continue
        kw = m.group(1)
        remainder = ln[m.end():]
        names = tokenize_decl_names(kw, remainder)
        for nm in names:
            decls.append((idx, kw, nm))
    return decls


def associate(decls, comments, lines):
    is_blank = {i+1: (lines[i].strip() == '') for i in range(len(lines))}
    results = []
    for line_no, kw, name in decls:
        desc = ''
        candidates = [c for c in comments if c[1] < line_no]
        if candidates:
            for start, end, content in reversed(candidates):
                if all(is_blank.get(ln, True) for ln in range(end+1, line_no)):
                    desc = content; break
        results.append((kw, name, desc, line_no))
    return results

def normalize_kind(kw: str) -> str:
    return KEYWORD_MAP.get(kw, kw)

def strip_comments_preserve_lines(lines: List[str]) -> List[str]:
    out: List[str] = []
    depth = 0
    for line in lines:
        i=0; n=len(line); buf=[]
        while i<n:
            if line.startswith('(*', i): depth+=1; i+=2; continue
            if line.startswith('*)', i) and depth>0: depth-=1; i+=2; continue
            ch=line[i]
            if depth==0: buf.append(ch)
            i+=1
        out.append(''.join(buf) if depth==0 else '')
    return out

def find_statement_end(clean_lines: List[str], start_line: int) -> int:
    for ln in range(start_line, len(clean_lines)+1):
        if '.' in clean_lines[ln-1]:
            return ln
    return start_line

def find_proof_end(clean_lines: List[str], stmt_end: int) -> Optional[int]:
    for ln in range(stmt_end+1, len(clean_lines)+1):
        line = clean_lines[ln-1].strip()
        if not line: continue
        if PROOF_END_RE.match(line): return ln
    return None

def collect_locals(statement_lines: List[str], body_lines: List[str]) -> Set[str]:
    locals: Set[str] = set()
    for line in statement_lines:
        for seg in re.findall(r"\([^)]*\)", line):
            content = seg[1:-1]; tokens = content.split()
            for tok in tokens:
                if tok in (':',':='): break
                if tok.startswith('{') and tok.endswith('}'): tok=tok[1:-1]
                if TOKEN_RE.fullmatch(tok): locals.add(tok)
    body_text='\n'.join(body_lines)
    for m in INTROS_RE.finditer(body_text):
        for tok in TOKEN_RE.findall(m.group(1)):
            locals.add(tok)
    return locals

def extract_dependencies(statement_lines: List[str], body_lines: List[str], global_names: Set[str], self_name: str, local_ids: Set[str]) -> List[str]:
    deps: List[str] = []; seen: Set[str] = set()
    for line in statement_lines:
        for tok in TOKEN_RE.findall(line):
            if tok == self_name: continue
            if tok in local_ids: continue
            if tok in global_names and tok not in seen:
                seen.add(tok); deps.append(tok)
    
    for line in body_lines:
        for tok in TOKEN_RE.findall(line):
            if tok == self_name: continue
            if tok in local_ids: continue
            if tok in global_names and tok not in seen:
                seen.add(tok); deps.append(tok)
    
    return deps

def get_coq_files() -> List[str]:
    
    if os.path.exists(PRJ_FILES_TXT):
        try:
            with open(PRJ_FILES_TXT, 'r', encoding='utf-8') as f:
                files = [line.strip() for line in f if line.strip()]
            if files:
                print(f"Loaded {len(files)} files from {PRJ_FILES_TXT}")
                return files
        except Exception as e:
            print(f"Failed to read {PRJ_FILES_TXT}: {e}")

    print("prj_files.txt is missing or empty; please select Coq sources...")
    
    root = tk.Tk()
    root.withdraw()
    
    file_paths = filedialog.askopenfilenames(
        title="Select Coq source files",
        filetypes=[("Coq files", "*.v"), ("All files", "*.*")]
    )
    
    root.destroy()
    
    if not file_paths:
        print("No files selected; exiting")
        sys.exit(1)
    
    files = list(file_paths)
    
    try:
        with open(PRJ_FILES_TXT, 'w', encoding='utf-8') as f:
            for file in files:
                f.write(file + '\n')
        print(f"Saved absolute paths of {len(files)} files to {PRJ_FILES_TXT}")
    except Exception as e:
        print(f"Failed to save file list to {PRJ_FILES_TXT}: {e}")
    
    return files

def find_decl_end(lines: List[str], start_line: int) -> int:
    for i in range(start_line, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        if KEYWORD_PATTERN.match(line):
            return i
        if PROOF_END_RE.match(line):
            return i + 1
    return len(lines)

def stage_scan_generate(files: List[str]):
    collected_names: List[str] = []
    code_index_entries: List[str] = []
    decl_objects: List[Decl] = []

    for path in files:
        try:
            with open(path, 'r', encoding='utf-8') as f: text = f.read()
        except FileNotFoundError:
            print(f"File not found: {path}", file=sys.stderr); continue
        lines = text.splitlines()
        comments = extract_comment_blocks(text)
        decls = find_decls(lines)
        assoc = associate(decls, comments, lines)
        for kw, name, desc, line_no in assoc:
            t = normalize_kind(kw)
            safe_desc = desc.replace(',', '，')
            safe_desc = re.sub(r'\s+', ' ', safe_desc).strip()
            base = os.path.basename(path)
            line_end = find_decl_end(lines, line_no)
            entry = f"{t},{name},{safe_desc},{base},{line_no},{line_end}"
            code_index_entries.append(entry)
            collected_names.append(name)
            decl_objects.append(Decl(kind=t, raw_kind=kw, name=name, file=base, line=line_no, line_end=line_end))

    with open(CODE_INDEX_FILE, 'w', encoding='utf-8-sig') as f:
        for line in code_index_entries: f.write(line+'\n')
    with open(NAMELIST_FILE, 'w', encoding='utf-8-sig') as f:
        for name in collected_names: f.write(name+'\n')
    for line in code_index_entries: print(line)
    return decl_objects, set(collected_names)

def load_decls_from_index() -> List[Decl]:
    decls: List[Decl] = []
    try:
        with open(CODE_INDEX_FILE, 'r', encoding='utf-8') as f:
            for ln in f:
                ln = ln.rstrip('\n')
                if not ln: continue
                parts = ln.split(',')
                if len(parts) < 6: continue
                kind, name, _desc, file_name, line_no, line_end = parts[:6]
                try: 
                    lno = int(line_no)
                    lend = int(line_end)
                except ValueError: continue
                decls.append(Decl(kind=kind, raw_kind=kind, name=name, file=file_name, line=lno, line_end=lend))
    except FileNotFoundError:
        print('[ERROR] Missing code_index.txt', file=sys.stderr); sys.exit(1)
    return decls

def load_names() -> Set[str]:
    names: Set[str] = set()
    try:
        with open(NAMELIST_FILE, 'r', encoding='utf-8') as f:
            for ln in f:
                ln=ln.strip();
                if ln: names.add(ln)
    except FileNotFoundError:
        print('[ERROR] Missing namelist.txt', file=sys.stderr); sys.exit(1)
    return names

def stage_deps(decls: List[Decl], global_names: Set[str]):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    v_files = [f for f in os.listdir(current_dir) if f.endswith('.v')]
    
    source_cache: Dict[str, List[str]] = {}
    clean_cache: Dict[str, List[str]] = {}
    
    prj_files = []
    if os.path.exists(PRJ_FILES_TXT):
        try:
            with open(PRJ_FILES_TXT, 'r', encoding='utf-8') as f:
                prj_files = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"[WARN] Failed to read {PRJ_FILES_TXT}: {e}", file=sys.stderr)
    
    file_path_map = {}
    
    for full_path in prj_files:
        filename = os.path.basename(full_path)
        file_path_map[filename] = full_path
    
    for filename in v_files:
        if filename not in file_path_map:
            file_path_map[filename] = os.path.join(current_dir, filename)
    
    needed_files = sorted({d.file for d in decls})
    
    for filename in needed_files:
        if filename in file_path_map:
            full_path = file_path_map[filename]
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read().splitlines()
                        source_cache[filename] = content
                        clean_cache[filename] = strip_comments_preserve_lines(content)
                except Exception as e:
                    print(f"[WARN] Failed to read {full_path}: {e}", file=sys.stderr)
            else:
                print(f"[WARN] Source file missing: {full_path}", file=sys.stderr)
        else:
            print(f"[WARN] Unable to locate path for: {filename}", file=sys.stderr)

    results: List[Tuple[str,List[str]]] = []

    for d in decls:
        if d.file not in source_cache: continue
        lines = source_cache[d.file]
        clean = clean_cache[d.file]
        if d.line < 1 or d.line > len(lines): continue
        
        estimated_end = d.line_end
        
        stmt_end = find_statement_end(clean, d.line)
        proof_end = find_proof_end(clean, stmt_end)
        
        if proof_end is None and estimated_end > stmt_end:
            proof_end = estimated_end
        
        if proof_end is not None and proof_end > stmt_end + 1:
            body_start = stmt_end + 1
            body_end = proof_end - 1
            if body_start > body_end: body_start = body_end = stmt_end
        else:
            body_start = d.line
            body_end = stmt_end
        statement_segment = lines[d.line-1:stmt_end]
        body_segment = lines[body_start-1:body_end] if body_start <= body_end else []
        clean_statement_segment = clean[d.line-1:stmt_end]
        clean_body_segment = clean[body_start-1:body_end] if body_start <= body_end else []
        locals_ids = collect_locals(statement_segment, body_segment)
        deps = extract_dependencies(clean_statement_segment, clean_body_segment, global_names, d.name, locals_ids)
        results.append((d.name, deps))

    try:
        with open(DEPS_FILE, 'w', encoding='utf-8-sig') as f:
            for name, deps in results:
                f.write(name + '|' + ','.join(deps) + '\n')
    except OSError as e:
        print(f"[ERROR] Failed to write {DEPS_FILE}: {e}", file=sys.stderr)

    for name, deps in results:
        print(name + '|' + ','.join(deps))

    name_set = {d.name for d in decls}
    reverse: Dict[str, List[str]] = {n: [] for n in name_set}
    for src, deps in results:
        for d in deps:
            if d not in reverse:
                reverse[d] = []
            reverse[d].append(src)
    try:
        with open(REVERSE_DEPS_FILE, 'w', encoding='utf-8-sig') as f:
            for n in sorted(reverse.keys()):
                users = reverse[n]
                f.write(n + '|' + ','.join(users) + '\n')
    except OSError as e:
        print(f"[ERROR] Failed to write {REVERSE_DEPS_FILE}: {e}", file=sys.stderr)

    kind_map: Dict[str, str] = {d.name: d.kind for d in decls}
    COLOR_BY_KIND = {
        'Theorem': '#ffcccc',
        'Lemma': '#cce5ff',
        'Corollary': '#ffe5cc',
        'Proposition': '#e0e0e0',
        'Fact': '#e0e0e0',
        'Remark': '#f2f2f2',
        'Definition': '#f9f9f9',
        'Fixpoint': '#f9f9f9',
        'CoFixpoint': '#f9f9f9',
        'Inductive': '#d5f5e3',
        'CoInductive': '#d5f5e3',
        'Record': '#f0d9ff',
        'Structure': '#f0d9ff',
        'Variant': '#f0d9ff',
        'Class': '#f0d9ff',
        'Axiom': '#e8ccff',
        'Hypothesis': '#fff3cd',
        'Variable': '#fff3cd',
        'Parameter': '#fff3cd'
    }
    try:
        with open(DEPS_DOT_FILE, 'w', encoding='utf-8') as f:
            f.write('digraph CoqDeps {\n')
            f.write('  rankdir=LR;\n')
            f.write('  node [shape=box, style=filled, fontname="Helvetica", fontsize=10];\n')
            for n in sorted(name_set):
                kind = kind_map.get(n, '')
                color = COLOR_BY_KIND.get(kind, '#ffffff')
                safe_label = n.replace('"', '\"')
                f.write(f'  "{safe_label}" [fillcolor="{color}" tooltip="{kind}"];\n')
            for src, deps in results:
                for d in deps:
                    f.write(f'  "{src}" -> "{d}";\n')
            f.write('}\n')
    except OSError as e:
        print(f"[ERROR] Failed to write {DEPS_DOT_FILE}: {e}", file=sys.stderr)

def main(argv: List[str]):
    args = argv[1:]
    do_scan = True
    do_deps = True
    if '--no-deps' in args:
        do_deps = False
    if '--deps-only' in args:
        do_scan = False
    decls: List[Decl]
    global_names: Set[str]
    if do_scan:
        coq_files = get_coq_files()
        decls, global_names = stage_scan_generate(coq_files)
    else:
        decls = load_decls_from_index()
        global_names = load_names()
    if do_deps:
        stage_deps(decls, global_names)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
