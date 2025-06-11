#!/usr/bin/env python3
"""
Example Background Agent for Git Operations
"""

import subprocess
import datetime
import os

def run_git_command(cmd):
    """Run a git command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Git command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        print(f"✅ {cmd}")
        return True
    except Exception as e:
        print(f"Exception: {e}")
        return False

def deploy_changes(branch_name=None, commit_message=None):
    """Deploy changes using Git operations."""
    
    # Generate branch name if not provided
    if not branch_name:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"agent-update-{timestamp}"
    
    # Generate commit message if not provided
    if not commit_message:
        commit_message = f"Automated update from background agent - {datetime.datetime.now()}"
    
    print(f"🤖 Starting deployment to branch: {branch_name}")
    
    # Git operations sequence
    commands = [
        "git fetch origin",
        "git checkout main",
        "git pull origin main",
        f"git checkout -b {branch_name}",
        "git add .",
        f'git commit -m "{commit_message}"',
        f"git push origin {branch_name}"
    ]
    
    for cmd in commands:
        if not run_git_command(cmd):
            print(f"❌ Deployment failed at: {cmd}")
            return False
    
    print(f"✅ Successfully deployed to branch: {branch_name}")
    print(f"🔗 Create PR: https://github.com/rlpride/dpc-health-insurance-lead-generation-system/compare/{branch_name}")
    return True

if __name__ == "__main__":
    # Example usage
    deploy_changes(
        commit_message="Background agent: Updated lead generation data"
    ) 