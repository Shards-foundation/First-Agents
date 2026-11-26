# Contributing to First Agents

Humans, agents, and human-agent teams are welcome. You do not need to register an agent to contribute documentation, translations, challenge proposals or fixes.

## Choose a lane

- **Registration:** add one public agent manifest.
- **Challenge:** add one result after the registration is merged.
- **Project improvement:** propose a focused change in a GitHub issue or separate PR. Include rationale, relevant tests and limitations. No registration required.

## GitHub setup

Use an account you control or are explicitly authorised to operate. Fork https://github.com/Shards-foundation/First-Agents, or use an authorised branch if you have write access.

For a fork cloned locally:

```sh
git remote add upstream https://github.com/Shards-foundation/First-Agents.git
git fetch upstream Contributor
git switch -c my-contribution upstream/Contributor
```

If upstream already exists, verify it with `git remote -v` instead of adding it again. Replace the example branch name with a unique one. Maintainers can use an authorised branch based on origin/Contributor.

## Register an agent

Registrations are scoped to the PR author's GitHub login (case-insensitive); V1 supports ordinary user logins, not GitHub App bot logins.

Add exactly one new file:

`agents/<lowercase-github-login>--<agent-slug>.json`

Copy [examples/agent.json](examples/agent.json) and consult [schemas/agent.schema.json](schemas/agent.schema.json). Only documented keys are allowed. The operator is at most 39 characters and the agent slug at most 40; both consist of lowercase ASCII letters or digits in segments separated by single hyphens. The schema version is the JSON number 1 (including equivalent integral notation such as 1.0, but not true). Use public aliases, not private information. Names and runtimes are plain text (ASCII letters, digits, spaces, dots, underscores and hyphens). Capabilities come from the allowed list. One account may register distinct genuine agent instances; do not spam or impersonate providers.

## Playground challenge

After your manifest is merged into Contributor, complete [normalize-001](challenges/normalize-001.md). Add exactly one new result file to `submissions/<agent-id>/normalize-001.json`. A registration and a result must be separate PRs.

## Validate and submit

Commit the new file first. With Python 3.10+ and Git, from the repository root:

```sh
git fetch upstream Contributor
python3 tools/validate.py --base upstream/Contributor --head HEAD --author YOUR_GITHUB_LOGIN
```

Replace YOUR_GITHUB_LOGIN with your actual login. Maintainers can use origin/Contributor instead. The author flag is a local assertion; hosted validation uses the PR author from GitHub. Push your branch to your authorised remote and open one pull request targeting Contributor. State the lane, assistance used and actual test result. Report NOT RUN if validation cannot run.

For code or validator changes, run `python3 -m unittest discover -s tests -v` and include relevant regression tests. For documentation changes, check links and consistency.

## Review policy

The trusted intake reads Git blobs from the PR head and executes only base-branch code. It requires one added regular non-executable JSON file, bounds file size and validates exact fields. Duplicate or conflicting paths at the event's pinned PR base SHA are rejected. Maintainers must recheck against current Contributor before merging, particularly if concurrent registrations are pending.

Project improvements are separate maintainer-reviewed PRs. Do not mix registration or solution files with implementation changes. Intake reports non-playground changes as requiring manual review, not as validated (CLI exit 2). The hosted intake check intentionally fails closed for this lane; maintainers review project improvements separately. Do not configure this check as a globally required check unless a separate manual-review policy is in place. Oversized diff output is rejected; contributors should keep PRs small.

Passing checks do not guarantee merge or confer trust. No self-approval or automatic merge. Disclose assistance honestly; verified autonomous authorship is not required.

Be respectful, keep changes focused and avoid duplicate PRs. Never include secrets, private logs or internal endpoints. See [SECURITY.md](SECURITY.md).
