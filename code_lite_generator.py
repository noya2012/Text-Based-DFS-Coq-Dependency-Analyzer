#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collatz Lite Code Generator
======================
Functionality:
 1. Read file list from prj_files.txt and process files one by one
 2. Remove the content between proof and qed in each file
 3. Merge processed code and output to code_lite.txt file

Description:
 - Remove proof sections, keep theorem statements and definitions
 - Maintain original file structure order
 - Output file uses UTF-8 encoding

Usage:
 python collatz_lite_generator.py
"""

import os
import re
from typing import List, Tuple

# Script directory (where this script is located)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Project root directory (parent of SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Project file list path
PRJ_FILES_PATH = os.path.join(SCRIPT_DIR, 'prj_files.txt')
# Output file path
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'code_lite.txt')

def load_project_files() -> List[str]:
    """
    Load project file list from prj_files.txt
    
    Returns:
        List of file paths
    """
    try:
        if not os.path.exists(PRJ_FILES_PATH):
            print(f"Error: Project file list {PRJ_FILES_PATH} does not exist")
            return []
        
        with open(PRJ_FILES_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter empty lines and comments, and process path format
        file_paths = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Convert path to current system format
                normalized_path = line.replace('/', os.sep).replace('\\', os.sep)
                # If path is absolute, use directly; otherwise relative to script directory
                if os.path.isabs(normalized_path):
                    file_paths.append(normalized_path)
                else:
                    file_paths.append(os.path.join(SCRIPT_DIR, normalized_path))
        
        print(f"Loaded {len(file_paths)} files from {PRJ_FILES_PATH}")
        return file_paths
        
    except Exception as e:
        print(f"Error loading project file list: {str(e)}")
        return []

def remove_proof_sections(content: str) -> str:
    """Remove proof blocks, leaving only statements and definitions."""
    # Use regex to match proof...qed sections, allowing either case for the keywords
    pattern = r'(\b[Pp]roof\b)(.*?)(\b[Qq]ed\b)'

    def replace_proof(match):
        # Remove the entire matched block and leave a blank line for structure
        return '\n'

    # DOTALL mode lets "." match newline characters
    result = re.sub(pattern, replace_proof, content, flags=re.DOTALL)

    return result

def process_coq_file(file_path: str) -> Tuple[bool, str, str]:
    """Process a single Coq file and strip its proof sections."""
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            return False, file_path, f"File does not exist: {file_path}"
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove proof sections
        processed_content = remove_proof_sections(content)
        
        return True, os.path.basename(file_path), processed_content
        
    except Exception as e:
        return False, file_path, f"Error processing file: {str(e)}"

def generate_collatz_lite():
    """Generate collatzlite.txt by aggregating processed Coq files."""
    print("Starting to generate Collatz Lite code...")
    
    # Load project file list
    project_files = load_project_files()
    if not project_files:
        print("Error: Unable to load project file list, generation failed")
        return False
    
    all_content = []
    processed_count = 0
    error_files = []
    
    # Process files one by one
    for file_path in project_files:
        print(f"Processing: {file_path}")
        
        success, base_name, content = process_coq_file(file_path)
        
        if success:
            # Add file separator and filename title
            all_content.append(f"\n{'='*60}\n")
            all_content.append(f"File: {base_name}\n")
            all_content.append(f"{'='*60}\n\n")
            all_content.append(content)
            processed_count += 1
            print(f"  ✓ Successfully processed")
        else:
            error_files.append((base_name, content))
            print(f"  ✗ Processing failed: {content}")
    
    # Write to output file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # Write file header
            f.write("Code Lite\n")
            f.write("=" * 50 + "\n")
            f.write("Description: This file contains Coq code with proof sections removed\n")
            f.write(f"Processed files: {processed_count}\n")
            f.write(f"Failed files: {len(error_files)}\n\n")
            
            # Write processing results
            f.write(''.join(all_content))
            
            # If there are error files, write error information
            if error_files:
                f.write("\n" + "=" * 60 + "\n")
                f.write("Failed files:\n")
                for file_name, error_msg in error_files:
                    f.write(f"  - {file_name}: {error_msg}\n")
        
        print(f"\nGeneration completed!")
        print(f"Successfully processed files: {processed_count}")
        print(f"Failed files: {len(error_files)}")
        print(f"Output file: {OUTPUT_FILE}")
        
        if error_files:
            print("\nList of failed files:")
            for file_name, error_msg in error_files:
                print(f"  - {file_name}: {error_msg}")
                
    except Exception as e:
        print(f"Error writing to output file: {str(e)}")
        return False
    
    return True

def remove_extra_empty_lines(content: str) -> str:
    """Drop redundant empty lines while keeping lines that contain a period."""
    lines = content.split('\n')
    result_lines = []
    
    for line in lines:
        # Keep lines that contain a period or any non-empty line
        if '.' in line.strip() or line.strip():
            result_lines.append(line)
    
    return '\n'.join(result_lines)

def post_process_output_file():
    """Perform secondary processing to trim extra empty lines in the output file."""
    try:
        # Check if the output file exists
        if not os.path.exists(OUTPUT_FILE):
            print(f"Warning: Output file {OUTPUT_FILE} does not exist, skipping secondary processing")
            return False
        
        # Read output file content
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove extra empty lines
        processed_content = remove_extra_empty_lines(content)
        
        # Write back to file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        print(f"✓ Secondary processing completed: Removed extra empty lines, keeping only lines with periods")
        return True
        
    except Exception as e:
        print(f"✗ Secondary processing failed: {str(e)}")
        return False


def main():
    """Entry point for the Collatz Lite generator."""
    print(" Lite Code Generator")
    print("=" * 50)
    
    # Generate code
    success = generate_collatz_lite()
    
    if success:
        # Perform secondary processing
        print("\nStarting secondary processing...")
        post_process_success = post_process_output_file()
        
        if post_process_success:
            print("\nTask completed!")
            print(f"Generated file: {OUTPUT_FILE}")
        else:
            print("\nTask completed (secondary processing failed)!")
    else:
        print("\nTask failed!")
        return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
