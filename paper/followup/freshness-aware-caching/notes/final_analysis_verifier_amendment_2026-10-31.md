# Final-analysis verifier amendment

Date recorded: 2026-10-31

GitHub Actions run `41148624728` completed successfully before this amendment. All 4,824 uploaded archives were downloaded and passed the frozen 18-file ZIP integrity check. The confirmatory analyzer then stopped on the first archive before calculating any estimate or exposing any scientific outcome.

The failed check compared a schedule parsed from JSON with the generator's in-memory mapping. JSON represents `duplicate_delays_ms` as a list, while `dataclasses.asdict` retains the in-memory tuple. The two values serialize to the same canonical JSON and produce identical full-schedule, trace and fault SHA-256 identities, but Python considers the raw list and tuple unequal.

The verifier now normalizes the generated mapping through JSON before the exact mapping comparison. The three prespecified canonical digest comparisons remain unchanged. This correction changes no observation, protocol condition, policy, parameter, sample size, contrast, outcome, bootstrap method, confidence level or interpretation rule. A regression test reproduces the list-versus-tuple representation difference. No confirmatory estimate was calculated or inspected before this amendment.
