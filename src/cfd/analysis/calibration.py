"""Weight calibration and synthetic fixtures for fraud score optimization."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

from cfd.config.settings import Settings
from cfd.graph.scoring import CONFIDENCE_LEVELS, DEFAULT_WEIGHTS

logger = logging.getLogger(__name__)

INDICATOR_TYPES = list(DEFAULT_WEIGHTS.keys())


@dataclass
class CalibrationSample:
    """A labeled sample for calibration."""

    author_id: str
    indicators: dict[str, float]  # indicator_type -> value [0, 1]
    expected_level: str  # "normal", "low", "moderate", "high", "critical"
    theorem3_passed: bool = False  # Theorem 3 (k>=5) → at least moderate


@dataclass
class CalibrationResult:
    """Result of weight optimization."""

    optimized_weights: dict[str, float]
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    fpr: float = 0.0  # false positive rate
    samples_used: int = 0
    iterations: int = 0
    converged: bool = False
    details: dict = field(default_factory=dict)


_LEVEL_ORDER = {"normal": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4}


def _score_to_level(score: float) -> str:
    """Map a fraud score to a confidence level."""
    for low, high, level in CONFIDENCE_LEVELS:
        if low <= score < high:
            return level
    return "critical"


def _level_to_numeric(level: str) -> int:
    """Convert level string to numeric order."""
    return _LEVEL_ORDER.get(level, 0)


def build_synthetic_fixtures() -> list[CalibrationSample]:
    """Generate synthetic calibration samples covering clean, moderate, high, and edge cases.

    Returns a list of CalibrationSample with known expected levels.
    """
    samples: list[CalibrationSample] = []

    # --- Clean authors (expected: normal) ---
    samples.append(CalibrationSample(
        author_id="clean_01",
        indicators={t: 0.0 for t in INDICATOR_TYPES},
        expected_level="normal",
    ))
    samples.append(CalibrationSample(
        author_id="clean_02",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "SCR": 0.10, "MCR": 0.05, "CV": 0.10,
        },
        expected_level="normal",
    ))
    samples.append(CalibrationSample(
        author_id="clean_03",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "SCR": 0.15, "TA": 0.10, "CB": 0.05, "RLA": 0.05,
        },
        expected_level="normal",
    ))

    # --- Low suspicion (expected: low) ---
    samples.append(CalibrationSample(
        author_id="low_01",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "SCR": 0.30, "MCR": 0.20, "CB": 0.15, "TA": 0.20,
        },
        expected_level="low",
    ))
    samples.append(CalibrationSample(
        author_id="low_02",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "SCR": 0.25, "CC": 0.30, "SSD": 0.20, "ANA": 0.15,
        },
        expected_level="low",
    ))

    # --- Moderate suspicion (expected: moderate) ---
    samples.append(CalibrationSample(
        author_id="mod_01",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "SCR": 0.50, "MCR": 0.40, "CB": 0.40, "TA": 0.50,
            "CLIQUE": 0.40, "COMMUNITY": 0.30,
        },
        expected_level="moderate",
    ))
    samples.append(CalibrationSample(
        author_id="mod_02",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "SCR": 0.40, "MCR": 0.35, "CB": 0.30, "TA": 0.40,
            "CC": 0.50, "SSD": 0.40, "ANA": 0.30,
        },
        expected_level="moderate",
    ))
    # Theorem 3 anchor: k>=5 triggered → at least moderate
    samples.append(CalibrationSample(
        author_id="mod_t3",
        indicators={
            **{t: 0.20 for t in INDICATOR_TYPES},
            "SCR": 0.50, "MCR": 0.45, "CB": 0.40, "TA": 0.50, "HTA": 0.45,
            "CLIQUE": 0.35, "COMMUNITY": 0.30, "CV": 0.30,
        },
        expected_level="moderate",
        theorem3_passed=True,
    ))

    # --- High suspicion (expected: high) ---
    samples.append(CalibrationSample(
        author_id="high_01",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "SCR": 0.70, "MCR": 0.60, "CB": 0.60, "TA": 0.70,
            "HTA": 0.50, "CLIQUE": 0.60, "COMMUNITY": 0.50,
            "CV": 0.50, "CC": 0.60,
        },
        expected_level="high",
    ))
    samples.append(CalibrationSample(
        author_id="high_02",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "SCR": 0.60, "MCR": 0.55, "CB": 0.50, "TA": 0.60,
            "RLA": 0.50, "GIC": 0.60, "SSD": 0.70, "CC": 0.50,
            "PAGERANK": 0.40,
        },
        expected_level="high",
    ))

    # --- Critical (expected: critical) ---
    samples.append(CalibrationSample(
        author_id="crit_01",
        indicators={t: 0.80 for t in INDICATOR_TYPES},
        expected_level="critical",
    ))
    samples.append(CalibrationSample(
        author_id="crit_02",
        indicators={t: 1.0 for t in INDICATOR_TYPES},
        expected_level="critical",
    ))

    # --- Edge cases ---
    # Only new indicators suspicious
    samples.append(CalibrationSample(
        author_id="edge_new_only",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "ANA": 0.60, "SSD": 0.70, "CC": 0.60, "CPC": 0.50,
        },
        expected_level="low",
    ))
    # Only graph indicators suspicious
    samples.append(CalibrationSample(
        author_id="edge_graph_only",
        indicators={
            **{t: 0.0 for t in INDICATOR_TYPES},
            "EIGEN": 0.60, "BETWEENNESS": 0.50, "PAGERANK": 0.60,
            "COMMUNITY": 0.50, "CLIQUE": 0.60,
        },
        expected_level="low",
    ))

    return samples


def _compute_score(indicators: dict[str, float], weights: dict[str, float]) -> float:
    """Compute weighted fraud score from indicator values and weights."""
    weighted_sum = 0.0
    total_weight = 0.0
    for itype, w in weights.items():
        val = indicators.get(itype, 0.0)
        weighted_sum += w * val
        total_weight += w
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def calibrate_weights(
    samples: list[CalibrationSample],
    settings: Settings | None = None,
    max_iter: int = 200,
) -> CalibrationResult:
    """Optimize indicator weights to minimize classification error.

    Uses SLSQP with constraints:
    - sum(weights) = 1.0
    - each weight in [0.01, 0.20]
    - Theorem 3 anchor: samples with theorem3_passed must score >= moderate (0.4)

    Returns CalibrationResult with optimized weights and metrics.
    """
    n = len(INDICATOR_TYPES)

    def _objective(w_array: np.ndarray) -> float:
        weights = {INDICATOR_TYPES[i]: float(w_array[i]) for i in range(n)}
        total_loss = 0.0
        for sample in samples:
            score = _compute_score(sample.indicators, weights)
            predicted_level = _score_to_level(score)
            pred_num = _level_to_numeric(predicted_level)
            expected_num = _level_to_numeric(sample.expected_level)
            # Squared error on level ordinal
            total_loss += (pred_num - expected_num) ** 2
            # Theorem 3 penalty: if theorem3_passed, score must be >= 0.4 (moderate)
            if sample.theorem3_passed and score < 0.4:
                total_loss += 10.0 * (0.4 - score) ** 2
        return total_loss / len(samples)

    # Initial weights from DEFAULT_WEIGHTS
    w0 = np.array([DEFAULT_WEIGHTS[t] for t in INDICATOR_TYPES], dtype=float)

    # Constraints: sum = 1
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    # Bounds: each weight in [0.01, 0.20]
    bounds = [(0.01, 0.20)] * n

    result = minimize(
        _objective, w0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"maxiter": max_iter, "ftol": 1e-10},
    )

    optimized = {INDICATOR_TYPES[i]: round(float(result.x[i]), 6) for i in range(n)}

    # Evaluate metrics
    eval_result = evaluate_calibration(samples, optimized)

    return CalibrationResult(
        optimized_weights=optimized,
        precision=eval_result["precision"],
        recall=eval_result["recall"],
        f1=eval_result["f1"],
        fpr=eval_result["fpr"],
        samples_used=len(samples),
        iterations=result.nit,
        converged=result.success,
        details={"scipy_message": result.message, "final_loss": float(result.fun)},
    )


def evaluate_calibration(
    samples: list[CalibrationSample],
    weights: dict[str, float],
    settings: Settings | None = None,
) -> dict:
    """Evaluate weight performance on labeled samples.

    Returns dict with precision, recall, f1, fpr, confusion details.
    """
    # Binary classification: "suspicious" = moderate/high/critical, "clean" = normal/low
    tp = fp = tn = fn = 0
    misclassified: list[dict] = []

    for sample in samples:
        score = _compute_score(sample.indicators, weights)
        predicted = _score_to_level(score)
        pred_suspicious = _level_to_numeric(predicted) >= 2
        expected_suspicious = _level_to_numeric(sample.expected_level) >= 2

        if pred_suspicious and expected_suspicious:
            tp += 1
        elif pred_suspicious and not expected_suspicious:
            fp += 1
            misclassified.append({"id": sample.author_id, "predicted": predicted, "expected": sample.expected_level})
        elif not pred_suspicious and expected_suspicious:
            fn += 1
            misclassified.append({"id": sample.author_id, "predicted": predicted, "expected": sample.expected_level})
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "misclassified": misclassified,
    }
