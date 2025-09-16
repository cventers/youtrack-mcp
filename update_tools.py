#!/usr/bin/env python3
"""
Script to update YouTrack MCP tools to remove legacy wrappers and use typed functions.
"""

import os
import re
import glob

def update_file(filepath):
    """Update a single file to remove wrappers and use typed functions."""
    print(f"Updating {filepath}")

    with open(filepath, 'r') as f:
        content = f.read()

    # Remove import lines
    content = re.sub(r'from youtrack_mcp\.mcp_wrappers import.*\n', '', content)
    content = re.sub(r'from youtrack_mcp\.utils import format_json_response\n', '', content)

    # Remove decorators
    content = re.sub(r'\s*@async_wrapper\n', '', content)
    content = re.sub(r'\s*@sync_wrapper\n', '', content)

    # Change return types from str to dict
    content = re.sub(r'-> str:', '-> dict:', content)

    # Replace format_json_response calls with direct dict returns
    content = re.sub(r'return format_json_response\((.*?)\)', r'return \1', content, flags=re.DOTALL)

    # For error_educator returns, they already return dict so no change needed
    # But we need to handle cases where format_json_response is called on error_educator results
    content = re.sub(r'return format_json_response\((\w+_response)\)', r'return \1', content)

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"Updated {filepath}")

def main():
    """Main function to update all tool files."""
    # Find all Python files in tools directory that import mcp_wrappers
    tools_dir = "youtrack_mcp/tools"
    pattern = os.path.join(tools_dir, "**", "*.py")

    updated_files = []
    for filepath in glob.glob(pattern, recursive=True):
        with open(filepath, 'r') as f:
            content = f.read()

        if 'from youtrack_mcp.mcp_wrappers import' in content:
            update_file(filepath)
            updated_files.append(filepath)

    print(f"\nUpdated {len(updated_files)} files:")
    for f in updated_files:
        print(f"  {f}")

if __name__ == "__main__":
    main()