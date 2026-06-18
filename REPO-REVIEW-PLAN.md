# Repository review improvement list

This file captures the repo review items identified for security, logic, cleanup,
documentation, CI, and deployment hardening.

1. Validate `MAX_FILE_BYTES` safely so a non-integer, zero, or negative environment value cannot break function cold start or disable the size guard.
2. Add tests for more edge cases: missing/empty filename, missing filename extension, malformed JSON, converter failure response, temporary-file cleanup, health response, and invalid `MAX_FILE_BYTES` configuration.
3. Pin or constrain production dependencies (`azure-functions`, `markitdown[docx,pdf]`) and dev dependencies (`pytest`) for reproducible builds and easier vulnerability review.
4. Add Dependabot or another lightweight dependency update/security update configuration.
5. Consider a dependency vulnerability check in CI, if it can be added without making the repo heavy or noisy.
6. Fix stale repository references from `GraafG/markitdown-powerplatform` to `GraafG/powerplatform-markitdown-function` in README, SECURITY, CONTRIBUTING, and ARM deployment defaults.
7. Review the Deploy to Azure button target because it currently points at the old repository path.
8. Review ARM deployment hardening around `AzureWebJobsStorage`; it currently uses a storage account key connection string, which may conflict with tenants that disable shared-key storage access.
9. Make deployment settings more explicit, especially `MAX_FILE_BYTES`, production auth expectations, and any public-network assumptions.
10. Review whether `/api/health` should remain anonymous in all deployments, or whether docs should clarify that Easy Auth can also protect it.
11. Review flow output exposure: `flows/sharepoint-folder-demo.json` includes converted Markdown in returned arrays, which can put document content into Power Automate run history.
12. Add pagination/large-library guidance or handling for the sample SharePoint flow, since it uses `$top: 100`.
13. Keep supported-extension declarations consistent across code, OpenAPI specs, README, SECURITY, TEST-STATUS, and the Power Automate flow.
14. Consider returning a more specific error for encrypted/protected files if `markitdown` exposes reliable exception types; otherwise keep the generic `500` and document it clearly.
15. Review logging to ensure correlation IDs are useful without logging document content, filenames that may contain sensitive data, or secrets.
16. Add tests or validation for both OpenAPI specs beyond JSON parsing, especially security definitions and required request fields.
17. Check `.funcignore`: it ignores `test`, but the repo folder is `tests`; confirm deployment packaging excludes the intended non-runtime files.
18. Consider adding a small sample request/response fixture or scripted smoke test for local manual validation.
