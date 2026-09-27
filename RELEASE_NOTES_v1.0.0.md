# Version 1.0.0 research artifact

This release supports the article "Contextual Rendering Selection Beyond Strong Fixed Baselines: A Controlled Browser Study."

## Included

- Twenty-four final test units and 1,728 original JSONL observations.
- Separate Mac and hosted Linux cohort metadata.
- Frozen actions for six evaluated policies.
- Expected results and an offline numerical reproduction script.
- The source snapshot and dependency locks used by the hosted collection.
- File inventory, hashes and privacy-scan record.

## Reproduced results

- Mac context-table minus fixed contrast: -0.2393518521 ms.
- Mac conditional 95% whole-session bootstrap interval: [-0.3993055552, -0.0923611107] ms.
- Hosted Linux context-table minus fixed contrast: -0.3018518519 ms.
- Hosted allocation signs: eight favor the context table and four favor the fixed policy.

## Limitations

This release reproduces final scoring. It does not contain the complete development, training, validation, variance, failed-campaign or pilot history. The endpoint is navigation-to-application-marker time and does not establish user-perceived performance. Cloud results are descriptive and do not demonstrate independent-host transport.

## Licensing

- Original software: MIT License.
- Original research data and documentation: CC BY 4.0.
- Third-party materials retain their existing licenses.

The article DOI will be added as a related identifier when available.
