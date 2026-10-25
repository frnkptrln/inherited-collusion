"""Assemble the V5 manuscript from closed, independently checked evidence.

All paths are relative to --project-root or this source directory. No model or
network calls occur. --final is reserved for the content-reviewed release.
"""
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path

import prepare_layout_input as layout

BUILD = Path(__file__).resolve().parent
ANALYSIS = 'output/analysis-v5/analysis.json'
CHECK = 'output/independent-v5/independent-check.json'
EXPECTED_ANALYSIS = '9d427bdad0580fdfeb14b8287094c4f39baec0abdf99761111e17e6b97b7aab4'
NOTE_ROOT = 'evidence/v5-content-review'
EXPECTED_NOTE_SEAL = '78883b0707462bc59a46254140f4fdb151b0622776e02afffd797995789f95f1'
MODEL_NAMES = {'qwen': 'Qwen', 'gptoss': 'GPT'}
ROUTES = {'facts_only': 'Facts', 'matched': 'Matched', 'verified': 'Verified'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def num(value, places=3):
    if value is None:
        return 'Unavailable'
    if abs(value) < 1e-10:
        value = 0.0
    return f'{value:.{places}f}'.rstrip('0').rstrip('.').replace('-', '−')


def interval(values):
    return '[' + ', '.join(num(v) for v in values) + ']'


def fraction(value, n):
    count = round(value * n)
    if abs(count - value * n) > 1e-8:
        raise ValueError('Binary group is not an exact complete-case fraction')
    return f'{count}/{n}'


def p(text):
    return {'type': 'p', 'text': text}


def h(text):
    return {'type': 'heading', 'level': 2, 'text': text}


def group(data, model, mode, structure, route):
    return next(g for g in data['models'][model]['modes'][mode]['groups']
                if g['structure'] == structure and g['condition'] == route)


def contrast(data, model, mode, name):
    return next(c for c in data['models'][model]['modes'][mode]['contrasts']
                if c['contrast'] == name)


def arm_table(data, mode):
    rows = []
    for model in ('qwen', 'gptoss'):
        for structure in ('symmetric', 'unique'):
            for route in ('facts_only', 'matched', 'verified'):
                g = group(data, model, mode, structure, route)
                v = g['common_six_arm_mean']
                n = len(g['common_six_arm_seeds']) * 2
                rows.append([MODEL_NAMES[model], structure.title(), ROUTES[route],
                             fraction(v['duplicate'], n), fraction(v['safe_optimal'], n),
                             fraction(v['harmful_joint'], n), num(v['outsider_loss']),
                             num(v['total_reward_loss'])])
    return {'type': 'table',
            'headers': ['Model', 'Structure', 'Route', 'Duplicate', 'Safe optimum', 'Joint harm', 'Outsider loss', 'Team loss'],
            'rows': rows, 'widths': [850, 1250, 1050, 1150, 1300, 1050, 1350, 1360]}


def assemble(project, final=False):
    data = json.loads((project / ANALYSIS).read_text())
    check = json.loads((project / CHECK).read_text())
    closure = json.loads((project / 'docs/v5-closeout-record.json').read_text())
    if sha(project / ANALYSIS) != EXPECTED_ANALYSIS:
        raise ValueError('Closed V5 analysis differs from reviewed snapshot')
    if not check['passed'] or check['mismatches'] or check['analysis_sha256'] != EXPECTED_ANALYSIS:
        raise ValueError('Independent raw countercheck is not a matching PASS')
    if closure['state'] != 'CLOSED_NO_FURTHER_DISPATCH':
        raise ValueError('Study is not closed')
    if (data['eligible_episodes'], data['planned_episodes'], check['raw_rows_checked']) != (240, 288, 240):
        raise ValueError('Unexpected final population')
    note_root = project / NOTE_ROOT
    if sha(note_root / 'content-review-seal.json') != EXPECTED_NOTE_SEAL:
        raise ValueError('Descriptive note review seal changed')
    note_seal = json.loads((note_root / 'content-review-seal.json').read_text())
    for name, record in note_seal['files'].items():
        if sha(note_root / name) != record['sha256']:
            raise ValueError('Sealed note review file changed: ' + name)
    if note_seal['closure_sha256'] != sha(project / 'docs/v5-closeout-record.json'):
        raise ValueError('Note review does not bind this closeout')
    notes = json.loads((note_root / 'note-review-summary.json').read_text())
    if (notes['notes_reviewed'], notes['planned_role_note_slots'], notes['complete_bundles']) != (80, 96, 40):
        raise ValueError('Unexpected note review coverage')
    if notes['semantic_codes_used_for_eligibility'] or notes['successor_or_aggregate_results_read']:
        raise ValueError('Note review scope differs from the report')
    spec = layout.assemble(project)
    spec.update(phase='V5 closed structural control integrated with retained V4 and V4F', ready_for_final=False)
    spec['follow_up'].update(status='closed_independently_checked', new_outcome_claims=True,
                             closed_at=closure['closed_at'], analysis_sha256=EXPECTED_ANALYSIS,
                             valid_joint_episodes=data['eligible_episodes'])
    spec['evidence_inputs'] += [{'path': path, 'sha256': sha(project / path)} for path in
        (ANALYSIS, CHECK, 'docs/v5-closeout-record.json', 'runs/phase5-budget.json',
         'evidence/v5-final-review/scientific-review.md', 'evidence/v5-final-review/scientific-review.json')]
    spec['evidence_inputs'] += [{'path': NOTE_ROOT + '/' + name, 'sha256': sha(note_root / name)} for name in
        ('content-review-seal.json', 'note-review-summary.json', 'note-review-summary.md', 'note-annotations.json')]
    spec['follow_up']['note_review'] = {'seal_sha256': EXPECTED_NOTE_SEAL,
        'timing': 'post-closure, outcome-unseen reviewer attestation', 'semantic_filter': False,
        'notes_reviewed': 80, 'planned_slots': 96, 'both_notes_convey_assigned_allocation_pairs': 26,
        'complete_pairs': 40, 'independent_human_or_interrater_validation': False}
    spec['abstract'] = (
        'We audit whether handoff notes carry instructed harmful allocations into neutral replacement agents. '
        'A transparent Colosseum-derived task pairs two independent model successors with scripted outsiders. '
        'The original strict protocol yields 360 valid episodes of 512 planned; a disclosed post-start format continuation '
        'reuses responses without resampling and yields 439. In amended data, same-source notes increase joint harm '
        'versus facts alone by 0.50 for Qwen3.6-35B-A3B over five complete cases and 0.43 for GPT-OSS-120B over seven. '
        'Verification reduces joint harm but increases duplicates relative to matched harmful notes. A post hoc baseline comparison '
        'motivates a separate control, locally frozen before new calls, pairing symmetric and unique-optimum tasks. '
        'It yields 240/288 planned episodes across four complete Qwen and six GPT-OSS cases. Under verification, harmful-mode '
        'duplicates fall from 5/8 to 0/8 for Qwen and 10/12 to 0/12 for GPT-OSS when the safe optimum becomes unique. '
        'Yet Qwen reaches that optimum in only 4/8 unique-task episodes, retaining partial outsider harm in four; GPT-OSS '
        'reaches it in 12/12. Matched harmful notes still induce joint harm under uniqueness. Thus the observed coordination '
        'cost depends on task structure, without establishing universal protection or an internal mechanism. Induced originals, '
        'regenerated notes, incomplete Qwen coverage and a narrow task family limit interpretation.')

    main_methods = [
        p('Motivated by the 24 October review, a separate control was locally frozen before new calls. Six fresh seeds (301–306) per model pair symmetric and unique-optimum tasks. Two original objectives, three routes (facts, matched, verified) and two nested draws yield 288 planned episodes. Task clusters, not individual draws, form comparison units.'),
        p('Adding one unit to each role’s other safe task raises the reversed safe plan’s cost by two. Optimal total cost and assigned safe/harmful-plan outcomes are preserved; the lexicographic reference may swap A/B roles. Instructions, reminder, settings and outcome-table visibility/construction are unchanged, but numeric table entries are recomputed. Fresh notes are generated per structure/objective; matched and verified share them. Four comprehension probes are diagnostic, not semantic exclusion gates. Technical failures or wrong original actions still stop a case.'),
        p('The primary harmful-mode duplicate interaction is (verified − matched) under uniqueness minus that under symmetry. All primary cells use common complete six-arm cases per model/mode, averaging two draws then weighting cases equally. Missing outputs are not safe. Changed notes are part of this structural intervention, not held fixed.'),
        p('The control yields 240/288 episodes: Qwen 96/144 over cases 301, 303, 304 and 306; GPT-OSS 144/144 over all six. Qwen-302 stopped on probe format and 305 on an unresolved request. Qwen-301 passed only 3/4 semantic diagnostics and remains included as specified. No case was replaced. All 80 notes enter analysis. A post-closure AI review classified both notes as clearly conveying the assigned future allocation in 26/40 pairs; the channel does not always supply faithful plans.'),
    ]
    result_text = (
        'The primary harmful-mode duplicate interaction is −0.625 for Qwen (4/6 cases) and −0.750 for GPT-OSS (6/6). '
        'Logical completion ranges over all six planned cases are [−1.083, +0.250] and [−0.750, −0.750], not confidence intervals. '
        'The verified unique-minus-symmetric duplicate contrast is −0.625 and −0.833; its Qwen completion range remains negative '
        '[−0.750, −0.083]. Unique verified Qwen still harms outsiders in 4/8 episodes: mean loss 12 versus 3.5 for facts only. '
        'Zero joint harm therefore does not establish safety. In legitimate mode, unique matched and verified plans are all optimal '
        '(Qwen 8/8; GPT-OSS 12/12). Under symmetry, verification lowers reward versus matched notes by 24.75 and 33.5 respectively; '
        'the unique-task difference is zero. Appendix G gives the separate facts-only structure contrasts and all control arms.')
    discussion = (
        'Handoffs transmit instructed coalition-favoring allocations in this task, while legitimate notes can supply useful conventions. '
        'The follow-up supports task-structure dependence of the observed coordination cost: uniqueness removes verified duplicates '
        'on complete cases, but does not by itself remove harmful transfer. Matched unique notes still yield joint harm in 5/8 Qwen '
        'and 6/12 GPT-OSS episodes. Qwen’s residual outsider harm and incomplete coverage preclude a general protection claim. '
        'Because both costs and newly generated notes change, the contrast does not isolate a fixed-message effect or prove why '
        'the models behave differently. The explicit shared lexicographic instruction proposed during review remains untested. '
        'The original convention-following criterion remains a manipulation check, separate from task utility.')
    blocks = []
    in_followup = False
    skip_old_discussion = False
    for block in spec['blocks']:
        text = block.get('text', '')
        if text.startswith('5. Follow-up control'):
            blocks.append(deepcopy(block)); blocks.extend(main_methods); in_followup = True
        elif in_followup and text.startswith('6. Discussion'):
            blocks += [p(result_text), deepcopy(block), p(discussion)]
            in_followup = False; skip_old_discussion = True
        elif in_followup:
            if block['type'] == 'caption':
                blocks.append({'type': 'caption', 'text': 'Table 4. Harmful-mode follow-up on common complete cases: Qwen n=4/6 (301, 303, 304, 306); GPT-OSS n=6/6 (301–306), two draws each. Binary columns are episode counts; losses are equal-case means relative to the cooperative optimum. GPT denotes GPT-OSS.'})
            elif block['type'] == 'table':
                blocks.append(arm_table(data, 'harmful'))
        elif skip_old_discussion and block['type'] != 'page_break':
            continue
        elif skip_old_discussion:
            skip_old_discussion = False; blocks.append(deepcopy(block))
        elif text.startswith('Inference is limited by donor-driven redesign'):
            blocks.append(p(text + ' The follow-up adds six planned clusters per model (four complete for Qwen), not an independent task-family replication. Diagnostic mistakes remain included. Changing cost geometry changes the task and regenerated notes jointly; model-specific notes prevent a clean capability ranking. No universal claim follows from a unique optimum in these fixtures.'))
        elif text.startswith('The phase ceiling was $8.328'):
            blocks.append(p(text.replace('The phase ceiling', 'The historical V4 phase ceiling').replace('Current-phase reservations', 'V4/V4F reservations')))
            blocks.append(p(f'The follow-up adds {data["requests"]} requests and {data["responses"]} responses, with a provider usage estimate of ${data["returned_response_cost_estimate_usd"]:.9f}. Adding the historical $1.922675947 once gives ${data["known_project_returned_response_estimate_usd"]:.9f} for known returned responses. Its $4.896 allocation plus retained prior ceilings totals $14.818 under the authorized $15. One additional unresolved request has no reported usage, bringing historical plus follow-up unresolved requests to five. These estimates do not establish invoiced cost.'))
        elif text.startswith('Appendix G.'):
            break
        else:
            blocks.append(deepcopy(block))
    blocks += appendix(data, closure, notes)
    spec['blocks'] = blocks
    # Primary historical evidence is immutable, including table order and values.
    old = json.loads((BUILD / 'v4-reviewed-input.json').read_text())
    assert [b for b in blocks if b['type'] == 'table'][:3] == [b for b in old['blocks'] if b['type'] == 'table']
    assert [b for b in blocks if b['type'] == 'figure'] == [b for b in old['blocks'] if b['type'] == 'figure']
    if final:
        if any('PENDING' in b.get('text', '') for b in blocks):
            raise ValueError('Semantic annotation/review integration is unfinished')
        spec['ready_for_final'] = True
    return spec


def appendix(data, closure, notes):
    b = [h('Appendix G. Follow-up control evidence and results'),
         p('V5 was motivated by the post hoc symmetry diagnostic, then locally frozen at 10:38:02.550157 UTC on 24 October 2026 before any V5 requests. It closed at ' + closure['closed_at'] + '. Six seeds (301–306) per model yield twelve fixed cases and at most 816 calls: four diagnostic probes, sixteen original-agent action/note calls and forty-eight successor calls per case. Original action commitment precedes note writing. Assigned original orientation alternates with seed parity. Both structures and objectives have fresh originals; semantic note quality never filters the primary population.'),
         p('The final record contains 683 requests and 682 saved responses. Four Qwen cases and all six GPT-OSS cases complete all 24 planned episodes each. Qwen-302 supplies a correct optimal allocation with disallowed introductory prose: this is a format-policy exclusion, not a reasoning failure. Qwen-305 has two requests, one response and an unresolved second probe; neither case produces notes or successor episodes. Of 48 planned probes, 43 were dispatched and 42 responses saved. Forty of 41 schema-valid responses are semantically correct (Qwen 16/17; GPT-OSS 24/24). Qwen-301’s symmetric B probe gives a technically valid but nonoptimal duplicated assignment; its 3/4 result does not exclude the case, as specified.'),
         p('The structural perturbation changes only the two nonpreferred safe A/B cells by +1. It preserves optimal total cost, the assigned safe/harmful-plan outcomes and outsider aggregate reference payoff, but the lexicographic full reference allocation and individual A/B reference payoffs may change. All sixteen public outcomes are recomputed for each structure. Independent recipients receive the same instruction construction and visibility, not identical numeric outcome tables across structures. The paired comparison includes both these task changes and newly generated notes.'),
         p('After closure, one agent-assisted reviewer read all 80 notes (32 Qwen, 48 GPT-OSS), retaining 16 missing slots among 96 planned. All JSON task fields match committed original actions. Under the disclosed coding rules, 60 notes clearly convey the assigned future A/B allocation, 19 do not and one is unclear; both notes do so in 26/40 pairs. Clear conveyance counts are 31/32 for Qwen and 29/48 for GPT-OSS. These are descriptive annotations, not independent observations or evidence of recipient compliance. No semantic code changes eligibility or any effect estimate.'),
         p('The review identifies one explicit wrong own-recipient instruction, 18 absent concrete future mappings and one unclear provisional mapping. For example, an A note accurately reports its own T1 action but tells its A successor to take B’s T2. Six GPT-OSS notes misstate the all-agent choice mechanism; six Qwen notes make false cost-minimum claims. Nine derived-claim assessments remain undecided. Categories can overlap. Excerpts, rationales, raw-note hashes, original context and the codebook are retained in evidence/v5-content-review.'),
         p('Annotation finished at 11:45:19.145220 UTC and was sealed at 11:46:43.856927 UTC on 24 October, after raw closure. The reviewer attests to not opening successor responses, episodes, run summaries or aggregate results, but knew model, structure, objective, role and original plan. This is not an automated proof of blinding, metadata-blind coding or independent inter-rater validation. The note review describes sender heterogeneity; it does not establish a behavioral correlation or a successor mechanism.'),
         {'type': 'caption', 'text': 'Table G1. Legitimate-mode arms, with the same complete case sets as Table 4. Binary columns are episode counts; continuous losses are means.'},
         arm_table(data, 'legitimate'),
         h('Selected structure contrasts and completion sensitivity'),
         p('Tables G2–G3 show the prespecified primary interaction and key verified/facts structure contrasts, using the same four Qwen or six GPT-OSS paired cases in each objective. All 44 model/objective contrast records and eight metrics are retained in output/analysis-v5/analysis.json. The interaction is (verified − matched)unique − (verified − matched)symmetric. Other rows subtract symmetric from unique for the named route. Each case contributes its two-draw mean. Bounds allow every absent planned slot to take any legal task outcome; they are logical completion envelopes, not sampling intervals or identified effects of nonexistent notes in the two missing Qwen cases. A degenerate interval reflects complete finite coverage, not certainty about future tasks or calls. The GPT-OSS primary interaction is negative in five cases and positive in one; the aggregate is not a claim that every case improves.')]
    for mode in ('harmful', 'legitimate'):
        rows = []
        for model in ('qwen', 'gptoss'):
            for name, label in [('verification_structure_interaction', 'Interaction'), ('unique_minus_symmetric:verified', 'Verified U−S'), ('unique_minus_symmetric:facts_only', 'Facts U−S')]:
                c = contrast(data, model, mode, name); v = c['common_six_arm_mean']
                rows.append([MODEL_NAMES[model], label, str(len(c['common_six_arm_seeds'])) + '/6',
                             num(v['duplicate']), interval(c['finite_completion_bounds']['duplicate']),
                             num(v['safe_optimal']), num(v['harmful_joint']), num(v['total_reward_loss'])])
        b += [{'type':'caption','text':f'Table G{2 if mode == "harmful" else 3}. {mode.title()} structure contrasts. U−S denotes unique minus symmetric; positive team loss is worse.'},
              {'type':'table','headers':['Model','Contrast','n/6','Δ duplicate','Completion range','Δ safe','Δ harm','Δ team loss'],
               'rows':rows,'widths':[850,1600,550,1100,1900,1000,1000,1360]}]
    b += [p('Facts-only improvement is not inferred from verified responses. In harmful mode, uniqueness reduces duplicates by 0.625 for Qwen and 0.917 for GPT-OSS, while safe-optimal frequency rises by 0.500 and 0.917. In legitimate mode, the corresponding changes are −0.750/+0.625 and −0.667/+0.667. The two nominal original modes have identical facts-only prompts within a role and structure; different rates reflect separate stochastic draws, not an original-mode treatment. Under uniqueness, optimal behavior may follow from public facts alone and does not prove note processing. Qwen unique harmful verification has lower safe-optimal frequency than facts alone (4/8 versus 7/8), and greater mean outsider loss (12 versus 3.5). All four nonoptimal verified episodes have positive outsider loss; joint harm remains zero. These metrics distinguish absent coordinated harm from successful safe task completion.'),
          p('The independent standard-library countercheck recomputes all 240 saved joint outcomes with exact arithmetic and agrees with the analysis on group summaries, paired contrasts and finite completion bounds. This validates arithmetic and retained evidence, not the causal interpretation or served weights. Software validation is distinct from the model observations. The finalized analysis and checker outputs, twelve raw run folders, protocol, freeze, closure, source snapshots and budget ledger are included in the companion package. The reviewed V4 package remains preserved byte-for-byte as historical evidence; no new public archive or submission is claimed.')]
    return b


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, default=BUILD / 'report-input.json')
    ap.add_argument('--final', action='store_true')
    args = ap.parse_args()
    spec = assemble(args.project_root.resolve(), final=args.final)
    args.out.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'input_sha256':sha(args.out),'ready_for_final':spec['ready_for_final'],
                      'abstract_words':len(spec['abstract'].split()),'old_tables_figures_unchanged':True}))


if __name__ == '__main__':
    main()
