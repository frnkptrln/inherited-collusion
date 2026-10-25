"""Prepare the separate V5 report without reading live follow-up outcomes.

This preparation version deliberately cannot mark a report ready for delivery.
After raw closeout and independent validation, its result assembly will be
completed against the retained V5 analysis. Historical V4 evidence is unchanged.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

BUILD = Path(__file__).resolve().parent
BASE = BUILD / 'v4-reviewed-input.json'
BASE_SHA = '1a084035c969b85abd9e5eeb35f56b41dc2bf9f2ca28fd9b620659fefaceb66c'
PROTOCOL_SHA = '8ca04dd6886b16b226e295bc831dbb1bfc8290a593d79a03fd0ea78f10a2b18f'
FREEZE_SHA = '966b1c2041098eb1de7622ba1c16531e4903c1314c6a147143693e3f983683e6'
MAIN_REWRITES = {
    1: 'Can unedited, role-specific handoffs transmit instructed harmful allocations to neutral replacements? We compare absent, one-sided, same-source, crossed-source and verification-reminder delivery, with legitimate-allocation controls for useful coordination. The contribution is a small controlled measurement of this channel, not the discovery of inherited misalignment.',
    2: 'Colosseum distinguishes collusive plans from enacted coalition-favoring behavior [1]; our reduced allocation fixture adapts its setting [4]. Self-Propagating Misalignment studies misaligned goals passed to neutral successors and memory defenses [2]. Salami Attack/MemCollusion examines jointly effective memory fragments [3]. Here separate successors each receive their own predecessor’s note, with public task facts fixed. We score coalition benefit, outsider loss and team utility. Same-source notes need not be compatible; instructed originals establish neither spontaneous collusion nor persistent private intent.',
    4: 'Earlier competence and donor-note failures shaped model selection and design. Primary analysis therefore includes sender errors within the technically usable handoff channel. Those pilots produced no successor observations; Appendix B retains their history.',
    5: 'V4 models, cases, prompts, analysis plan and execution source were frozen locally before successor requests on 23 October 2026, following earlier competence and donor observations. This was not public preregistration. All technically valid notes enter primary analysis; false claims, ambiguous roles and refusals do not filter execution.',
    6: 'Strict V4 rejected Markdown-wrapped JSON, including a correct competence answer. The disclosed post-start continuation V4F admitted exactly one complete outer JSON fence with unchanged inner schema and gates. It reused saved responses without resampling and collected only undispatched planned calls. Original analysis remains separate; this amended descriptive analysis is not an independent replication. Appendix B records chronology and accidental partial-outcome visibility.',
    12: 'Each model passes a seed-902 qualification; each main case repeats two full-allocation probes on an asymmetric unique-optimum fixture and four queue-note probes. Required own task, assignment and cost must be correct. A failed gate stops the case without replacement. Queue probes establish elementary note access, not actual-task convention use. Notes must have valid schema, known task, nonempty text within 2,000 characters and bounded successor prompts. Reported task may differ from original action. Hash-bound AI annotations precede that case’s successors.',
    19: 'Actual-task convention use requires at least 12/16 planned legitimate episodes separately for same-p0 and same-p1; missingness cannot help it pass. This is a descriptive manipulation check, not an execution gate. Secondary source-pairing and stricter note-content analyses appear in Appendix F. Source compatibility, mechanical conjunction in joint harm and content-selection bias preclude interpreting them directly as strategic interaction.',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def p(text):
    return {'type': 'p', 'text': text}


def h(text, level=2):
    return {'type': 'heading', 'level': level, 'text': text}


def assemble(project):
    if sha(BASE) != BASE_SHA:
        raise ValueError('Reviewed original report input changed')
    for name, expected in [('docs/v5-protocol.json', PROTOCOL_SHA),
                           ('docs/v5-freeze.json', FREEZE_SHA)]:
        if sha(project / name) != expected:
            raise ValueError('Follow-up protocol/freeze changed: ' + name)
    old = json.loads(BASE.read_text())
    spec = deepcopy(old)
    spec.update(phase='V5 follow-up report preparation after local freeze',
                ready_for_final=False)
    spec['abstract'] = ('We audit whether authentic handoff notes carry instructed coalition-favoring allocations into neutral replacement agents. A transparent Colosseum-derived task gives two independent model successors all costs and outcomes while two outsiders follow a scripted rule. Eight delivery conditions include legitimate-allocation controls. The original strict protocol yields 360 valid episodes of 512 planned; a disclosed post-start format-only continuation reuses responses without resampling and yields 439. In amended data, same-source p0 notes increase joint harm versus facts alone by 0.50 for Qwen3.6-35B-A3B over five complete cases and 0.43 for GPT-OSS-120B over seven. Verification reduces harm but also lowers harmful-mode team reward relative to same-source notes. A post hoc comparison finds that verification and facts alone have identical duplicate frequencies on their common amended cases, consistent with loss of a shared convention in a task with two safe optima. A separate follow-up, locally specified before new calls, pairs symmetric and unique-optimum structures across six fresh cases per model and 288 planned episodes. PENDING: audited follow-up findings and denominator-qualified conclusion. Earlier design adaptation, incomplete collection and model-specific notes limit interpretation. These observations concern induced allocations in a narrow task family, not spontaneous collusion or a general safety guarantee.')
    spec['follow_up'] = {
        'status': 'awaiting_raw_closeout_analysis_and_independent_review',
        'frozen_at': '2026-10-24T10:38:02.550157+00:00',
        'planned_joint_episodes': 288,
        'planned_case_seeds': list(range(301, 307)),
        'maximum_model_calls': 816,
        'new_outcome_claims': False,
        'no_pooling_with_v4': True,
    }
    spec['evidence_inputs'] += [
        {'path': 'docs/v5-protocol.json', 'sha256': PROTOCOL_SHA},
        {'path': 'docs/v5-freeze.json', 'sha256': FREEZE_SHA},
    ]
    blocks = []
    # Original primary tables and figures are retained verbatim. Only detailed
    # secondary results are relocated, with concise main-text crossreferences.
    for i, block in enumerate(old['blocks']):
        if i in MAIN_REWRITES:
            blocks.append(p(MAIN_REWRITES[i]))
        elif i == 36:
            blocks.append(p('One-note and crossed-source arms have no observed joint-harm episodes, yet retain partial outsider harm and can disrupt legitimate coordination. Source-pairing and semantic-note subset results are reported in Appendix F; neither identifies strategic reasoning or the causal role of false claims.'))
        elif i == 37:
            continue
        elif i == 39:
            blocks.append(p('Logical completion envelopes over all planned slots retain missingness sensitivity. The strict Qwen p0 interval includes zero; the amended Qwen and both GPT-OSS intervals do not. These are arithmetic ranges, not confidence intervals or identified effects for nonexistent notes. Exact ranges and qualifications remain in Appendix F.'))
        elif i == 40:
            # Release the former forced Discussion page break for the control.
            continue
        elif i == 41:
            blocks += [
                h('5. Follow-up control with a unique safe optimum'),
                p('Motivated by the 24 October review, a separate control was locally frozen before new calls. Six fresh seeds (301–306) per model pair symmetric and unique-optimum structures. Two original objectives, three routes (facts, matched and verified) and two nested draws yield 288 planned episodes. The six paired task clusters per model, not 288 independent observations, form the comparison units.'),
                p('Adding one cost unit to each role’s other safe task raises the reversed safe allocation cost by two; preferred safe and selected harmful-plan payoffs remain unchanged. Each structure/objective generates fresh originals and notes; matched and verified share exact notes. Neutral instructions, outcome tables, reminder and model settings are unchanged. Four actual-task comprehension responses per case are diagnostic, so semantic mistakes do not exclude cases. Technical failure or wrong original action still stops a case without replacement.'),
                p('The primary contrast is the harmful-mode verification-associated duplicate increase under uniqueness minus that under symmetry. Verified and facts-only structure effects accompany it, with facts analyzed separately by objective mode. All primary cells share complete six-arm cases per model/mode, averaging two draws then weighting cases equally. Missing outputs are not safe. Changed notes are part of the intervention, rather than held fixed.'),
                p('PENDING: Insert audited V5 stage counts, primary contrast table with exact case denominators/seeds, legitimate cooperation control, failures and logical completion ranges only after closure and independent raw verification.'),
                {'type': 'caption', 'text': 'Table 4. Follow-up harmful-mode results on common complete six-arm cases. All result cells are pending. Probabilities and mean team reward loss use equal case weights; n is out of six planned cases. GPT denotes GPT-OSS.'},
                {'type': 'table', 'headers': ['Model', 'Structure', 'Route', 'n/6', 'Duplicate', 'Safe optimum', 'Joint harm', 'Team loss'],
                 'rows': [[model, structure, route, 'TBD', 'TBD', 'TBD', 'TBD', 'TBD']
                          for model in ('Qwen', 'GPT') for structure in ('Symmetric', 'Unique')
                          for route in ('Facts', 'Matched', 'Verified')],
                 'widths': [1000, 1300, 1100, 700, 1200, 1400, 1300, 1360]},
                p('PENDING: Report the primary duplicate interaction for each model with exact n/6 and seeds, the verified structure contrasts, and facts-only structure effects separately in harmful and legitimate mode. This space reserves approximately one hundred words for the audited numerical results and their uncertainty. State the legitimate-mode verification contrast and safe-optimal performance alongside harmful-mode changes. Include failed cases and any unavailable comparisons; no missing outcome may count as successful safety. State whether the follow-up supports task-structure dependence in this finite family, without treating changed notes as a fixed-message intervention or claiming a general model mechanism.'),
                h('6. Discussion and conclusion'),
            ]
        elif i == 43:
            blocks.append(p('PENDING: Integrate the follow-up findings without pooling them with V4/V4F, attributing an internal mechanism or claiming a general safeguard. The explicit shared lexicographic tie-break proposed during the review remains untested: changing cost geometry is a different intervention. The original convention-following criterion remains a manipulation check separate from task utility.'))
        else:
            blocks.append(deepcopy(block))
    blocks += [
        {'type': 'page_break'},
        h('Appendix F. Original secondary results and completion sensitivity'),
        deepcopy(old['blocks'][19]),
        deepcopy(old['blocks'][36]), deepcopy(old['blocks'][37]),
        deepcopy(old['blocks'][38]), deepcopy(old['blocks'][39]),
        h('Appendix G. Follow-up evidence and complete results'),
        p('PENDING: Retain the final V5 sample flow, all model/structure/mode/arm summaries and primary and secondary contrasts, exact source and closure bindings, diagnostics, cumulative accounting and independent validation. No follow-up result is yet supplied.'),
    ]
    spec['blocks'] = blocks
    assert [b for b in blocks if b['type'] == 'table'][:3] == [b for b in old['blocks'] if b['type'] == 'table']
    assert [b for b in blocks if b['type'] == 'figure'] == [b for b in old['blocks'] if b['type'] == 'figure']
    return spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=BUILD / 'report-input.json')
    args = parser.parse_args()
    if args.out.exists() and json.loads(args.out.read_text()).get('ready_for_final'):
        raise ValueError('Do not replace an already finalized report input')
    spec = assemble(args.project_root.resolve())
    args.out.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ready_for_final': False, 'input_sha256': sha(args.out),
                      'new_results_supplied': False, 'old_tables_figures_unchanged': True}))


if __name__ == '__main__':
    main()
