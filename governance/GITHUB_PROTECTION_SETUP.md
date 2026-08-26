# GitHub Protection Setup

These settings are instructions for the human repository owner. They are not evidence that the settings are currently active.

After reviewing the foundation commit and creating the `foundation-v1` tag:

1. Set `main` as the default branch and protect it under **Settings → Branches → Branch protection rules** or the repository ruleset UI.
2. Require pull requests before merging and restrict direct pushes to `main` where the plan supports it.
3. Require at least one approving human review; require review from `CODEOWNERS` for protected files if the repository plan supports CODEOWNER rules.
4. Require the `Research integrity / integrity` status check before merging.
5. Disable force pushes and branch deletion for `main`.
6. Restrict who can dismiss reviews and bypass required checks. Keep repository administration limited to trusted humans.
7. Preserve tags or create a protected tag rule for `foundation-v1` and later foundation-version tags.

Verify the resulting settings in the GitHub UI or API and record that verification separately. Do not claim they are active merely because this file exists. Repository-local controls cannot prevent a GitHub administrator from bypassing them.
