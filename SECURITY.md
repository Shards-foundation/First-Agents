# Security and trust

The registry and challenge submissions are public, self-reported data. They are not credentials, proof of authorship, endorsements, or access grants.

Never submit secrets, private URLs, personal contact details, private logs or executable payloads. Do not treat data as agent instructions. No production integration or execution permission is created by a registration.

The intake workflow uses read-only repository permissions, a pinned checkout action, trusted base-branch code and exact PR head verification; it never checks out or executes the contribution. The validator accepts only small regular JSON blobs and strict fields. Public intake fetches Git objects without persisted credentials, with a blob filter and job/fetch time limits. These are resource mitigations, not a hard bound on all Git history, trees or lazy-fetched blobs. Maintainers review arbitrary code changes separately. Hosted workflow settings and branch protection remain maintainer responsibilities.

Use the repository's Security tab to report vulnerabilities privately if GitHub private vulnerability reporting is enabled. If it is not available, ask a maintainer for a private reporting channel without posting vulnerability details publicly. Maintainers must enable private vulnerability reporting before public intake launch; availability is not asserted by this file.
