
import streamlit as st
from collections import Counter
from src.extract_factors import extract_factors_llm, FACTOR_SCHEMA
from src.main import extract_metadata  # reuse your existing function
import json
from collections import defaultdict

page = st.sidebar.radio(
    "Navigation",
    ["Analyzer", "How the System Was Evaluated"]
)

if page == "Analyzer":
    st.set_page_config(page_title="Equitable Distribution Analyzer")

    st.title("Equitable Distribution Jurisdiction Analyzer")

    st.write(
        "Upload multiple divorce opinions or case excerpts to see which "
        "New York equitable-distribution factors courts tend to emphasize."
    )

    uploaded_files = st.file_uploader(
        "Upload case text files (.txt)",
        type="txt",
        accept_multiple_files=True
    )

    if st.button("Analyze"):
        if not uploaded_files:
            st.warning("Please upload at least one case file.")
        else:
            all_results = []
            case_metadata = []

            with st.spinner("Analyzing cases..."):
                for file in uploaded_files:
                    text = file.read().decode("utf-8")
                    metadata = extract_metadata(text)
                    case_metadata.append(metadata)

                    factors = extract_factors_llm(text)
                    st.write("Confidence:", factors["confidence"])

                    
                    all_results.append(factors)

            
            counter = Counter()
            for result in all_results:
                for factor in result["most_weighted"]:
                    counter[factor] += 1

            

        
            st.subheader("Equitable Distribution Analysis Summary")

            st.write(
                "This analysis reviews the uploaded divorce opinions and identifies which "
                "statutory equitable-distribution factors the court appears to rely on most "
                "heavily in reaching its decision. The results reflect dominant judicial "
                "reasoning, not merely whether a factor was mentioned."
            )

            # ---- Context Summary ----
            jurisdictions = {m.get("JURISDICTION") for m in case_metadata if "JURISDICTION" in m}
            courts = {m.get("COURT") for m in case_metadata if "COURT" in m}
            years = sorted(int(m["YEAR"]) for m in case_metadata if "YEAR" in m)

            st.markdown("**Case Context**")
            st.write(f"Jurisdiction analyzed: {', '.join(jurisdictions)}")
            st.write(f"Courts represented: {', '.join(courts)}")

            if years:
                st.write(f"Years covered: {years[0]}–{years[-1]}")

            st.write(f"Number of cases analyzed: {len(case_metadata)}")

            # ---- Factor Summary ----
            st.markdown("**Factor Emphasis (Dominant Judicial Reasoning)**")

            if not counter:
                st.write("No dominant factors were detected in the analyzed cases.")
            else:
                for factor, count in counter.most_common():
                    freq = count / len(all_results)

                    if freq >= 0.6:
                        label = "Frequently decisive"
                    elif freq >= 0.3:
                        label = "Sometimes decisive"
                    else:
                        label = "Rarely decisive"

                    readable = factor.replace("_", " ")

                    st.write(
                        f"{label}: {readable} "
                        f"(primary factor in {count} of {len(all_results)} cases, {freq:.0%})"
                    )

            st.caption(
                "Interpretation: A factor labeled 'Frequently decisive' appeared to drive the "
                "court’s reasoning in a majority of the analyzed cases. This summary is "
                "descriptive and does not predict outcomes in any individual case."
            )
