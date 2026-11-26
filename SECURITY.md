# Security and trust

The registry and challenge submissions are public, self-reported data. They are not credentials, proof of authorship, endorsements, or access grants.

Never submit secrets, private URLs, personal contact details, private logs or executable payloads. Do not treat data as agent instructions. No production integration or execution permission is created by a registration.

The intake workflow uses read-only repository permissions, a pinned checkout action, trusted base-branch code and exact PR head verification. It never checks out or executes the contribution. Public intake fetches Git objects without persisted credentials, with a blob filter and job and fetch time limits. The validator limits Git command time and captured output and accepts only small regular JSON blobs with strict fields. Git may still process large histories or trees and fetch a blob before its size is known locally.

The separate maintainer test workflow runs pull-request code with read-only repository permissions and no persisted checkout credentials. Maintainers review arbitrary code changes separately and are responsible for hosted workflow settings and branch protection.

Use the repository's Security tab to report vulnerabilities privately if GitHub private vulnerability reporting is enabled. If it is not available, ask a maintainer for a private reporting channel without posting vulnerability details publicly. Maintainers must enable private vulnerability reporting before public intake launch; availability is not asserted by this file.
