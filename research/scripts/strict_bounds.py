"""Post-start sensitivity helper; no model calls, file loading, or data selection.

Supply only strict-eligible observed outcomes; a wrapper-rejected answer is
missing here even if an amended analysis can recover it. Bounds are extrema
over the finite fixture, not confidence intervals or missing-at-random estimates.
"""
from itertools import product
import math


def number(value):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected a finite numeric outcome or bound")
    return float(value)


def possible_metric_ranges(checkpoint, scorer, metrics):
    """Enumerate all 16 public A/B choices, without looking at study outcomes."""
    tasks = tuple(sorted(checkpoint["tasks"]))
    if len(tasks) != 4:
        raise ValueError("The frozen fixture must have exactly four tasks")
    outcomes = [scorer(checkpoint, {"A": left, "B": right})
                for left, right in product(tasks, repeat=2)]
    return {metric: (min(number(o[metric]) for o in outcomes),
                     max(number(o[metric]) for o in outcomes))
            for metric in metrics}


def linear_contrast_bounds(components, coefficients, metric_ranges):
    """Bound a contrast using observed components and public missing ranges.

    components maps each condition to an eligible outcome dict or None.
    A missing key also means missing. Observed components cannot be imputed
    from a saved strict-invalid episode. Negative contrast coefficients reverse
    endpoints, which also supports balanced source and presence contrasts.
    """
    if not coefficients:
        raise ValueError("A contrast needs at least one component")
    terms = {condition: number(coefficient)
             for condition, coefficient in coefficients.items()}
    if any(coefficient == 0 for coefficient in terms.values()):
        raise ValueError("Omit zero-weight components from a contrast")
    results = {}
    observed = sum(components.get(condition) is not None for condition in terms)
    for metric, interval in metric_ranges.items():
        lo, hi = map(number, interval)
        if lo > hi:
            raise ValueError("Invalid public outcome interval")
        lower, upper = 0.0, 0.0
        for condition, coefficient in terms.items():
            outcome = components.get(condition)
            if outcome is None:
                left, right = lo, hi
            else:
                left = right = number(outcome[metric])
                if left < lo - 1e-9 or left > hi + 1e-9:
                    raise ValueError("Observed outcome is outside public fixture range")
            first, second = coefficient * left, coefficient * right
            lower += min(first, second)
            upper += max(first, second)
        results[metric] = {"lower": lower, "upper": upper}
    return {"bounds": results, "planned_components": len(terms),
            "observed_components": observed,
            "missing_components": len(terms) - observed,
            "complete": observed == len(terms)}


def planned_contrast_bounds(outcomes, ranges_by_case, coefficients,
                            case_seeds=tuple(range(201, 209)), repeats=(0, 1)):
    """Keep all planned case/repeat cells and weight every case equally.

    outcomes[seed][repeat][condition] is an eligible outcome dict or None.
    ranges_by_case must contain public metric ranges for every planned seed.
    Extra seeds/repeats are rejected rather than silently changing denominators.
    """
    if not case_seeds or len(set(case_seeds)) != len(case_seeds):
        raise ValueError("Use distinct planned case seeds")
    if not repeats or len(set(repeats)) != len(repeats):
        raise ValueError("Use distinct planned repetition IDs")
    if set(outcomes) - set(case_seeds) or set(ranges_by_case) != set(case_seeds):
        raise ValueError("Outcomes/ranges must follow the fixed planned case set")
    metrics = tuple(ranges_by_case[case_seeds[0]])
    if not metrics or any(set(ranges_by_case[s]) != set(metrics) for s in case_seeds):
        raise ValueError("Every case needs the same nonempty metric set")
    cases = []
    for seed in case_seeds:
        data = outcomes.get(seed, {})
        if set(data) - set(repeats):
            raise ValueError("Unexpected repetition outside the fixed schedule")
        rows = [{"repeat": rep, **linear_contrast_bounds(
                    data.get(rep, {}), coefficients, ranges_by_case[seed])}
                for rep in repeats]
        cases.append({"seed": seed, "repetitions": rows,
                      "complete": all(r["complete"] for r in rows),
                      "bounds": {metric: {
                          endpoint: sum(r["bounds"][metric][endpoint] for r in rows) / len(repeats)
                          for endpoint in ("lower", "upper")}
                          for metric in metrics}})
    return {"analysis": "Post-start strict planned-cohort worst-case sensitivity bounds",
            "not_confidence_intervals": True,
            "missing_at_random_assumed": False,
            "case_weighting": "Equal planned-case weights; equal repeats within each case",
            "planned_cases": len(case_seeds), "planned_repeats_per_case": len(repeats),
            "complete_cases": sum(case["complete"] for case in cases),
            "planned_components": sum(r["planned_components"] for c in cases for r in c["repetitions"]),
            "observed_components": sum(r["observed_components"] for c in cases for r in c["repetitions"]),
            "missing_components": sum(r["missing_components"] for c in cases for r in c["repetitions"]),
            "coefficients": dict(coefficients), "cases": cases,
            "bounds": {metric: {
                endpoint: sum(case["bounds"][metric][endpoint] for case in cases) / len(cases)
                for endpoint in ("lower", "upper")}
                for metric in metrics}}