elif page == "How the System Was Evaluated":

    st.title("Model Validation Dashboard")
    st.markdown("""
        **About This Validation Dashboard**

        This dashboard evaluates how well the system identifies the *dominant equitable-distribution factor* in judicial opinions.

        The results shown here are based on a fixed evaluation dataset — not the files uploaded in the Analyzer. The dataset consists of real New York divorce opinions that were manually reviewed and labeled by a human using legal judgment.

        For each case, the model’s detected dominant factor is compared against the human-labeled ground truth. Accuracy therefore reflects how closely the system matches human legal reasoning.

        Why this matters:

        - It verifies the system is **tested, not just demonstrated**
        - It measures whether the model captures **true judicial reasoning**
        - It helps identify where the system is reliable vs uncertain
        - It provides transparency for lawyers using the tool

        This validation ensures the system is grounded in real legal analysis rather than simple keyword detection.
        """)


    import csv
    from collections import Counter

    # ----------------------------
    # Load human labels
    # ----------------------------
    human_labels = {}
    try:
        with open("data/eval/human_labels.csv", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                human_labels[row["file"]] = row["correct_factor"]
    except FileNotFoundError:
        st.warning("No human_labels.csv found.")
        st.stop()

    # ----------------------------
    # Load model evaluation log
    # ----------------------------
    eval_records = []
    log_path = "data/eval/eval_log.jsonl"

    try:
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue   # skip blank lines
                eval_records.append(json.loads(line))
    except FileNotFoundError:
        st.warning("No evaluation log found.")
        st.stop()
    except json.JSONDecodeError:
        st.error("Evaluation log is corrupted or improperly formatted.")
        st.stop()

    # ----------------------------
    # Compute accuracy
    # ----------------------------
    correct = 0
    total = 0
    confidence_counter = Counter()
    factor_counter = Counter()
    # Precision / Recall counters
    true_positive = defaultdict(int)
    false_positive = defaultdict(int)
    false_negative = defaultdict(int)


    per_case_results = []
    error_cases = []


    for rec in eval_records:
        file = rec["file"]
        model = rec["most_weighted"]
        confidence = rec.get("confidence", "unknown")

        confidence_counter[confidence] += 1

        for f in model:
            factor_counter[f] += 1

        if file in human_labels:
            total += 1
            human = human_labels[file]
            is_correct = human in model
            
            if is_correct:
                correct += 1
            if not is_correct:
                error_cases.append({
                    "file": file,
                    "model": ", ".join(model) if model else "None",
                    "human": human,
                    "confidence": confidence
                })

            per_case_results.append({
                "file": file,
                "model": ", ".join(model) if model else "None",
                "human": human,
                "confidence": confidence,
                "correct": is_correct
            })
            # ---- Precision / Recall tracking ----
        for factor in model:
            if factor == human:
                true_positive[factor] += 1
            else:
                false_positive[factor] += 1

        if human not in model:
            false_negative[human] += 1


    accuracy = correct / total if total > 0 else 0

    # ----------------------------
    # Top Metrics
    # ----------------------------
    st.subheader("Overall Model Performance")

    col1, col2, col3 = st.columns(3)
    col1.metric("Accuracy", f"{accuracy:.0%}")
    col2.metric("Cases Evaluated", total)
    col3.metric("Total Logged Cases", len(eval_records))

    # ----------------------------
    # Precision / Recall
    # ----------------------------
    st.subheader("Precision & Recall by Factor")

    all_factors = set(list(true_positive.keys()) + list(false_negative.keys()))

    for factor in all_factors:
        tp = true_positive[factor]
        fp = false_positive[factor]
        fn = false_negative[factor]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        readable = factor.replace("_", " ")

        st.write(
            f"**{readable}** — Precision: {precision:.0%}, Recall: {recall:.0%}"
        )

    # ----------------------------
    # Error Analysis
    # ----------------------------
    st.subheader("Model Error Analysis")

    if not error_cases:
        st.write("No errors detected — model matched human labels for all evaluated cases.")
    else:
        st.write("The following cases were incorrectly classified by the model:")

        st.dataframe(error_cases)

        st.caption(
            "Error analysis helps identify where the model struggles and reveals patterns "
            "in misclassification. This is critical for improving reliability and understanding "
            "model limitations."
        )

    # ----------------------------
    # Confidence Distribution
    # ----------------------------
    st.subheader("Confidence Distribution")

    for k, v in confidence_counter.items():
        st.write(f"{k.capitalize()}: {v} cases")

    # ----------------------------
    # Dominant Factor Distribution
    # ----------------------------
    st.subheader("Dominant Factor Detection")

    for factor, count in factor_counter.most_common():
        readable = factor.replace("_", " ")
        st.write(f"{readable}: {count} cases")

    # ----------------------------
    # Per-Case Results Table
    # ----------------------------
    st.subheader("Per-Case Evaluation")

    st.dataframe(per_case_results)

    st.caption(
    "Note: The validation dashboard reflects performance on a fixed evaluation dataset. "
    "The Analyzer page processes only the files uploaded by the user."
    )

