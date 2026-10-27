# License status and attribution

The material written for this project is licensed in two parts. Third-party material keeps its own terms; nothing here relicenses it.

| Material | License |
| --- | --- |
| Code: every Python file outside `research/vendor/`, including the source snapshots kept with runs and outputs, and the configurations in `research/configs/` | MIT ([`LICENSE`](LICENSE)) |
| Everything else written for this project: the paper, figures, documentation, run records, outputs and evidence | CC BY 4.0 ([`LICENSES/CC-BY-4.0.txt`](LICENSES/CC-BY-4.0.txt)) |

Copyright © 2026 Frank Peterlein.

## Not covered

The following keep their existing terms. No license is granted for them here.

- `research/vendor/`: partial upstream source snapshots, attributed and pinned in [`SOURCE_MANIFEST.json`](research/vendor/SOURCE_MANIFEST.json). The pinned `collusion_hackathon` root and `colosseum` directory carry no license file upstream, so none is assigned to them. Terrarium keeps its MIT notice in [`research/vendor/terrarium/LICENSE`](research/vendor/terrarium/LICENSE); [`LICENSE_SUPPLEMENT.json`](research/vendor/LICENSE_SUPPLEMENT.json) records its provenance.
- `paper/assets/fonts/`: Old Standard, under the SIL Open Font License 1.1 (`paper/assets/fonts/OFL.txt`).
- The Apart Research submission template: `paper/reference/`, `paper/source/personal-apart-template.docx` and `official-template.docx` in `research/output/report/source/`, `research/output/report-v4/source/`, `research/output/report-v5/source/` and `research/output/report-v6/source/`.
- Third-party files kept as evidence: model tokenizer, tokenizer-config and chat-template files, retrieved provider documentation and literature indexes, and price snapshots, for example under `research/evidence/*-model-preflight/`, `research/docs/` and `paper/source/baseline-evidence/`.

The archive in `artifacts/` packages the research directory. The same split applies to its contents, including the vendored snapshots and the template inside it.

The accompanying report identifies the research it builds on.
