# Equitable Distribution Analyzer

A computational tool for analyzing New York equitable distribution opinions. The system identifies which statutory factors under NY Domestic Relations Law §236(B)(5)(d) actually drove a court's reasoning — not merely which ones were mentioned — and uses those factor profiles to find structurally similar prior decisions.

**Live app (no setup required):** [equitable-distribution-llm.streamlit.app](https://equitable-distribution-llm.streamlit.app)

> **Note for Professor Ohm and Patrick:** The easiest way to evaluate this project is to visit the live app link above. It is fully functional in any browser with no installation, no API key, and no configuration. If you would prefer to run the code locally, complete setup instructions are in the section below.

---

## Quickest Way to Evaluate — Use the Live App

The application is deployed at **equitable-distribution-llm.streamlit.app**. Everything works immediately:

- **Analyzer page:** Upload any of the `.txt` or `.pdf` opinion files from `data/raw/eval_cases/` to see the factor extraction in action
- **Case Similarity page:** Type a plain-language description of a case's facts to find similar decisions
- **Sample inputs for the Case Similarity page:**
- "The wife supported her husband through medical school while 
  working full time. After he obtained his license he filed for 
  divorce. The only significant asset is his enhanced earning capacity."
- "The husband transferred marital funds to a separate account 
  shortly before the divorce action was filed, with no documentation 
  of legitimate purpose."
- **Validation Dashboard:** View the full evaluation results against the 21 human-labeled cases

No API key, no Python, no installation needed.

---

## Running Locally — Step-by-Step Setup

If you prefer to run the code on your own machine, follow these steps exactly.

### Step 1 — Prerequisites

- Python 3.10 or higher
- pip
- An OpenAI API key (required to analyze new cases; not required to view the Validation Dashboard or Evaluation Log)


### Step 2 — Install Dependencies

From the project directory:

```bash
pip install -r requirements.txt
```

This installs: streamlit, openai, sentence-transformers, python-dotenv, numpy, torch (CPU version), scikit-learn, and pdfplumber.

**If torch fails to install**, run this instead:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Step 3 — Add Your API Key

Create a file named `.env` in the root of the project directory (the same folder as `app.py`). The file should contain exactly one line:

```
OPENAI_API_KEY=sk-your-key-here
```

Replace `sk-your-key-here` with your actual OpenAI API key. This file is never committed to any repository — it stays only on your machine.

**Without this file**, the Analyzer and Case Similarity pages will fail with an authentication error. The Validation Dashboard and Evaluation Log pages will still work because they read from pre-computed files and do not call the API.

### Step 4 — Run the App

```bash
streamlit run app.py
```

This opens the application in your browser at `http://localhost:8501`. The first launch takes 30-60 seconds as the sentence-transformer embedding model downloads and initializes — this is normal.

### Step 5 — Run the Evaluation Pipeline (Optional)

To re-run the full evaluation against the labeled dataset:

```bash
python3 -m src.main
```


---

## How the System Works

### The Core Distinction: Mentioned vs. Decisive

NY Domestic Relations Law §236(B)(5)(d) lists sixteen factors courts must consider in equitable distribution. Courts do not weigh them equally. Judicial opinions routinely mention many factors while actually relying on one or two. Keyword-based tools like Westlaw return every case that mentions a term regardless of whether that term drove the outcome. This system detects the difference by identifying the evaluative judicial language courts use when a factor is outcome-determinative.

### Pipeline

1. **LLM Extraction** (`src/extract_factors.py`) — Each opinion is split into 2,500-word chunks and sent to GPT-4o-mini with a prompt instructing it to detect decisive reasoning language. Results are cached by MD5 hash to avoid redundant API calls.

2. **Vectorization** (`src/vectorize.py`) — The LLM's output is converted into a 16-dimensional numerical vector, one position per statutory factor. Top-ranked factor → 1.0, second → 0.85, third → 0.7, mentioned but not decisive → 0.5, absent → 0.0.

3. **Similarity Search** (`src/similarity.py`) — Factor vectors are compared using IDF-weighted cosine similarity. A second signal from the `all-MiniLM-L6-v2` sentence-transformer captures semantic similarity between case explanations. Final score = 70% factor structure + 30% text similarity.

4. **Evaluation** (`src/main.py`) — Runs offline against the labeled dataset, computing accuracy, stability, truncation robustness, and noise robustness for each case.

---

## Evaluation Results

Benchmarked against 21 human-labeled New York opinions. The dataset contains two types of cases: 13 synthetic simplified excerpts and 8 real appellate opinions. Overall Top-1 accuracy was 86% (18/21 labeled). On real appellate opinions specifically, the model correctly identified the dominant factor in 5 of 8 cases.

| Metric | Score |
|---|---|
| Top-1 Accuracy | 86% (18/21) |
| Stability (consistency across repeated runs) | 1.00 / 1.0 |
| Truncation Robustness | 0.78 / 1.0 |
| Noise Robustness | 0.81 / 1.0 |

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
│   │   ├── eval_cases/             # Synthetic evaluation excerpts (.txt)
│   │   ├── ny_real_snippets/       # Real appellate opinion excerpts (.txt)
│   │   └── demo_cases/             # Fresh cases for testing, not used in eval
│   └── eval/
│       ├── eval_log.jsonl          # Pre-computed evaluation records
│       ├── human_labels.csv        # Ground truth factor labels
│       └── run_history.jsonl       # Historical evaluation summaries
```
## Adding New Cases

Save the opinion text as a .txt file with a metadata header at the top:

JURISDICTION: New York
COURT: Court of Appeals
YEAR: 1985
JUDGE: Wachtler

Place the file in data/raw/eval_cases/ or data/raw/ny_real_snippets/
Add a row to data/eval/human_labels.csv with the dominant factor label
Run python3 -m src.main to regenerate eval_log.jsonl
Push eval_log.jsonl and human_labels.csv — the deployed app immediately searches the expanded dataset
---

## Limitations

- **Dataset size:** 21 cases covering 11 of 16 statutory factors. Results are descriptive, not statistically generalizable.
- **Single annotator:** Ground truth labels were created by one annotator. Inter-annotator agreement is a planned next step in collaboration with a family law professor.
- **Single jurisdiction:** New York only.
- **Descriptive, not predictive:** The system identifies reasoning patterns in past opinions. It does not predict outcomes.





