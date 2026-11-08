# Known limitations

## Visual analysis

The report is generated text, not a deterministic assertion. A model may miss real
issues or describe issues that are not present. Review its findings and keep
ordinary UI assertions for behavior that can be checked directly. Exit code 0
means a report was produced, even when it describes an error on the page.

The tool analyzes one screenshot at a time. It does not compare a saved baseline,
aggregate multiple pages, or infer changes from previous runs. Tests verify the
software workflow and request format; they do not measure model accuracy.

## Capture

- Chrome is the only implemented browser. Full-page capture depends on Chrome
  DevTools Protocol.
- Every call starts a fresh session. Existing logins, cookies, and browser profiles
  are not reused, and there is no built-in login flow.
- Element selectors apply to the main document. Switching into iframes or shadow
  roots is not implemented.
- Navigation completion and element visibility are the available readiness checks.
  Dynamic content, images, fonts, and animations may still change afterwards.
- Full-page capture uses the current document size and does not scroll to load
  content. Very large pages can exceed browser or Pillow image limits.
- Element capture cannot be combined with full-page capture.

Capture produces PNG bytes. The encoder accepts PNG/JPEG bytes, preserves
dimensions, and processes the first frame of animated PNG input. JPEG conversion
is lossy and flattens transparency onto white. It does not resize large images to
fit a provider's limits.

## API compatibility

The client supports an OpenAI-compatible Chat Completions image request and a
non-streaming text response. A configurable URL does not add support for other
schemas such as Responses or Anthropic Messages. The caller must choose a model
with image support and appropriate access.

Only the first choice is returned. Empty text, invalid JSON, and completions with
an incomplete finish reason are treated as API errors. Requests are not retried,
and redirects are not followed. The HTTP timeout covers connection establishment
and read inactivity; it is not a total wall-clock deadline for the analysis.

Screenshots and the prompt are sent to the configured provider. Use a provider and
target page suitable for the data you intend to analyze. Local configuration and
credential files are ignored by Git, and `.env` files are not loaded automatically.
