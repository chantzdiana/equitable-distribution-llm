# Equitable Distribution LLM

# Equitable Distribution Factor Analysis (Prototype)

## Overview

This project is a prototype legal analytics tool designed to help lawyers understand **which statutory factors courts actually emphasize** when applying equitable distribution in divorce cases.

While equitable distribution statutes—such as New York Domestic Relations Law § 236(B)(5)(d)—enumerate many factors, courts rarely weigh all of them in every case. Instead, judicial opinions tend to emphasize a smaller subset of considerations depending on the facts. This project explores whether large language models (LLMs) can help surface those patterns more efficiently than traditional rule-based approaches.

The prototype analyzes judicial opinions (or excerpts) and identifies which statutory factors appear to play a meaningful role in the court’s reasoning. It then aggregates results across cases to provide **jurisdiction-level insight** into factor emphasis.

---

## Motivation

For practicing family law attorneys, equitable distribution analysis is time-consuming and often qualitative. Lawyers must read many cases to understand how a given jurisdiction tends to reason about:

* contributions to marital property or career development
* custodial parent housing needs
* dissipation or improper transfers
* duration of marriage and related considerations

This tool is motivated by a practical question a real lawyer might ask:

> *“In this jurisdiction, which equitable-distribution factors do courts actually focus on most often?”*

By automating part of that analysis, the project aims to:

* reduce research time and cost,
* help lawyers prioritize arguments,
* and improve access to justice by lowering informational barriers.

---

## What the System Does

1. **Input**

   * Short case excerpts or sample opinions (currently `.txt` files)
   * Each file includes simple metadata (jurisdiction, court, year)

2. **Extraction**

   * A large language model analyzes the text
   * It outputs a structured JSON object indicating whether each statutory factor is emphasized

3. **Aggregation**

   * Results are aggregated across multiple cases
   * Factors are summarized as:

     * *Frequently emphasized*
     * *Sometimes emphasized*
     * *Rarely emphasized*

4. **Context Summary**

   * The system prints a lawyer-readable summary of:

     * jurisdiction
     * courts
     * year range
     * number of cases analyzed

---

## Example Output

```
=== Analysis Context ===

Jurisdiction: New York
Courts: Supreme Court, Appellate Division
Years Covered: 1996–2019
Number of Cases Analyzed: 3

=== New York Equitable Distribution Factor Emphasis ===

Frequently emphasized:
- contributions_to_marital_property_and_career (67%)

Sometimes emphasized:
- custodial_parent_housing_needs (33%)
- wasteful_dissipation_of_assets (33%)
- improper_transfers_or_encumbrances (33%)
- duration_of_marriage_age_and_health (33%)
```

---

## Methodology

### Factor Schema

The factor schema is derived directly from **New York Domestic Relations Law § 236(B)(5)(d)**. Closely related statutory considerations are grouped into higher-level conceptual factors to reflect how courts typically discuss them in practice.

This grouping preserves fidelity to the statute while enabling structured extraction.

### Rule-Based vs LLM Extraction

The project originally implemented a rule-based baseline using keyword matching. That approach consistently over-identified factors due to lack of context and inability to handle negation or emphasis.

The LLM-based approach proved more selective and better aligned with judicial reasoning, particularly in cases where courts explicitly downplayed certain factors or focused narrowly on one consideration.

---

## Limitations

* The current prototype uses **sample cases and short excerpts**, not a comprehensive corpus.
* Results are **descriptive**, not predictive.
* The system does **not** attempt to forecast outcomes or assign numerical weights.
* Judge-level analysis is not yet implemented.
* LLM output is non-deterministic; defensive parsing is used to ensure robustness.

These limitations are intentional to keep the prototype scoped and ethically responsible.

---

## Future Work

Planned or possible extensions include:

* Judge-level aggregation (descriptive, not predictive)
* Support for additional jurisdictions
* A simple user interface allowing lawyers to paste case text
* Exporting results to CSV for use in briefs or memos

The architecture is designed to support these extensions without major refactoring.

---

## Societal Impact

By reducing the cost and complexity of doctrinal research, this project aims to support more efficient and equitable legal representation. Tools that surface patterns in judicial reasoning can help lawyers better serve clients with limited resources and improve transparency in how legal standards are applied in practice.

---

## How to Run

```bash
python src/main.py
```

---

## Status

This project is a functional prototype developed for a Computer Science for Lawyers course. It is intended as an exploratory and educational tool.

---


