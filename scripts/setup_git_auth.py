#!/usr/bin/env python3
"""
Git Authentication Setup for Background Agents
This script configures Git to use Personal Access Tokens for automated operations.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, capture_output=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        return result.stdout.strip() if capture_output else True
    except Exception as e:
        print(f"Exception running command {cmd}: {e}")
        return False

def setup_git_credentials(github_token, username="background-agent", email="agent@dpc-health.com"):
    """Configure Git with credentials for background agents."""
    
    print("🔧 Configuring Git for background agents...")
    
    # Set up user info
    commands = [
        f'git config --global user.name "{username}"',
        f'git config --global user.email "{email}"',
        'git config --global credential.helper store',
        'git config --global init.defaultBranch main'
    ]
    
    for cmd in commands:
        if not run_command(cmd):
            print(f"❌ Failed to execute: {cmd}")
            return False
    
    # Store credentials securely
    git_credentials_path = Path.home() / '.git-credentials'
    credential_line = f"https://{username}:{github_token}@github.com"
    
    # Check if credentials already exist
    existing_credentials = []
    if git_credentials_path.exists():
        with open(git_credentials_path, 'r') as f:
            existing_credentials = f.readlines()
    
    # Remove any existing GitHub credentials
    filtered_credentials = [line for line in existing_credentials if 'github.com' not in line]
    
    # Add new credentials
    filtered_credentials.append(credential_line + '\n')
    
    # Write credentials file
    try:
        with open(git_credentials_path, 'w') as f:
            f.writelines(filtered_credentials)
        
        # Set secure permissions
        os.chmod(git_credentials_path, 0o600)
        print("✅ Git credentials configured successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to write credentials: {e}")
        return False

def test_git_access():
    """Test if Git access is working properly."""
    print("\n🧪 Testing Git access...")
    
    # Test git config
    username = run_command("git config --global user.name")
    email = run_command("git config --global user.email")
    
    print(f"Git user: {username}")
    print(f"Git email: {email}")
    
    # Test remote access
    print("Testing remote repository access...")
    if run_command("git ls-remote origin"):
        print("✅ Successfully authenticated with GitHub!")
        return True
    else:
        print("❌ Failed to authenticate with GitHub")
        return False

def create_example_agent_script():
    """Create an example background agent script."""
    
    agent_script = '''#!/usr/bin/env python3
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
'''
    
    script_path = Path("scripts/example_background_agent.py")
    script_path.parent.mkdir(exist_ok=True)
    
    with open(script_path, 'w') as f:
        f.write(agent_script)
    
    os.chmod(script_path, 0o755)
    print(f"📝 Created example agent script: {script_path}")

def main():
    """Main setup function."""
    print("🚀 Background Agent Git Authentication Setup")
    print("=" * 50)
    
    # Get GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable not set!")
        print("\nPlease:")
        print("1. Create a Personal Access Token at: https://github.com/settings/personal-access-tokens/tokens")
        print("2. Set it as an environment variable: export GITHUB_TOKEN=your_token_here")
        print("3. Run this script again")
        sys.exit(1)
    
    # Setup credentials
    if setup_git_credentials(github_token):
        # Test access
        if test_git_access():
            # Create example script
            create_example_agent_script()
            print("\n🎉 Setup complete!")
            print("\nNext steps:")
            print("1. Your background agents can now use Git operations")
            print("2. Check the example script: scripts/example_background_agent.py")
            print("3. Set GITHUB_TOKEN environment variable in your agent environments")
        else:
            print("❌ Setup completed but authentication test failed")
    else:
        print("❌ Setup failed")

if __name__ == "__main__":
    main() 