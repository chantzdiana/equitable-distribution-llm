
import streamlit as st
from collections import Counter
from src.extract_factors import extract_factors_llm, FACTOR_SCHEMA
from src.main import extract_metadata  # reuse your existing function
import json
from collections import defaultdict

page = st.sidebar.radio(
    "Navigation",
    ["Analyzer", "How the System Was Evaluated", "Evaluation Log", "Case Similarity"]
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
                    filename = file.name   # <-- get case name

                    text = file.read().decode("utf-8")
                    metadata = extract_metadata(text)
                    case_metadata.append(metadata)

                    factors = extract_factors_llm(text)

                    # ---- CASE HEADER ----
                    st.markdown(f"### Case: {filename}")

                    # Optional: show metadata if present
                    if metadata:
                        meta_parts = []
                        if "COURT" in metadata:
                            meta_parts.append(metadata["COURT"])
                        if "YEAR" in metadata:
                            meta_parts.append(metadata["YEAR"])
                        if "JUDGE" in metadata:
                            meta_parts.append(f"Judge {metadata['JUDGE']}")

                        if meta_parts:
                            st.caption(" • ".join(meta_parts))

                    # ---- MODEL OUTPUT ----
                    st.write("**Confidence:**", factors["confidence"])
                    st.write("**Explanation:**", factors["explanation"])

                    st.divider()   # visual separator between cases

            
                #

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
    st.markdown("""
    ### What Has This System Been Tested For?

    This model has undergone structured evaluation across multiple dimensions of reliability and legal reasoning:

    - **Top-1 Accuracy** — Agreement with human legal judgment on the primary decisive factor
    - **Top-3 Accuracy** — Whether the correct factor appears among the model’s top reasoning drivers
    - **Stability** — Consistency across repeated model runs
    - **Confidence Calibration** — How certainty correlates with correctness
    - **Truncation Robustness** — Whether reasoning survives partial opinions
    - **Noise Robustness** — Resistance to formatting and textual corruption
    - **Explainability** — Human-readable justification grounded in judicial reasoning
    - **Judge Analytics** — Detection of factor emphasis patterns across judges

    Together, these tests evaluate whether the system captures **true judicial reasoning**, not just keyword presence.
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

    confidence_correct = Counter()
    confidence_total = Counter()


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
            confidence_total[confidence] += 1
            if is_correct:
                confidence_correct[confidence] += 1
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
    # Confidence Reliability
    # ----------------------------
    st.subheader("Confidence Reliability")

    for level in confidence_total:
        total_c = confidence_total[level]
        correct_c = confidence_correct[level]

        accuracy_c = correct_c / total_c if total_c > 0 else 0

        st.write(
            f"**{level.capitalize()} confidence** — Accuracy: {accuracy_c:.0%} "
            f"({correct_c}/{total_c} correct)"
        )

    st.caption(
        "This section evaluates whether the model's confidence score correlates with accuracy. "
        "Ideally, higher confidence predictions should be more reliable."
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

    table_rows = []

    for rec in eval_records:
        row = {
            "File": rec.get("file"),
            "Top Factor": rec.get("top_factor"),
            "Confidence": rec.get("confidence"),
            "Stability": rec.get("stability"),
            "Explanation": rec.get("explanation", "")[:200]  # short preview
        }
        table_rows.append(row)

    st.dataframe(table_rows)




    st.subheader("Reliability vs Confidence")

    from collections import defaultdict

    confidence_correct = defaultdict(int)
    confidence_total = defaultdict(int)

    for rec in eval_records:
        file = rec["file"]
        conf = rec.get("confidence", "unknown")

        if file in human_labels:
            human = human_labels[file]
            model_top = rec.get("top_factor")

            confidence_total[conf] += 1

            if model_top == human:
                confidence_correct[conf] += 1

    # Display calibration
    for conf in sorted(confidence_total.keys()):
        total = confidence_total[conf]
        correct = confidence_correct[conf]

        if total > 0:
            acc = correct / total
            st.write(
                f"{conf.capitalize()} confidence — Accuracy: {acc:.0%} "
                f"({correct}/{total} correct)"
            )


    # =============================
    # Judge Analytics
    # =============================

    st.subheader("Judge-Level Decision Patterns")

    judge_factor_counter = defaultdict(Counter)
    judge_confidence_counter = defaultdict(Counter)
    judge_case_count = Counter()

    for rec in eval_records:
        judge = rec.get("metadata", {}).get("JUDGE", "Unknown")
        factors = rec.get("most_weighted", [])
        confidence = rec.get("confidence", "unknown")

        judge_case_count[judge] += 1
        judge_confidence_counter[judge][confidence] += 1

        for f in factors:
            judge_factor_counter[judge][f] += 1

    for judge in sorted(judge_case_count.keys()):
        st.markdown(f"### Judge: {judge}")

        total_cases = judge_case_count[judge]
        st.write(f"Cases analyzed: {total_cases}")

        # ---- Dominant Factors ----
        if judge_factor_counter[judge]:
            st.write("Most influential factors:")
            for factor, count in judge_factor_counter[judge].most_common():
                freq = count / total_cases
                readable = factor.replace("_", " ")
                st.write(f"- {readable} ({freq:.0%} of cases)")
        else:
            st.write("No dominant factor detected.")

        # ---- Confidence profile ----
        st.write("Confidence profile:")
        for conf, count in judge_confidence_counter[judge].items():
            freq = count / total_cases
            st.write(f"- {conf.capitalize()}: {freq:.0%}")

        st.write("---")



    # ----------------------------
    # Stability + Robustness Metrics
    # ----------------------------

    st.subheader("Model Reliability")
    st.caption(
    "Truncation robustness measures whether the model reaches the same legal conclusion when only part of an opinion is available."
    )

    stability_scores = []
    truncation_scores = []

    for rec in eval_records:
        if "stability" in rec:
            stability_scores.append(rec["stability"])
        if "truncation_robustness" in rec:
            truncation_scores.append(rec["truncation_robustness"])

    if stability_scores:
        avg_stability = sum(stability_scores) / len(stability_scores)
        st.metric("Average Stability", f"{avg_stability:.2f}")

    if truncation_scores:
        avg_trunc = sum(truncation_scores) / len(truncation_scores)
        st.metric("Truncation Robustness", f"{avg_trunc:.2f}")

    st.caption(
    "Note: The validation dashboard reflects performance on a fixed evaluation dataset. "
    "The Analyzer page processes only the files uploaded by the user."
    )


elif page == "Evaluation Log":

    st.title("Raw Evaluation Log")

    st.markdown("""
    This page shows the **raw model evaluation records** used to compute all validation metrics.

    Each row corresponds to one judicial opinion and contains:
    - Detected dominant factors
    - Confidence level
    - Stability score
    - Explanation generated by the model
    - Metadata (court, judge, year)

    This provides full transparency into how the system was evaluated.
    """)

    import json

    log_path = "data/eval/eval_log.jsonl"
    records = []

    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                records.append(rec)
    except FileNotFoundError:
        st.warning("No evaluation log found.")
        st.stop()

    if not records:
        st.warning("Evaluation log is empty.")
        st.stop()

    # Flatten for display
    table = []
    for r in records:
        table.append({
            "file": r.get("file"),
            "judge": r.get("metadata", {}).get("JUDGE"),
            "court": r.get("metadata", {}).get("COURT"),
            "year": r.get("metadata", {}).get("YEAR"),
            "top_factor": r.get("top_factor"),
            "most_weighted": ", ".join(r.get("most_weighted", [])),
            "confidence": r.get("confidence"),
            "stability": r.get("stability"),
            "explanation": r.get("explanation"),
        })

    st.dataframe(table, use_container_width=True)



elif page == "Case Similarity":
    st.title("Case Similarity Engine")

    st.markdown(
        "Paste a case description or facts below. The system will identify "
        "the most similar judicial decisions based on legal reasoning patterns."
    )

    user_text = st.text_area("Enter case facts or summary:", height=200)

    if st.button("Find Similar Cases") and user_text.strip():

        from src.extract_factors import extract_factors_llm
        from src.vectorize import build_factor_vector
        from src.similarity import find_most_similar_cases

        # --- Analyze user case ---
        result = extract_factors_llm(user_text)

        st.subheader("Detected Legal Reasoning")

        if result["most_weighted"]:
            st.write("Most Weighted Factors:")
            for f in result["most_weighted"]:
                st.markdown(f"- {f.replace('_', ' ')}")
        else:
            st.write("Most Weighted Factors: None detected")   
       
        st.write("Confidence:", result["confidence"])
        st.write("Explanation:", result["explanation"])

        # --- Build vector ---
        query_vector = build_factor_vector(
            result["mentioned"],
            result["most_weighted"]
        )

        # --- Find similar cases ---
        similar_cases = find_most_similar_cases(query_vector, top_k=5)

        st.subheader("Most Similar Judicial Decisions")

        for s in similar_cases:
            st.markdown(
                f"""
                **Case:** {s['file']}  
                **Judge:** {s['judge']}  
                **Similarity:** {s['score']:.2f}  
                **Dominant Factor:** {s['top_factor']}
                """
            )

