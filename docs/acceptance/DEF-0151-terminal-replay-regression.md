# DEF-0151 terminal replay seam regression

Issue [#111](https://github.com/Young-Consultations/.github/issues/111), TC-MVP-E2E-001-SIM. Preserve the original terminal failure evidence; never replay #167 or #170.

The Nov 24 offline experiment identified a coverage gap: existing SIM passed a constructed prior-effect classification directly to the target. The new pytest suite runs actual router validation and dispatch with a strict synthetic GH command transport; the same trusted in-memory journal supplies actual preflight main(), the exact registered target adapter and actual receiver. The adapter checkout must match the registry commit and receiver pin before import. No source, target or control-plane production implementation changes. Test synthetic source #999999 only; fake admission, dispatch, model, publication and projection counts are observable. No live credentials, provider invocation, actual workflow dispatch, network sockets or external processes after checkout identity verification. CI checkout and dependency setup are ordinary read-only test preparation.

Run with an existing exact registered adapter checkout:

```bash
TC_MVP_E2E_TARGET_ROOT=/path/to/registered-adapter python -m pytest tests/test_terminal_replay_seam.py
```

PR SIM automatically runs the regression; missing target checkout fails in CI. JUnit evidence is retained with SIM evidence. The normal SIM report and REAL acceptance semantics are unchanged.

Cases cover receiver-generated failed result and same-delivery readmission denial, new identity positive control, nonmanaged terminal statuses, malformed/unavailable/ambiguous evidence, forged untrusted marker, actual managed draft reuse including receipt-only failure before forwarding, missing/conflicting owned draft, and invalid preflight classification. Fake router dispatch is intentionally allowed even for a prior terminal delivery: the pre-execution gate must prevent a second model call. This is not proof of real credential permissions, concurrency/atomicity, or live acceptance. DEF-0151 remains investigating until independent review, exact merged verification and explicit governed acceptance. No paid replay is required or permitted.
