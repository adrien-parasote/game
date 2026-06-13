# Skip/Waiver Register

| Item | Class | Evidence / Reason |
|------|-------|-------------------|
| /doc-update | (c) Out of scope | No spec drift detected. The change in OcclusionRenderer only bypasses an internal cache without changing its interface. Tests were only fixed to match the new descending logic implemented in a prior commit. |
| /refactor-clean | (c) Out of scope | No dead code was introduced; we only added a cache invalidation condition and updated test asserts. |
| submit_learning | (d) Tool unavailable | The `learnings-hub` MCP is not configured in this workspace, unable to submit. |
