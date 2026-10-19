# Remove token URL transport and make settings recoverable

Steward proposal, 2026-10-19, from architecture audit [5].
Pending steward promotion; not authorization to implement or deploy.

Review F4 / Step 2; phone configUrl() still includes the token query and derives
/config from the saved endpoint. webviewclosed accepts arbitrary URLs.

## Acceptance criteria

- Existing tokens never appear in configuration path/query or HTTP request targets;
  test mocked openURL and config-page request targets with synthetic tokens.
- Validate HTTPS endpoints before saving; document any explicit local-only exception.
  Blank token retains the current token only for the unchanged endpoint; changing
  origin requires deliberate credentials and never silently forwards the old token.
- A broken saved endpoint can be reset through a bootstrap route independent of it;
  document recovery when bootstrap is unavailable. Keep /config unauthenticated.
- Node VM tests cover cancel, malformed JSON, blank settings, schemes, origin changes,
  save/reopen and unreachable endpoints. Record physical phone/reinstall verification
  separately or qualify unsupported persistence claims; do not infer it from localStorage.
- Deploy compatible config HTML before dependent phone changes; retain valid settings.
  Update both READMEs and leave service-token rotation to an authorized operator.
