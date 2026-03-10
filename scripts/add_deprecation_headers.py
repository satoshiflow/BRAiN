#!/usr/bin/env python3
"""
Add deprecation headers to Wave-1 execution consolidation modules.
Part of: Execution Consolidation Plan (Block A1)
"""

import os
import sys
from pathlib import Path

PYTHON_HEADER = '''# ============================================================================
# DEPRECATION NOTICE (Execution Consolidation Wave 1)
# Module role will be reduced/replaced by OpenCode execution plane.
#
# Status: PLANNED_FOR_DEPRECATION
# Owner: BRAiN Runtime / OpenCode Integration
# Replacement Target: {replacement_target}
# Sunset Phase: {sunset_phase}
# Rule: Do not add new features here. Only critical fixes allowed.
# See: docs/specs/opencode_execution_consolidation_plan.md
# ============================================================================

'''

MD_HEADER = '''> **DEPRECATION NOTICE (Execution Consolidation Wave 1)**  
> Status: PLANNED_FOR_DEPRECATION  
> Replacement Target: {replacement_target}  
> Sunset Phase: {sunset_phase}  
> Rule: No new feature work; critical fixes only.  
> See: `docs/specs/opencode_execution_consolidation_plan.md`

'''

# Wave-1 targets
WAVE1_TARGETS = {
    # factory_executor
    'backend/app/modules/factory_executor/base.py': {
        'replacement': 'opencode worker job contracts',
        'sunset': 'wave1-factory-executor'
    },
    'backend/app/modules/factory_executor/executor.py': {
        'replacement': 'opencode worker job contracts',
        'sunset': 'wave1-factory-executor'
    },
    'backend/app/modules/factory_executor/preflight.py': {
        'replacement': 'opencode worker job contracts',
        'sunset': 'wave1-factory-executor'
    },
    'backend/app/modules/factory_executor/rollback_manager.py': {
        'replacement': 'opencode worker job contracts',
        'sunset': 'wave1-factory-executor'
    },
    'backend/app/modules/factory_executor/__init__.py': {
        'replacement': 'opencode worker job contracts',
        'sunset': 'wave1-factory-executor'
    },
    
    # webgenesis execution layer
    'backend/app/modules/webgenesis/service.py': {
        'replacement': 'opencode worker (build/deploy/rollback)',
        'sunset': 'wave1-webgenesis-exec'
    },
    'backend/app/modules/webgenesis/ops_service.py': {
        'replacement': 'opencode worker (build/deploy/rollback)',
        'sunset': 'wave1-webgenesis-exec'
    },
    'backend/app/modules/webgenesis/releases.py': {
        'replacement': 'opencode worker (build/deploy/rollback)',
        'sunset': 'wave1-webgenesis-exec'
    },
    'backend/app/modules/webgenesis/rollback.py': {
        'replacement': 'opencode worker (build/deploy/rollback)',
        'sunset': 'wave1-webgenesis-exec'
    },
    'backend/app/modules/webgenesis/router.py': {
        'replacement': 'opencode worker (build/deploy/rollback)',
        'sunset': 'wave1-webgenesis-exec'
    },
    'backend/app/modules/webgenesis/README.md': {
        'replacement': 'opencode worker (build/deploy/rollback)',
        'sunset': 'wave1-webgenesis-exec'
    },
    
    # course_factory bridge
    'backend/app/modules/course_factory/webgenesis_integration.py': {
        'replacement': 'course_factory -> runtime job contract -> opencode',
        'sunset': 'wave1-course-bridge'
    },
}


def has_deprecation_header(content: str) -> bool:
    """Check if file already has deprecation notice."""
    return 'DEPRECATION NOTICE (Execution Consolidation Wave 1)' in content


def add_header_to_python(filepath: Path, replacement: str, sunset: str) -> bool:
    """Add deprecation header to Python file."""
    content = filepath.read_text()
    
    if has_deprecation_header(content):
        print(f"  ⊘ Already has header: {filepath}")
        return False
    
    header = PYTHON_HEADER.format(
        replacement_target=replacement,
        sunset_phase=sunset
    )
    
    # Insert after module docstring if present
    if content.startswith('"""') or content.startswith("'''"):
        # Find end of docstring
        quote = '"""' if content.startswith('"""') else "'''"
        end_idx = content.find(quote, 3) + 3
        
        new_content = content[:end_idx] + '\n\n' + header + content[end_idx:]
    else:
        # No docstring, add at top
        new_content = header + content
    
    filepath.write_text(new_content)
    print(f"  ✓ Added header: {filepath}")
    return True


def add_header_to_markdown(filepath: Path, replacement: str, sunset: str) -> bool:
    """Add deprecation header to Markdown file."""
    content = filepath.read_text()
    
    if has_deprecation_header(content):
        print(f"  ⊘ Already has header: {filepath}")
        return False
    
    header = MD_HEADER.format(
        replacement_target=replacement,
        sunset_phase=sunset
    )
    
    # Add at top (after title if present)
    lines = content.split('\n')
    if lines and lines[0].startswith('#'):
        # Has title, add after it
        new_content = lines[0] + '\n\n' + header + '\n'.join(lines[1:])
    else:
        new_content = header + content
    
    filepath.write_text(new_content)
    print(f"  ✓ Added header: {filepath}")
    return True


def main():
    root = Path(__file__).parent.parent
    added_count = 0
    skipped_count = 0
    
    print("🏷️  Adding Wave-1 deprecation headers...")
    print()
    
    for rel_path, config in WAVE1_TARGETS.items():
        filepath = root / rel_path
        
        if not filepath.exists():
            print(f"  ⚠️  Not found: {filepath}")
            continue
        
        if filepath.suffix == '.py':
            if add_header_to_python(filepath, config['replacement'], config['sunset']):
                added_count += 1
            else:
                skipped_count += 1
        elif filepath.suffix == '.md':
            if add_header_to_markdown(filepath, config['replacement'], config['sunset']):
                added_count += 1
            else:
                skipped_count += 1
    
    print()
    print(f"✅ Done: {added_count} headers added, {skipped_count} already present")
    
    if added_count == 0 and skipped_count == 0:
        print("❌ No files processed")
        sys.exit(1)


if __name__ == '__main__':
    main()
