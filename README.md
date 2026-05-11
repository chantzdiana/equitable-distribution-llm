# Equitable Distribution Analyzer

A computational tool for analyzing New York equitable distribution opinions. The system identifies which statutory factors under NY Domestic Relations Law §236(B)(5)(d) actually drove a court's reasoning — not merely which ones were mentioned — and uses those factor profiles to find structurally similar prior decisions.

**Live app:** [equitable-distribution-llm.streamlit.app](https://equitable-distribution-llm.streamlit.app)

---

## The Problem This Solves

New York divorce law gives judges 16 statutory factors to consider when dividing marital property. Courts do not weight them equally, and judicial opinions routinely mention many factors while actually relying on one or two. Identifying which factors are doing real work in the reasoning requires parsing evaluative judicial language — something keyword-based tools like Westlaw cannot do.

This tool is built around a single distinction: **mentioned vs. decisive**. A factor appearing in an opinion is not the same as a factor driving the outcome. The LLM extraction layer is specifically designed to detect which factors courts treat as outcome-determinative.

---

## What the System Does

### Analyzer Page
Upload one or more judicial opinion files (`.txt` or `.pdf`). The system sends each to GPT-4o-mini with a prompt designed to detect decisive legal reasoning language — phrases like "primary consideration," "determinative," and "the court relies heavily on." For each case it returns:

- The dominant statutory factor
- A confidence level (high / medium / low)
- A plain-English explanation of the court's reasoning

Across all uploaded cases, it produces an aggregate Factor Emphasis summary showing which factors were frequently, sometimes, or rarely decisive — along with the statutory citation and typical reasoning for the dominant factor.

### Case Similarity Page
Enter a plain-language description of a case's facts. The system runs the full pipeline on the input text, builds a 16-dimensional factor vector, and compares it against all indexed cases using a hybrid similarity score:

- **70%** IDF-weighted cosine similarity between factor vectors
- **30%** semantic text similarity via sentence-transformer embeddings

Returns the top 8 most structurally similar cases from the evaluation dataset.

### Validation Dashboard
Shows how accurately the model performs against 22 human-labeled New York opinions, including Top-1 accuracy, precision and recall by factor, stability across repeated runs, truncation robustness, and noise robustness.

---

## How It Works

### 1. LLM Factor Extraction — `src/extract_factors.py`

Each opinion is split into 2,500-word chunks. Each chunk is sent to GPT-4o-mini with a prompt instructing it to detect decisive reasoning language rather than count factor mentions. Results are aggregated across chunks: `mentioned` flags use logical OR, `most_weighted` lists merge and deduplicate to top 3, confidence takes the maximum, explanation uses the first non-empty response.

Results are cached by MD5 hash of the input text to avoid redundant API calls.

### 2. Vectorization — `src/vectorize.py`

The LLM's JSON output is converted into a 16-dimensional numerical vector — one position per statutory factor, always in the same fixed order. Encoding:

| Condition | Value |
|---|---|
| Not mentioned | 0.0 |
| Mentioned, not decisive | 0.5 |
| 3rd most weighted | 0.7 |
| 2nd most weighted | 0.85 |
| 1st most weighted | 1.0 |

The LLM decides which factors mattered and in what order. The vector function mechanically translates that judgment into numbers. They are completely separate steps.

### 3. Similarity Search — `src/similarity.py`

Factor vectors are compared using cosine similarity — a measure of the angle between two vectors in 16-dimensional space. Before comparison, stored vectors are adjusted by IDF (Inverse Document Frequency) weights that downweight common factors and amplify rare ones, preventing the similarity search from being dominated by the most frequent factor in the dataset.

A second signal — semantic text similarity via the `all-MiniLM-L6-v2` sentence-transformer model — captures factual narrative similarity between cases. The two signals are blended 70/30.

### 4. Evaluation — `src/main.py`

Runs offline against the labeled dataset. For each case: LLM extraction (configurable number of runs), truncation robustness (first half / second half / middle third), noise robustness (punctuation removal + sentence dropout), vectorization, and storage to `data/eval/eval_log.jsonl`.

---

## Evaluation Dataset

22 human-labeled New York equitable distribution opinions covering 11 of the 16 statutory factors:

| Factor | Cases |
|---|---|
| contributions_to_marital_property_and_career | 8 |
| custodial_parent_residence_needs | 2 |
| wasteful_dissipation_of_assets | 3 |
| difficulty_of_asset_valuation_or_business_interests | 1 |
| domestic_violence | 1 |
| contributions_to_marital_property_and_career (Elkus) | 1 |
| loss_of_inheritance_and_pension_rights | 1 |
| other_just_and_proper_factor | 1 |
| tax_consequences | 1 |
| future_financial_circumstances | 1 |
| liquidity_of_assets | 1 |
| loss_of_health_insurance | 1 |

---

## Evaluation Results

Benchmarked against 22 human-labeled opinions:

- **Top-1 Accuracy:** 100%
- **Stability:** 1.00 / 1.0
- **Truncation Robustness:** 0.44 / 1.0
- **Noise Robustness:** 0.69 / 1.0

Top-1 accuracy reflects the model's #1 predicted factor matching the human-labeled ground truth. Truncation robustness measures consistency when the model sees only a portion of each opinion — lower scores indicate decisive language is concentrated in one section rather than distributed throughout.

---

## Project Structure

```
equitable-distribution-llm/
├── app.py                          # Streamlit web interface (5 pages)
├── main.py                         # Offline evaluation pipeline
├── requirements.txt
├── src/
│   ├── extract_factors.py          # LLM extraction, chunking, caching
│   ├── vectorize.py                # 16-dim factor vector encoding
│   ├── similarity.py               # Cosine similarity, IDF, embeddings
│   ├── user_similarity.py          # Pipeline orchestrator for app
│   ├── cache.py                    # MD5 hash-based result cache
│   └── factor_explanations.py      # Statutory citations and summaries
├── data/
│   ├── raw/
│   │   ├── eval_cases/             # Labeled evaluation opinions (.txt)
│   │   └── ny_real_snippets/       # Additional case excerpts (.txt)
│   ├── eval/
│   │   ├── eval_log.jsonl          # Per-case evaluation records
│   │   ├── human_labels.csv        # Ground truth factor labels
│   │   └── run_history.jsonl       # Historical evaluation summaries
│   └── cache/
│       └── cache.json              # LLM result cache (gitignored)
```

---

## Running Locally

**Prerequisites:** Python 3.10+, OpenAI API key

```bash
git clone https://github.com/chantzdiana/equitable-distribution-llm.git
cd equitable-distribution-llm
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
OPENAI_API_KEY=sk-your-key-here
```

Run the Streamlit app:
```bash
streamlit run app.py
```

Run the evaluation pipeline:
```bash
python3 -m src.main
```

---

## Adding New Cases

1. Obtain the full opinion text and save as a `.txt` file with a metadata header:
```
JURISDICTION: New York
COURT: Appellate Division, First Department
YEAR: 1991
JUDGE: Rosenberger
```
2. Place the file in `data/raw/eval_cases/`
3. Add a row to `data/eval/human_labels.csv`:
```
filename.txt,dominant_factor_name
```
4. Run `python3 -m src.main` to regenerate `eval_log.jsonl`
5. Push `eval_log.jsonl` and `human_labels.csv` — the deployed app immediately searches the expanded dataset

---

## Deployment

Deployed to [Streamlit Community Cloud](https://streamlit.io/cloud). The app auto-redeploys on every push to the `main` branch. The OpenAI API key is stored in Streamlit's encrypted secrets manager and never appears in the repository.

---

## Limitations

- **Dataset size:** 22 cases covering 11 of 16 statutory factors. Results are descriptive, not statistically generalizable.
- **Single annotator:** Ground truth labels were created by one annotator. Inter-annotator agreement has not yet been measured.
- **Single jurisdiction:** New York only. The methodology could extend to other equitable distribution states but has not been tested.
- **Mentioned vs. decisive:** The model correctly avoids over-predicting factors that are merely discussed. Cases like *Elkus v. Elkus* — which address a threshold legal question rather than factor weighing — return low confidence as expected behavior, not a failure.
- **Results are descriptive:** The system identifies reasoning patterns in past opinions. It does not predict outcomes in any individual case.

---

## Societal Impact

By reducing the cost and complexity of doctrinal research, this tool aims to support more efficient legal representation. Surfacing patterns in judicial reasoning helps lawyers better understand how courts apply equitable distribution standards, improve argument prioritization, and serve clients with limited resources more effectively.

---

## Status

Active development. Originally developed for a Computer Science for Lawyers course at Georgetown University Law Center. Currently expanding the case dataset and evaluation methodology toward a practitioner-facing research tool.

---

## License

MIT


