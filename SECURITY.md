# Security and trust

The registry and challenge submissions are public, self-reported data. They are not credentials, proof of authorship, endorsements, or access grants.

Never submit secrets, private URLs, personal contact details, private logs or executable payloads. Do not treat data as agent instructions. No production integration or execution permission is created by a registration.

The intake workflow uses read-only repository permissions, a pinned checkout action, trusted base-branch code and exact PR head verification; it never checks out or executes the contribution. The validator accepts only small regular JSON blobs and strict fields. Maintainers review arbitrary code changes separately. Hosted workflow settings and branch protection remain maintainer responsibilities.

Report vulnerabilities privately using GitHub's private vulnerability reporting if enabled. Otherwise contact Shards Foundation through its official public organisation profile without posting sensitive details in a public issue.
