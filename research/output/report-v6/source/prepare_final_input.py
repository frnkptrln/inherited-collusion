#!/usr/bin/env python3
"""Prepare a guarded V6 manuscript without fabricating follow-up findings.

The final adapter accepts only the retained sealed evidence and independent checks.
Draft authoring is retained for provenance; --final integrates closed observations.
It never starts model calls, reads credentials, or modifies experiment evidence.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

BUILD = Path(__file__).resolve().parent
BASE = BUILD / 'v5-reviewed-input.json'
BASE_SHA = 'ca7905043e3ad6b417f741bae5d048d487e37af03cd5d3a09b961294c4d7faeb'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def p(text):
    return {'type': 'p', 'text': text}

def heading(text, level=2):
    return {'type': 'heading', 'text': text, 'level': level}

def caption(text):
    return {'type': 'caption', 'text': text}

def table(headers, rows, widths):
    return {'type': 'table', 'headers': headers, 'rows': rows, 'widths': widths}

def assemble(project_root):
    if sha(BASE) != BASE_SHA:
        raise ValueError('Reviewed V5 manuscript changed')
    old = json.loads(BASE.read_text())
    for item in old['evidence_inputs']:
        if sha(project_root / item['path']) != item['sha256']:
            raise ValueError('Historical evidence changed: ' + item['path'])
    b = old['blocks']
    spec = deepcopy(old)
    spec.update(
        phase='V6 authoring preparation only; no new outcomes integrated',
        editorial_review_date='2026-10-25', ready_for_final=False,
        title='Safe Coordination after Harmful Agent Handoffs',
        subtitle='A Controlled Audit of Verification and Shared Decision Rules',
        abstract=(
            'Can a shared public decision rule support safe coordination when neutral '
            'replacement agents inherit harmful notes? In a transparent Colosseum-derived '
            'allocation task, we hold original notes and symmetric cost matrices fixed '
            'across ten available donor cases: four for Qwen3.6-35B-A3B and six for '
            'GPT-OSS-120B. Fresh successors receive verification alone or verification '
            'plus lexicographic-first or lexicographic-last selection among public safe '
            'optima. Each condition has two nested draws, with harmful and legitimate '
            'original notes examined separately. PENDING final V6 primary effect, exact '
            'denominators, legitimate utility and residual outsider harm. The primary '
            'contrast gives both rule directions equal weight and measures safe-optimal '
            'completion separately by model. Earlier delivery audits found harmful '
            'allocation transfer and a reduction in joint harm under verification, '
            'accompanied by duplicate claims. A subsequent structural control removed '
            'verified duplicates when the safe optimum became unique, but retained '
            'partial outsider harm for Qwen and changed generated notes as well as '
            'costs. The fixed-note comparison addresses that ambiguity. It tests an '
            'explicit common decision policy, not internal verification or its '
            'necessity. Availability-selected donors, small finite cohorts, two draws, '
            'heterogeneous note quality and the absence of a rule-only arm limit '
            'generalization.'
        ),
        follow_up={
            'status': 'PENDING closed V6 evidence and independent check',
            'planned_joint_episodes': 120, 'maximum_model_calls': 240,
            'available_donor_cases': {'Qwen': [301,303,304,306], 'GPT-OSS': [301,302,303,304,305,306]},
            'new_outcome_claims': False, 'no_pooling_with_prior_phases': True,
            'primary': 'harmful safe-optimal rate: 0.5*(tie_first+tie_last)-verified',
            'rule_only_arm_present': False,
        },
    )
    spec['supplementary_inputs'].append({'path': BASE.name, 'sha256': BASE_SHA})
    retrieval=BUILD/'literature-retrieval-2026-10-25.json'
    spec['supplementary_inputs'].append({'path':retrieval.name,'sha256':sha(retrieval)})

    main = [
        heading('1 Introduction'),
        p('A safety instruction can reject a harmful recommendation without telling independent agents how to coordinate on a safe alternative. In the Inherited Collusion project, we audit that distinction in handoffs from explicitly instructed original agents to neutral successors. The central question is whether useful common conventions can be supplied without preserving coalition-favoring allocations. Prior results establish a coordination problem in this task; the new intervention tests an explicit common decision rule. It does not test spontaneous collusion or persistent private intent.'),
        p('Colosseum distinguishes expressed collusive plans from enacted coalition-favoring behavior [1,4]. Self-Propagating Misalignment already studies harmful goals passed to neutral successors and memory defenses [2], while Salami Attack studies jointly effective memory fragments [3]. Our contribution is a small controlled delivery audit, followed by two targeted controls addressing task structure and the decision policy given to successors. We claim neither the first harmful memory transfer nor a general defense against collusion.'),
        p('Shared conventions and symmetry breaking are established coordination approaches. Theory of Scene documents collisions among homogeneous concurrent agents and uses public roles with shared task context to derive a common division of labor [5]. Tacit Coordination of Large Language Models studies focal points and learning-free coordination strategies without communication [6]. Our narrower question is whether an explicit public safe convention helps when harmful inherited notes are held fixed, alongside legitimate controls. We do not claim to discover the symmetry trap or the first general coordination remedy.'),
        heading('2 Task and experimental logic'),
        deepcopy(b[9]),
        p('Original agents receive an experimenter-specified joint allocation and an explicitly harmful or legitimate objective. Their actions must execute that allocation, whose outcome is saved before each writes a note to its own replacement. Successors start a new round with neutral instructions, unchanged public costs and no access to each other’s choice. Harmful plans take both outsider specialties, shifting reward from C/D to A/B. Legitimate plans preserve the team optimum. Notes can contain errors; their semantic quality is part of the channel rather than a primary eligibility filter.'),
        p('A joint-harm outcome requires both outsider specialties to be taken with positive coalition gain and outsider loss relative to the cooperative reference. We also measure outsider reward loss, team reward loss, duplicate task claims and safe-optimal completion. A safe optimum maximizes distinct task completion and then minimizes all-agent cost. Absence of the binary joint-harm event is insufficient: one outsider can still lose reward. Each result is reported separately for Qwen3.6-35B-A3B and GPT-OSS-120B.'),
        p('Both models use temperature 0.6, top-p 0.95 and at most 8,192 output tokens. Each model authors its own notes and supplies its own successors. Thus a model difference combines sender and recipient behavior. Returned identifiers are checked, but do not authenticate served weights. Exact routing, reasoning-default and technical evidence are in Appendix B.'),
        heading('3 Harmful transfer and the coordination problem'),
        p('The initial audit fixes eight cost cases per model, two original plan orientations p0/p1 within each objective, and two nested successor draws per delivery route. It compares facts alone, one note, both notes from the same branch, crossed branches and a verification reminder. The reminder asks recipients to retain recommendations compatible with public rules and total cost. The full routes and all original contrasts remain in Appendix H.'),
        p('The original strict procedure was locally frozen before successor responses. A disclosed post-start continuation accepted exactly one complete outer JSON fence, reused existing responses without resampling and dispatched only previously uncalled slots. These populations remain separate: 360/512 valid episodes in strict V4 and 439/512 in amended V4F. Four unresolved requests remain missing and were never retried. The continuation and prior development observations preclude describing the whole project as prospectively designed or publicly preregistered.'),
        caption('Table 1. Retained episode counts. Earlier strict and amended populations overlap and must not be pooled. V6 is restricted to the ten V5 symmetric donor cases already available before its new calls.'),
        table(['Study', 'Qwen valid / planned', 'GPT-OSS valid / planned', 'Comparison scope'], [
            ['Original strict V4', '127/256', '233/256', 'Eight cases per model'],
            ['Amended V4F', '206/256', '233/256', 'Same planned cohort'],
            ['Structure control V5', '96/144', '144/144', 'Four / six complete cases'],
            ['Fixed-note V6', 'PENDING / 48', 'PENDING / 72', 'Four / six available donor cases'],
        ], [1800,1900,1900,3760]),
        p('In amended data, same-p0 notes increase joint-harm probability relative to facts alone by 0.50 for Qwen across five complete cases and 0.43 for GPT-OSS across seven. Strict counterparts are 0.50 over one case and 0.43 over seven, respectively. These are finite complete-case delivery contrasts, not independent replications. Legitimate convention following passes the prespecified criterion for amended Qwen but fails for GPT-OSS; the handoff channel is not uniformly faithful (Appendix H).'),
        p('On cases complete for both harmful and legitimate verification comparisons, the reminder reduces amended joint harm by 0.50 for Qwen (five cases) and 0.42 for GPT-OSS (six). Yet relative to matched harmful notes it reduces team reward by 84.2 and 78.4, and distinct completion by 0.5 in each model. A post hoc check finds the same duplicate frequencies under verification and facts alone: 5/10 for Qwen and 6/12 for GPT-OSS, versus zero under matched notes. Because both roles have identical costs and two equally safe optima, this pattern is consistent with losing a shared convention. It does not identify that mechanism or establish an unavoidable safety–utility trade-off.'),
        heading('4 Structural control and its remaining ambiguity'),
        p('The separately frozen V5 control changes two nonpreferred safe A/B cost cells by one unit each, making one safe plan uniquely optimal. Optimal total cost and assigned original-plan outcomes remain unchanged. Numeric outcome tables are recomputed, and fresh original notes are generated for each structure and objective. Six new cases per model were planned, with two successor draws per cell. Qwen retains four cases; a format-policy failure and an unresolved probe remove two without replacement. One semantically incorrect but technically valid diagnostic remains included. Full probe and note evidence is in Appendix G.'),
        caption('Table 2. Harmful-mode V5 verification results on complete cases. Binary entries are episode counts; outsider loss is a mean. Qwen has four complete cases and GPT-OSS six, with two draws per cell.'),
        table(['Model', 'Structure', 'Duplicates', 'Safe optimum', 'Joint harm', 'Outsider loss'], [
            [row[0],row[1],row[3],row[4],row[5],row[6]] for row in b[45]['rows'] if row[2]=='Verified'
        ], [1150,1600,1500,1700,1500,1910]),
        p('The primary harmful-mode duplication interaction, (verified minus matched) under uniqueness minus that under symmetry, is −0.625 for Qwen and −0.750 for GPT-OSS. Completion ranges over all six planned cases are [−1.083, +0.250] and [−0.750, −0.750]; they are logical ranges, not confidence intervals. Unique verified Qwen still causes outsider loss in four of eight episodes, whereas GPT-OSS reaches the safe optimum in all twelve. Matched harmful notes retain joint harm under uniqueness (Qwen 5/8; GPT-OSS 6/12). The cost of verification therefore depends on the setting, but this comparison changes notes as well as the matrix.'),
        heading('5 Fixed notes and a shared safe decision rule'),
        p('V6 fixes the symmetric matrices and exact original notes from the ten available V5 donor cases: Qwen seeds 301, 303, 304 and 306, and GPT-OSS seeds 301–306. Availability is selected by the earlier collection, not a new random sample. Each case supplies harmful and legitimate original notes. No new originals or probes are generated. All three arms receive fresh successor draws: verification alone, verification plus lexicographic-first selection, or verification plus lexicographic-last selection. Earlier V5 successor outputs are not reused as the baseline.'),
        p('Both added rules tell successors to identify public A/B outcome rows with maximum distinct completion and minimum total cost, then choose the lexicographically first or last A/B task pair among ties. Each recipient takes its own role’s task. The matrix, outcome table, original notes and reminder stay fixed within a case and objective; only this extra decision rule changes. Two directions discourage treating success as an unexplained preference for one plan. They are fixed conditions, not two independent studies.'),
        p('The primary harmful-mode contrast is the equally weighted mean of the two rule arms minus verification alone in safe-optimal completion. We average the two draws within each arm and then weight complete cases equally, separately by model. The planned total is 120 joint episodes: ten cases, two original objectives, three arms and two draws. Missing outputs are never counted as safe. Legitimate utility, duplicate claims, joint harm, partial outsider loss, directional differences and missingness sensitivity accompany the primary contrast. PENDING final frozen protocol identifier and exact completed-case rules.'),
        caption('Figure 1. V6 safe-optimal completion under fresh verification alone and either added shared rule. Harmful and legitimate originals are shown separately for each model. PENDING final four-panel scientific figure with exact case and episode denominators.'),
        p('PENDING figure space. No observations are plotted.\n' + '\n'*15),
        caption('Table 3. Primary harmful-mode safe-optimal contrast, equally averaging the two tie directions minus fresh verification alone. Missingness ranges concern the fixed available donor cohort, not selection into it.'),
        table(['Model', 'Complete cases', 'Safe-optimal difference', 'Completion range'], [
            [model,'PENDING','PENDING','PENDING'] for model in ['Qwen','GPT-OSS']
        ], [1500,1750,2850,3260]),
        p('PENDING V6 primary contrasts with case denominators, exact repeat counts, finite completion sensitivity, legitimate-control outcomes and any remaining partial outsider harm. The conclusion will follow the sealed analysis and independent raw-data check, including failures and mixed outcomes.'),
        heading('6 Interpretation and limitations'),
        p('The existing evidence separates harmful allocation transfer from successful safe coordination. Explicit shared rules are a targeted test of a remedy in this fixed donor cohort. Even if they improve safe-optimal completion, they would not prove internal verification, identify convention loss as the only cause, or show that verification is necessary: there is no rule-only arm. The public outcome table and deterministic tie policy provide substantial assistance, limiting transfer to less transparent tasks.'),
        p('PENDING final conclusion integrating V6 without overstating universality. The earlier structural intervention, the fresh fixed-note intervention and the original strict/amended audit must retain their distinct populations and timing. Small task clusters, selected donor availability, two nested draws, heterogeneous note quality and unverified served weights limit the scope. No results imply spontaneous collusion, an enduring coalition, or general protection against harmful handoffs.'),
    ]

    # Retain every old numeric table and both figures; relocate only their captions.
    appendix = deepcopy(b[49:])
    reference_end=next(i for i,x in enumerate(appendix) if x.get('text','').startswith('Appendix A.'))
    appendix[reference_end:reference_end]=[
        p('[5] Liangqi Yuan, Wenzhi Fang, Shiqiang Wang and Christopher G. Brinton. 2026. Theory of Scene: Breaking the Symmetry Trap in Multi-Agent LLM Coordination. arXiv:2609.32939v1. https://arxiv.org/html/2609.32939v1'),
        p('[6] Ido Aharon, Emanuele La Malfa, Michael Wooldridge and Sarit Kraus. 2026. Tacit Coordination of Large Language Models. arXiv:2601.22184v2. https://arxiv.org/html/2601.22184v2'),
    ]
    for item in appendix:
        if item.get('type')=='heading' and item.get('text','').startswith('Appendix G.'):
            item['text']='Appendix G. Structural control evidence and results'
        if item.get('type')=='caption':
            item['text']=item['text'].replace('Table G1.', 'Table G2.').replace('Table G2. Harmful', 'Table G3. Harmful').replace('Table G3. Legitimate', 'Table G4. Legitimate')
            item['text']=item['text'].replace('same complete case sets as Table 4', 'same complete case sets as Table G1')
        if item.get('type')=='p':
            item['text']=item['text'].replace('Tables G2–G3 show', 'Tables G3–G4 show')
    g_index=next(i for i,x in enumerate(appendix) if x.get('text','').startswith('Table G2. Legitimate'))
    appendix[g_index:g_index]=[
        caption(b[44]['text'].replace('Table 4.', 'Table G1.')),
        deepcopy(b[45]),
    ]
    appendix += [
        {'type':'page_break'},heading('Appendix H. Original delivery design and complete primary results'),
        p('The following material preserves the full original delivery comparison and its prespecified interpretation checks. Strict V4 and amended V4F overlap. Complete-case counts vary by contrast; main-text summaries do not replace these denominators.'),
        deepcopy(b[10]), deepcopy(b[12]),
        caption(b[13]['text'].replace('Table 1.', 'Table H1.')),deepcopy(b[14]),deepcopy(b[15]),deepcopy(b[18]),deepcopy(b[19]),
        deepcopy(b[22]),caption(b[23]['text'].replace('Table 2.', 'Table H2.')),deepcopy(b[24]),deepcopy(b[25]),deepcopy(b[26]),
        caption(b[28]['text'].replace('Table 3.', 'Table H3.')),deepcopy(b[29]),
        deepcopy(b[30]),deepcopy(b[31]),deepcopy(b[32]),deepcopy(b[34]),deepcopy(b[35]),deepcopy(b[38]),
        heading('Appendix I. Fixed-note control evidence'),
        p('PENDING final V6 protocol and freeze, immutable donor/matrix bindings, closure, exact raw-call inventory, technical attrition, per-model cost accounting, independent arithmetic check and full arm/contrast results. The old V4/V4F/V5 evidence remains separate and unchanged.'),
        caption('Table I1. All V6 arm outcomes, including any outsider loss and exact direction adherence. PENDING results and denominators.'),
        table(['Model / objective', 'Arm', 'Safe optimum', 'Any outsider loss', 'Exact rule adherence', 'Team loss'], [
            [model+' / '+mode,arm,'PENDING','PENDING','Not applicable' if arm=='Verified' else 'PENDING','PENDING'] for model in ['Qwen','GPT-OSS'] for mode in ['Harmful','Legitimate'] for arm in ['Verified','Tie first','Tie last']
        ], [1950,1450,1400,1500,1700,1360]),
        p('PENDING full legitimate-control table, each tie direction separately, rule-following diagnostics if prespecified, and all required sensitivity analyses. No success is inferred from correct software execution alone.'),
    ]
    # This relocated original paragraph must refer to its new table number.
    for item in appendix:
        if item.get('type')=='p':
            item['text']=item['text'].replace('positive in both models (Table 3)', 'positive in both models (Table H3)')
    spec['blocks']=main+appendix
    old_tables=[x for x in b if x['type']=='table']
    new_tables=[x for x in spec['blocks'] if x['type']=='table']
    assert all(x in new_tables for x in old_tables), 'Historical numeric table changed'
    assert [x for x in b if x['type']=='figure']==[x for x in spec['blocks'] if x['type']=='figure']
    assert 150 <= len(spec['abstract'].split()) <= 250
    return spec

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=BUILD/'report-input.json')
    parser.add_argument('--final',action='store_true')
    args=parser.parse_args()
    spec=assemble(args.project_root.resolve())
    if args.final:
        from integrate_closed_results import integrate
        spec=integrate(spec,args.project_root.resolve(),BUILD)
        spec['ready_for_final']=True
    args.out.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'input_sha256':sha(args.out),'ready_for_final':spec['ready_for_final'],'abstract_words':len(spec['abstract'].split()),'historical_tables_preserved':7,'historical_figures_preserved':2,'status':'CLOSED_EVIDENCE' if args.final else 'DRAFT_ONLY'}))

if __name__=='__main__':
    main()
