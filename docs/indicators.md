# Indicators

CFD computes 20 indicators grouped into 5 categories. Each indicator produces a normalized value in [0, 1] where higher values indicate greater suspicion.

## Core Citation Indicators

### SCR — Self-Citation Ratio

Fraction of an author's citations that are self-citations.

$$SCR = \frac{\text{self-citations}}{\text{total citations}}$$

| Threshold | Level |
|-----------|-------|
| > 0.25 | Warning |
| > 0.40 | High |

### MCR — Mutual Citation Ratio

Proportion of reciprocal citations between author pairs.

$$MCR = \frac{2 \cdot \min(A \to B, B \to A)}{A \to B + B \to A}$$

Threshold: > 0.30

### CB — Citation Burst

Unusually high citation activity in a short window, detected via Z-score.

Threshold: Z > 3.0

### TA — Temporal Anomaly

Irregular temporal distribution of received citations (Z-score based).

Threshold: Z > 3.0

### HTA — H-index Temporal Anomaly

Abnormal growth rate of h-index over time (dh/dt analysis).

## Reference & Geographic Indicators

### RLA — Reference List Anomaly

Combines self-reference rate with reference concentration (Herfindahl index).

$$RLA = 0.5 \cdot \text{self\_ref\_rate} + 0.5 \cdot \text{reference\_concentration}$$

### GIC — Geographic/Institutional Concentration

Shannon entropy of citing sources. Low entropy (citations from few sources) signals potential manipulation.

$$GIC = 1 - \frac{H}{\log_2(n)}$$

## Graph-Based Indicators

### EIGEN — Eigenvector Centrality

Influence in the citation network based on connections to other influential nodes.

### BETWEENNESS — Betweenness Centrality

How often the author lies on shortest paths between other authors.

### PAGERANK — PageRank

Adapted Google PageRank applied to the citation network.

### COMMUNITY — Community Anomaly

Deviation from expected community structure based on Louvain detection.

### CLIQUE — Clique Participation

Membership in dense citation cliques (fully-connected subgraphs).

## Temporal & Velocity Indicators

### CV — Citation Velocity

Rate of citation accumulation over time. Sudden spikes are suspicious.

### SBD — Sleeping Beauty Detector

Identifies papers with delayed recognition patterns (long dormancy followed by sudden citations).

## Contextual & Advanced Indicators

### CTX — Contextual Signal

Discipline-baseline comparison: how the author's metrics deviate from field norms.

### ANA — Authorship Network Anomaly

Unusual patterns in co-authorship networks.

### PB — Peer Benchmark

Comparison against peer group medians for key metrics.

### SSD — Salami Slicing Detector

Identifies potential fragmentation of work into minimal publishable units based on title/abstract similarity.

### CC — Citation Cannibalism

Detects when an author's newer papers disproportionately cite their own older papers.

### CPC — Cross-Platform Consistency

Compares metrics across data sources (OpenAlex vs Scopus) for discrepancies.

## Scoring

The final fraud score is a weighted average of all available indicators:

$$\text{Score} = \sum_{i} w_i \cdot \text{normalize}(I_i)$$

Default weights (sum = 1.0):

| Indicator | Weight |
|-----------|--------|
| SCR | 0.08 |
| MCR | 0.10 |
| CB | 0.06 |
| TA | 0.08 |
| HTA | 0.06 |
| RLA | 0.05 |
| GIC | 0.05 |
| EIGEN | 0.03 |
| BETWEENNESS | 0.03 |
| PAGERANK | 0.05 |
| COMMUNITY | 0.03 |
| CLIQUE | 0.03 |
| CV | 0.06 |
| SBD | 0.04 |
| CTX | 0.04 |
| ANA | 0.05 |
| PB | 0.04 |
| SSD | 0.05 |
| CC | 0.04 |
| CPC | 0.03 |

## Mathematical Theorems

### Theorem 1: Perron-Frobenius

Applies Perron-Frobenius theorem to the citation adjacency matrix. An anomalously high leading eigenvalue relative to the spectral gap indicates concentrated citation flow.

### Theorem 2: Ramsey-Based Clique Detection

Uses Ramsey theory bounds to detect whether the citation graph contains unexpectedly large cliques.

### Theorem 3: Benford's Law

Tests whether citation count distributions follow Benford's law. Significant deviations may indicate artificial manipulation.
