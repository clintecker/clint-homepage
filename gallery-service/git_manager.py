"""GitHub repository management for gallery commits"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

import frontmatter
from git import Repo
from datetime import datetime


class GitManager:
    """Manages git operations for gallery creation"""

    def __init__(self, repo_url: str, github_token: str):
        self.repo_url = repo_url
        self.github_token = github_token

        # Convert SSH URL to HTTPS with token if needed
        if repo_url.startswith('git@github.com:'):
            # Convert git@github.com:user/repo.git to https://token@github.com/user/repo.git
            repo_path = repo_url.replace('git@github.com:', '').replace('.git', '')
            self.repo_url_with_auth = f"https://{github_token}@github.com/{repo_path}.git"
        else:
            self.repo_url_with_auth = repo_url

    def create_gallery_commit(self, gallery_data: Dict[str, Any]) -> str:
        """Create gallery markdown file and commit to GitHub

        Returns: commit SHA
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Clone repo
            repo = Repo.clone_from(
                self.repo_url_with_auth,
                temp_path,
                depth=1,
                branch='main'
            )

            # Create gallery markdown file
            date = datetime.fromisoformat(gallery_data['date'])
            filename = f"{date.strftime('%Y-%m-%d')}-{gallery_data['slug']}.md"
            gallery_path = temp_path / 'content' / 'galleries' / filename

            # Ensure directory exists
            gallery_path.parent.mkdir(parents=True, exist_ok=True)

            # Create frontmatter
            post = frontmatter.Post(gallery_data.get('description', ''))
            post['title'] = gallery_data['title']
            post['date'] = gallery_data['date']
            post['slug'] = gallery_data['slug']
            post['tags'] = gallery_data.get('tags', [])
            post['type'] = 'gallery'
            post['photos'] = gallery_data['photos']

            # Write file
            with open(gallery_path, 'w') as f:
                f.write(frontmatter.dumps(post))

            # Git operations
            repo.index.add([str(gallery_path.relative_to(temp_path))])

            commit_message = f"""Add gallery: {gallery_data['title']}

{len(gallery_data['photos'])} photos

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

            repo.index.commit(commit_message)

            # Configure git user
            with repo.config_writer() as config:
                config.set_value("user", "name", "Gallery Service")
                config.set_value("user", "email", "gallery@clintecker.com")

            # Push
            origin = repo.remote('origin')
            origin.push('main:main')

            return repo.head.commit.hexsha
