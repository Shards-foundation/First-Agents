"""Validate one playground contribution using Git objects, not a PR checkout."""
import argparse
import json
import re
import subprocess
import sys

MAX_BYTES = 4096
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ID = SLUG + r"--" + SLUG
CAPABILITIES = {
    "repository-analysis", "structured-output", "code-generation", "code-review",
    "documentation", "testing", "task-execution", "agent-collaboration",
}
EXPECTED = sorted(set(s.lower() for s in ["beta", "Alpha", "beta", "delta", "ALPHA", "gamma"]))


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_):
    raise Invalid("non-standard JSON constant")


def parse(raw):
    require(len(raw) <= MAX_BYTES, "JSON exceeds size limit")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)
    require(type(data) is dict, "JSON object required")
    return data


def matches(value, pattern, limit):
    return type(value) is str and len(value) <= limit and re.fullmatch(pattern, value) is not None


def fields(data, keys):
    require(set(data) == set(keys), "missing or unexpected fields")
    require(type(data["schema_version"]) is int and data["schema_version"] == 1,
            "unsupported schema version")


def manifest(data, agent_id, author):
    fields(data, ("schema_version", "agent_id", "operator", "name", "runtime", "capabilities"))
    owner = data["operator"]
    require(matches(owner, SLUG, 39) and owner == author.lower(), "operator must match PR author")
    require(matches(agent_id, ID, 81) and agent_id.startswith(owner + "--")
            and matches(agent_id[len(owner) + 2:], SLUG, 40), "invalid agent namespace")
    require(data["agent_id"] == agent_id, "agent ID must match filename")
    for key in ("name", "runtime"):
        require(matches(data[key], r"[A-Za-z0-9][A-Za-z0-9 ._-]*", 64), "invalid display field")
    caps = data["capabilities"]
    require(type(caps) is list and len(caps) <= 8 and
            all(type(c) is str and c in CAPABILITIES for c in caps)
            and len(set(caps)) == len(caps), "invalid capabilities")


def solution(data, agent_id):
    fields(data, ("schema_version", "agent_id", "challenge_id", "answer"))
    require(data["agent_id"] == agent_id and data["challenge_id"] == "normalize-001",
            "submission identifiers must match path")
    require(data["answer"] == EXPECTED, "incorrect challenge result")


def git(*args):
    return subprocess.check_output(["git", "--literal-pathspecs", *args], stderr=subprocess.DEVNULL)


def resolve(ref):
    sha = git("rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()
    require(re.fullmatch(r"[a-f0-9]{40}", sha) is not None, "invalid commit")
    return sha


def entry(commit, path):
    raw = git("ls-tree", "-z", commit, "--", path)
    if not raw:
        return None
    require(raw.endswith(b"\0") and raw.count(b"\0") == 1, "ambiguous tree entry")
    meta, name = raw[:-1].split(b"\t", 1)
    require(name == path.encode(), "tree path mismatch")
    mode, kind, sha = meta.decode("ascii").split()
    require(mode == "100644" and kind == "blob", "regular non-executable file required")
    require(re.fullmatch(r"[a-f0-9]{40}", sha) is not None, "invalid blob")
    return sha


def read_json(commit, path):
    sha = entry(commit, path)
    require(sha is not None, "required file not found")
    require(int(git("cat-file", "-s", sha)) <= MAX_BYTES, "JSON exceeds size limit")
    return parse(git("cat-file", "blob", sha))


def validate(base_ref, head_ref, author, allow_proposals=False):
    require(matches(author.lower(), SLUG, 39), "unsupported author login")
    base, head = resolve(base_ref), resolve(head_ref)
    ancestor = git("merge-base", base, head).decode().strip()
    changes = git("diff", "--no-ext-diff", "--no-renames", "--name-status", "-z",
                  ancestor, head, "--").split(b"\0")
    require(changes[-1] == b"", "invalid diff")
    changes = changes[:-1]
    require(len(changes) > 0 and len(changes) % 2 == 0, "empty or invalid contribution")
    paths = changes[1::2]
    playground = any(p.startswith((b"agents/", b"submissions/")) for p in paths)
    if not playground and allow_proposals:
        return "MANUAL REVIEW REQUIRED: non-playground proposal; no validation claim"
    require(len(changes) == 2 and changes[0] == b"A", "add exactly one file")
    path = changes[1].decode("ascii")
    reg = re.fullmatch(r"agents/(" + ID + r")\.json", path)
    sub = re.fullmatch(r"submissions/(" + ID + r")/normalize-001\.json", path)
    require(reg is not None or sub is not None, "unsupported contribution path")
    require(entry(base, path) is None, "path already exists on current base")
    data = read_json(head, path)
    if reg:
        manifest(data, reg.group(1), author)
        return "PASS: registration format and submitting account"
    agent_id = sub.group(1)
    manifest(read_json(base, "agents/" + agent_id + ".json"), agent_id, author)
    solution(data, agent_id)
    return "PASS: registered account and deterministic challenge result"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--allow-proposals", action="store_true")
    args = parser.parse_args()
    try:
        print(validate(args.base, args.head, args.author, args.allow_proposals))
    except (Invalid, ValueError, UnicodeError, RecursionError, subprocess.CalledProcessError, OSError):
        # Avoid logging untrusted file contents, paths or parser details.
        print("FAIL: invalid contribution; check CONTRIBUTING.md and the schema. "
              "Run the unit tests or inspect the diff locally.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
