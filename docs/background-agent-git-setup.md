# Background Agent Git Authentication Setup

This guide explains how to set up Git authentication for background agents so they can perform automated Git operations (branching, committing, pushing, merging).

## Prerequisites

1. **GitHub Repository**: Your project is connected to `https://github.com/rlpride/dpc-health-insurance-lead-generation-system.git`
2. **GitHub Account**: You need access to create Personal Access Tokens

## Step 1: Create GitHub Personal Access Token

1. Go to [GitHub Personal Access Tokens](https://github.com/settings/personal-access-tokens/tokens)
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Configure the token:
   - **Token name**: `Background-Agent-DPC-Health-Insurance`
   - **Expiration**: 90 days (recommended for security)
   - **Scopes** (select these):
     - ✅ `repo` (Full control of private repositories)
     - ✅ `workflow` (Update GitHub Action workflows)
     - ✅ `write:packages` (if using GitHub packages)

4. Click **"Generate token"**
5. **IMPORTANT**: Copy the token immediately (you won't see it again!)

## Step 2: Set Up Environment

Add the GitHub token to your environment:

```bash
# Add to your environment or .env file
export GITHUB_TOKEN=your_personal_access_token_here
```

## Step 3: Run Setup Script

Use the provided setup script to configure Git authentication:

```bash
# Make sure GITHUB_TOKEN is set
export GITHUB_TOKEN=your_token_here

# Run the setup script
python scripts/setup_git_auth.py
```

This script will:
- Configure Git with appropriate user settings for agents
- Set up credential storage
- Test the authentication
- Create an example background agent script

## Step 4: Background Agent Usage

Once set up, your background agents can perform Git operations:

```python
#!/usr/bin/env python3
import subprocess
import datetime

def deploy_changes():
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"agent-update-{timestamp}"
    
    commands = [
        "git fetch origin",
        "git checkout main", 
        "git pull origin main",
        f"git checkout -b {branch_name}",
        "git add .",
        f'git commit -m "Automated update from background agent"',
        f"git push origin {branch_name}"
    ]
    
    for cmd in commands:
        subprocess.run(cmd, shell=True, check=True)
    
    print(f"✅ Deployed to branch: {branch_name}")
    return branch_name
```

## Example Background Agent Operations

The setup creates an example script at `scripts/example_background_agent.py` that demonstrates:

- **Branching**: Create feature branches with timestamps
- **Adding**: Stage all changes
- **Committing**: Commit with automated messages
- **Pushing**: Push to remote repository
- **PR Creation**: Generate GitHub PR URLs

## Security Best Practices

1. **Token Rotation**: Rotate tokens every 90 days
2. **Minimal Permissions**: Only grant necessary scopes
3. **Environment Variables**: Store tokens in environment variables, not code
4. **Monitoring**: Monitor agent activities in GitHub
5. **Backup Authentication**: Have multiple tokens for different environments

## Troubleshooting

### Authentication Failed
- Verify `GITHUB_TOKEN` is set correctly
- Check token hasn't expired
- Ensure token has required permissions

### Permission Denied
- Verify token has `repo` scope
- Check repository permissions
- Ensure you're pushing to the correct remote

### Rate Limiting
- GitHub has rate limits for API calls
- Implement backoff strategies in your agents
- Consider using GitHub Apps for higher limits

## Environment Variables Reference

Add these to your environment configuration:

```bash
# Required for background agents
GITHUB_TOKEN=your_personal_access_token_here

# Optional: Custom Git settings
GIT_AUTHOR_NAME="Background Agent"
GIT_AUTHOR_EMAIL="agent@dpc-health.com"
GIT_COMMITTER_NAME="Background Agent"  
GIT_COMMITTER_EMAIL="agent@dpc-health.com"
```

## Next Steps

1. Run the setup script
2. Test with the example agent
3. Integrate Git operations into your background processes
4. Set up monitoring for automated commits
5. Consider implementing PR-based workflows for review 