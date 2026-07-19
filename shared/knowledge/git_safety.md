# Git Safety Rules (Global)

## Active Protections
- **Pre-commit hook**: Blocks merge conflict markers, .env files, secrets, warns on large files/debug code
- **Pre-push hook**: Blocks direct push to main/master (use feature branches)
- **Global .gitignore**: Python caches, venv, IDE files, secrets, build artifacts
- **Commit template**: Conventional commit format (feat:, fix:, chore:, etc.)

## Key Config
- Pull rebase: enabled (no merge commits)
- Merge conflict style: diff3 (shows yours + theirs + common ancestor)
- Push auto-setup remote: true
- Rebase auto-stash: true
- LFS: configured for large binary files

## Agent Rules
1. NEVER push to main/master directly (hook will block it anyway)
2. ALWAYS use feature branches: git switch -c feature/<name>
3. NEVER commit secrets or .env files
4. Run `git status` and `git diff` before committing
5. Use `git undo` (not reset --hard) to undo commits
6. Use `git lg` to see branch history
7. Use `git cleanup` to delete merged branches

## Bypass (Emergency Only)
- git commit --no-verify  (skip pre-commit)
- git push --no-verify    (skip pre-push)
