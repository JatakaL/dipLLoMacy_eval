#!/usr/bin/env python3
"""
Output Utilities for Map Generation

This module provides utilities for managing output paths and filenames
with datetime stamping, supporting both orchestrator and individual phase execution.
"""

import os
from datetime import datetime
from pathlib import Path


def get_default_output_base():
    """
    Get the default base output directory.
    
    By default, this is one level above the git repository root.
    
    Returns:
        Path to the default output base directory
    """
    # Get the directory containing this file (map_gen/phases/)
    current_file = Path(__file__).resolve()
    phases_dir = current_file.parent
    map_gen_dir = phases_dir.parent
    repo_root = map_gen_dir.parent
    
    # Go one level above the repo root
    default_base = repo_root.parent / "map_output"
    
    return str(default_base)


def get_output_base_dir(custom_base=None):
    """
    Get the base output directory, using custom path if provided.
    
    Args:
        custom_base: Optional custom base directory path
        
    Returns:
        Path to the base output directory
    """
    if custom_base:
        return custom_base
    return get_default_output_base()


def create_datetime_subdir(base_dir, datetime_str=None):
    """
    Create a datetime-stamped subdirectory within the base directory.
    
    Args:
        base_dir: Base output directory
        datetime_str: Optional datetime string (format: YYYYMMDD_HHMMSS)
                     If None, generates current datetime
        
    Returns:
        Tuple of (full_path_to_subdir, datetime_string_used)
    """
    if datetime_str is None:
        datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_dir = Path(base_dir) / datetime_str
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return str(output_dir), datetime_str


def get_datetime_filename(base_name, datetime_str=None, extension=".json"):
    """
    Generate a filename with datetime stamp.
    
    Args:
        base_name: Base name for the file (e.g., "phase1_mesh_output")
        datetime_str: Optional datetime string (format: YYYYMMDD_HHMMSS)
                     If None, generates current datetime
        extension: File extension (default: ".json")
        
    Returns:
        Tuple of (filename_with_datetime, datetime_string_used)
    """
    if datetime_str is None:
        datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Remove extension from base_name if present
    base_name_no_ext = base_name.rsplit('.', 1)[0]
    
    # Create filename: base_name_YYYYMMDD_HHMMSS.extension
    filename = f"{base_name_no_ext}_{datetime_str}{extension}"
    
    return filename, datetime_str


def extract_datetime_from_path(file_path):
    """
    Extract datetime string from a file path or filename.
    
    Looks for patterns like YYYYMMDD_HHMMSS in the path.
    
    Args:
        file_path: Path to a file (can be filename or full path)
        
    Returns:
        Datetime string if found, None otherwise
    """
    import re
    
    # Pattern to match YYYYMMDD_HHMMSS
    pattern = r'(\d{8}_\d{6})'
    
    path_str = str(file_path)
    match = re.search(pattern, path_str)
    
    if match:
        return match.group(1)
    
    return None


def get_input_directory(input_file):
    """
    Get the directory containing the input file.
    
    Args:
        input_file: Path to input file
        
    Returns:
        Directory path containing the input file
    """
    input_path = Path(input_file).resolve()
    return str(input_path.parent)


def get_output_path_for_phase(phase_name, input_file=None, base_dir=None, 
                               datetime_str=None, is_orchestrator=False):
    """
    Get the complete output path for a phase.
    
    This function handles the logic for determining where output files should go:
    - Orchestrator mode: Uses base_dir/datetime_str/
    - Phase 1 standalone: Creates new datetime_str subdirectory
    - Phase 2+ standalone: Uses same directory as input_file
    
    Args:
        phase_name: Name of the phase (e.g., "phase1_mesh")
        input_file: Path to input file (for phases 2+)
        base_dir: Base output directory (for orchestrator and phase 1)
        datetime_str: Datetime string to use (for orchestrator)
        is_orchestrator: Whether running in orchestrator mode
        
    Returns:
        Tuple of (output_directory, datetime_string, full_output_path)
    """
    if is_orchestrator:
        # Orchestrator mode: use base_dir and provided datetime_str
        if base_dir is None:
            base_dir = get_default_output_base()
        if datetime_str is None:
            datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_dir, dt_str = create_datetime_subdir(base_dir, datetime_str)
        filename, _ = get_datetime_filename(phase_name, dt_str)
        full_path = os.path.join(output_dir, filename)
        
        return output_dir, dt_str, full_path
    
    elif phase_name == "phase1_mesh" or input_file is None:
        # Phase 1 standalone: create new datetime subdirectory
        if base_dir is None:
            base_dir = get_default_output_base()
        
        # Generate new datetime
        dt_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir, dt_str = create_datetime_subdir(base_dir, dt_str)
        filename, _ = get_datetime_filename(phase_name, dt_str)
        full_path = os.path.join(output_dir, filename)
        
        return output_dir, dt_str, full_path
    
    else:
        # Phase 2+ standalone: use same directory as input file
        output_dir = get_input_directory(input_file)
        
        # Generate new datetime for this phase
        dt_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename, _ = get_datetime_filename(phase_name, dt_str)
        full_path = os.path.join(output_dir, filename)
        
        return output_dir, dt_str, full_path
