
import streamlit as st
import json
import csv
from collections import Counter, defaultdict
from src.extract_factors import extract_factors_llm, FACTOR_SCHEMA
from src.main import extract_metadata
from src.factor_explanations import FACTOR_EXPLANATIONS
from src.user_similarity import analyze_user_case

st.set_page_config(
    page_title="Equitable Distribution Analyzer",
    layout="wide"
)
st.markdown(
    """
    <style>
    div[data-testid="stVerticalBlock"] > div:has(div.stContainer) {
        padding: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)



st.markdown("""
<style>

/* ── Base ── */
.stApp {
    background-color: #f5f7fa;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

.block-container {
    padding-top: 2.5rem;
    max-width: 1100px;
}

/* ── Typography ── */
h1, h2, h3 {
    color: #0d2340 !important;
    font-weight: 700;
    letter-spacing: -0.02em;
}

p, li, .stMarkdown {
    color: #374151;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e5e9f0;
}

section[data-testid="stSidebar"] * {
    color: #0d2340 !important;
}

/* ── Cards (st.container with border) ── */
div[data-testid="stContainer"] {
    background-color: #ffffff;
    border: 1px solid #dde3ed;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* ── Case cards (raw HTML) ── */
.case-card {
    padding: 18px 20px;
    border-radius: 10px;
    border: 1px solid #dde3ed;
    background: #ffffff;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    color: #0d2340;
    line-height: 1.6;
}

/* ── Metric cards ── */
.metric-card {
    background-color: #ffffff;
    padding: 18px;
    border-radius: 10px;
    border: 1px solid #dde3ed;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* ── Buttons ── */
div.stButton > button {
    background-color: #0d2340;
    color: #ffffff !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.45rem 1.2rem;
    transition: background 0.2s ease;
}

div.stButton > button * {
    color: #ffffff !important;
}

div.stButton > button:hover {
    background-color: #163a6b;
    color: #ffffff !important;
}

div.stButton > button:hover * {
    color: #ffffff !important;
}

/* ── Dividers ── */
hr {
    border-color: #e5e9f0;
}

/* ── Info boxes ── */
div[data-testid="stAlert"] {
    background-color: #eef3fb;
    border: 1px solid #c5d5ef;
    border-radius: 8px;
    color: #0d2340;
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
    color: #6b7280;
    font-weight: 500;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #0d2340;
    border-bottom: 2px solid #0d2340;
}

</style>
""", unsafe_allow_html=True)





# Initialize session state for page navigation
if "page" not in st.session_state:
    st.session_state.page = "Home"

page = st.sidebar.radio(
    "Navigation",
    [
        "Home",
        "Analyzer",
        "How the System Was Evaluated",
        "Evaluation Log",
        "Case Similarity"
    ],
    index=[
        "Home",
        "Analyzer",
        "How the System Was Evaluated",
        "Evaluation Log",
        "Case Similarity"
    ].index(st.session_state.page)
)

st.session_state.page = page

if st.session_state.page == "Home":

    st.title("⚖ Equitable Distribution Analyzer")

    st.write(
        "Analyze divorce opinions and identify how courts weigh statutory equitable-distribution factors."
    )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.subheader("🔎 Analyze Case")
            st.write(
                "Upload divorce opinions and extract the equitable-distribution factors the court relied on most heavily."
            )

            if st.button("Open Analyzer"):
                st.session_state.page= "Analyzer"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("🔗 Find Similar Cases")
            st.write(
                "Enter facts from your case and discover similar judicial decisions based on reasoning patterns."
            )

            if st.button("Find Cases"):
                st.session_state.page = "Case Similarity"
                st.rerun()

    with col3:
        with st.container(border=True):
            st.subheader("📊 Validation Dashboard")
            st.write(
                "Explore the model's evaluation results, including accuracy, robustness, and transparency metrics."
            )

            if st.button("View Evaluation"):
                st.session_state.page = "How the System Was Evaluated"
                st.rerun()

elif st.session_state.page == "Analyzer":
    

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

                    filename = file.name
                    text = file.read().decode("utf-8")

                    metadata = extract_metadata(text)
                    case_metadata.append(metadata)

                    factors = extract_factors_llm(text, use_cache=True)

                    all_results.append(factors)

                    st.markdown(f"### Case: {filename}")

                    st.write("**Confidence:**", factors["confidence"])
                    st.info(factors["explanation"])
                    st.divider()
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
            if counter:
                dominant_factor = counter.most_common(1)[0][0]

                if dominant_factor in FACTOR_EXPLANATIONS:

                    info = FACTOR_EXPLANATIONS[dominant_factor]

                    st.markdown("### ⚖️ Legal Basis")

                    st.markdown(f"""
            **Statute:** {info["statute"]}

            **Summary:** {info["summary"]}

            **Typical Court Reasoning:**  
            {info["typical_reasoning"]}
            """)

            st.caption(
                "Interpretation: A factor labeled 'Frequently decisive' appeared to drive the "
                "court’s reasoning in a majority of the analyzed cases. This summary is "
                "descriptive and does not predict outcomes in any individual case."
            )
# REFACTORED VALIDATION PAGE - Insert this into app.py to replace the "How the System Was Evaluated" section

elif st.session_state.page == "How the System Was Evaluated":

    st.title("📊 Model Validation Dashboard")
    
    # Quick context
    with st.expander("📋 About This Validation", expanded=True):
        st.markdown("""
        **What:** Evaluates model accuracy on identifying dominant equitable-distribution factors.
        
        **Dataset:** Real NY divorce opinions, manually labeled by legal experts (fixed evaluation set).
        
        **Method:** Compares model outputs against human-labeled ground truth.
        """)
    
    with st.expander("🧪 Evaluation Dimensions", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Accuracy Metrics:**")
            st.markdown("• Top-1 Accuracy\n• Top-3 Accuracy\n• Precision & Recall per Factor")
        with col2:
            st.markdown("**Robustness Tests:**")
            st.markdown("• Stability (repeated runs)\n• Confidence Calibration\n• Truncation Robustness")

    
    st.markdown("---")
    
    # Load data
    human_labels = {}
    try:
        with open("data/eval/human_labels.csv", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row["file"].strip().lower()
                human_labels[filename] = row["correct_factor"].strip().lower()
    except FileNotFoundError:
        st.warning("No human_labels.csv found.")
        st.stop()

    eval_records = []
    log_path = "data/eval/eval_log.jsonl"
    try:
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                eval_records.append(json.loads(line))
    
    except FileNotFoundError:
        st.warning("No evaluation log found.")
        st.stop()
    except json.JSONDecodeError:
        st.error("Evaluation log is corrupted.")
        st.stop()
    
   
    correct_top1 = 0
    correct_top3 = 0
    total = 0

    confidence_counter = Counter()
    factor_counter = Counter()
    confidence_correct = Counter()
    confidence_total = Counter()

    true_positive = defaultdict(int)
    false_positive = defaultdict(int)
    false_negative = defaultdict(int)
    error_cases = []

   
    for rec in eval_records:
        file = rec["file"].strip().lower()
        model = rec.get("most_weighted", [])
        confidence = rec.get("confidence", "unknown")

        confidence_counter[confidence] += 1
        for f in model:
            factor_counter[f] += 1

        if file not in human_labels:
            st.warning(f"Missing human label for: {file}")
            continue

        total += 1

        human = human_labels[file]

        # ---- NORMALIZE STRINGS (CRITICAL FIX) ----
        human_clean = human.strip().lower()
        model_clean = [m.strip().lower() for m in model]

        # ---- TOP 1 ----
        top1_correct = len(model_clean) > 0 and model_clean[0] == human_clean
        if top1_correct:
            correct_top1 += 1

        # ---- TOP 3 ----
        top3_correct = human_clean in model_clean
        if top3_correct:
            correct_top3 += 1

        confidence_total[confidence] += 1
        if top1_correct:
            confidence_correct[confidence] += 1

        if not top1_correct:
            error_cases.append({
                "file": file,
                "model": ", ".join(model_clean) if model_clean else "None",
                "human": human_clean,
                "confidence": confidence
            })

        # ---- Precision / Recall tracking ----
        for factor in model_clean:
            if factor == human_clean:
                true_positive[factor] += 1
            else:
                false_positive[factor] += 1

        if human_clean not in model_clean:
            false_negative[human_clean] += 1


    # ---- FINAL ACCURACY ----
    top1_accuracy = correct_top1 / total if total else 0
    top3_accuracy = correct_top3 / total if total else 0
    if total == 0:
        st.error("No matching files between eval_log and human_labels.csv")
        st.stop()

    

    # Display top metrics
    st.subheader("📈 Overall Performance")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Top-1 Accuracy", f"{top1_accuracy:.0%}")
        st.metric("Top-3 Accuracy", f"{top3_accuracy:.0%}")
    with col2:
        st.metric("Cases Evaluated", total)
    with col3:
        unique_cases = len(set(rec["file"] for rec in eval_records))
        st.metric("Total Logged", unique_cases)

    # Tabbed results
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Factor Analysis", "🔴 Errors", "📋 All Cases", "👨‍⚖️ Judges"])

    with tab1:
        st.subheader("Precision & Recall by Factor")
        all_factors = set(list(true_positive.keys()) + list(false_negative.keys()))
        
        if all_factors:
            factor_rows = []
            for factor in sorted(all_factors):
                tp = true_positive[factor]
                fp = false_positive[factor]
                fn = false_negative[factor]
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                factor_rows.append({
                    "Factor": factor.replace("_", " ").title(),
                    "Precision": f"{precision:.0%}",
                    "Recall": f"{recall:.0%}",
                    "Correct Predictions": tp
                })
            st.dataframe(factor_rows, use_container_width=True)

    with tab2:
        st.subheader("Error Analysis")
        if not error_cases:
            st.success("✅ No errors — model matched all labeled cases!")
        else:
            st.warning(f"⚠️ {len(error_cases)} case(s) misclassified:")
            st.dataframe(error_cases, use_container_width=True)
        
        

    with tab3:
        st.subheader("All Evaluation Cases")
        table_rows = []
        for rec in eval_records:
            table_rows.append({
                "File": rec.get("file"),
                "Top Factor": (rec.get("top_factor", "—") or "—").replace("_", " ").title(),
                "Confidence": rec.get("confidence", "—"),
                "Stability": f"{rec.get('stability', 0):.2f}",
            })
        st.dataframe(table_rows, use_container_width=True)

    with tab4:
        st.subheader("Judge-Level Patterns")
        judge_factor_counter = defaultdict(Counter)
        judge_case_count = Counter()

        for rec in eval_records:
            judge = rec.get("metadata", {}).get("JUDGE", "Unknown")
            factors = rec.get("most_weighted", [])
            judge_case_count[judge] += 1
            for f in factors:
                judge_factor_counter[judge][f] += 1

        for judge in sorted(judge_case_count.keys()):
            with st.expander(f"👨‍⚖️ {judge}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cases", judge_case_count[judge])
                    st.markdown("**Top Factors:**")
                    if judge_factor_counter[judge]:
                        for factor, count in judge_factor_counter[judge].most_common(3):
                            freq = count / judge_case_count[judge]
                            st.caption(f"• {factor.replace('_', ' ')}: {freq:.0%}")
                with col2:
                    st.markdown("**Factor Appearance Count:**")
                    if judge_factor_counter[judge]:
                        for factor, count in judge_factor_counter[judge].most_common(3):
                            st.caption(f"• {factor.replace('_', ' ')}: {count} appearance(s)")

    st.divider()
    st.subheader("🛡️ Robustness Metrics")
    st.markdown("### Confidence Calibration")

    rows = []
    for level in confidence_total:
        total_c = confidence_total[level]
        correct_c = confidence_correct[level]
        acc_c = correct_c / total_c if total_c else 0

        rows.append({
            "Confidence Level": level,
            "Accuracy": f"{acc_c:.0%}",
            "Cases": total_c
        })

    st.dataframe(rows, use_container_width=True)
    st.caption(
    "Confidence levels reflect the model's self-assessed certainty in identifying the dominant statutory factor."
    )
    
    stability_scores = []
    truncation_scores = []
    noise_scores = []
    for rec in eval_records:
        if "stability" in rec:
            stability_scores.append(rec["stability"])
        if "truncation_robustness" in rec:
            truncation_scores.append(rec["truncation_robustness"])
        if "noise_robustness" in rec:
            noise_scores.append(rec["noise_robustness"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if stability_scores:
            avg_stability = sum(stability_scores) / len(stability_scores)
            st.metric("Consistency Across Runs", f"{avg_stability:.2f}/1.0")
            st.caption("Same top factor predicted across repeated runs on the same case.")
    with col2:
        if truncation_scores:
            avg_trunc = sum(truncation_scores) / len(truncation_scores)
            st.metric("Truncation Robustness", f"{avg_trunc:.2f}/1.0")
            st.caption("Top factor consistent when only first half, second half, or middle of the opinion is shown.")
    with col3:
        if noise_scores:
            avg_noise = sum(noise_scores) / len(noise_scores)
            st.metric("Noise Robustness", f"{avg_noise:.2f}/1.0")
            st.caption("Top factor consistent after punctuation removal and random sentence dropout.")
    with col4:
        total_robustness_cases = len(set(
            rec["file"] for rec in eval_records
            if "truncation_robustness" in rec
        ))
        st.metric("Cases Tested", total_robustness_cases)
        st.caption("Number of unique opinions used in robustness evaluation.")

    st.info("💡 **Note:** This dashboard reflects a fixed evaluation dataset. The Analyzer processes your uploaded files.")


elif st.session_state.page == "Evaluation Log":

    st.title("📋 Raw Evaluation Log")

    with st.expander("ℹ️ About This Log", expanded=False):
        st.markdown("""
        **Raw model evaluation records** used to compute all validation metrics.
        
        Each row is one judicial opinion containing:
        - Detected factors and confidence level
        - Stability and robustness scores
        - Model's explanation
        - Case metadata (court, judge, year)
        
        This provides complete transparency into system evaluation.
        """)
    

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
        st.error("❌ No evaluation log found.")
        st.stop()

    if not records:
        st.warning("⚠️ Evaluation log is empty.")
        st.stop()

    # Create filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        show_mode = st.radio("Display Mode:", ["Summary Table", "Detailed View"], horizontal=True)
    
    if show_mode == "Summary Table":
        # Flatten for display
        table = []
        for r in records:
            table.append({
                "File": r.get("file"),
                "Judge": r.get("metadata", {}).get("JUDGE") or "—",
                "Court": r.get("metadata", {}).get("COURT") or "—",
                "Year": r.get("metadata", {}).get("YEAR") or "—",
                "Top Factor": (r.get("top_factor") or "—").replace("_", " ").title(),
                "Confidence": r.get("confidence", "—"),
                "Stability": f"{r.get('stability', 0):.2f}",
                "Robustness": f"{r.get('truncation_robustness', 0):.2f}",
            })

        st.dataframe(table, use_container_width=True, height=400)
        
        st.caption(f"📊 Total records: {len(records)}")
    
    else:  # Detailed View
        for idx, r in enumerate(records, 1):
            with st.expander(f"Case {idx}: {r.get('file')}", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Judge", r.get("metadata", {}).get("JUDGE") or "—")
                with col2:
                    st.metric("Court", r.get("metadata", {}).get("COURT") or "—")
                with col3:
                    st.metric("Year", r.get("metadata", {}).get("YEAR") or "—")
                with col4:
                    st.metric("Confidence", r.get("confidence", "—"))
                
                st.divider()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Top Factor:**")
                    st.code(r.get("top_factor") or "None", language="text")
                    st.markdown("**All Weighted Factors:**")
                    factors = r.get("most_weighted", [])
                    if factors:
                        for f in factors:
                            st.caption(f"• {f.replace('_', ' ')}")
                    else:
                        st.caption("None detected")
                
                with col2:
                    st.markdown("**Robustness Scores:**")
                    st.caption(f"Stability: {r.get('stability', 0):.2f}")
                    st.caption(f"Truncation Robustness: {r.get('truncation_robustness', 0):.2f}")
                    st.caption(f"Noise Robustness: {r.get('noise_robustness', 0):.2f}")
                
                st.divider()
                st.markdown("**Model Explanation:**")
                st.info(r.get("explanation", "No explanation provided."))



elif st.session_state.page == "Case Similarity":
    st.title("⚖️ Find Similar Cases")

    with st.expander("ℹ️ How This Works", expanded=False):
        st.markdown("""
        Enter your case facts or summary. The system will:
        1. Extract key equitable-distribution factors
        2. Compare against all evaluated cases
        3. Return the most structurally similar judicial decisions
        
        **Similarity** is based on shared legal reasoning patterns, not keyword matching.
        """)

    user_text = st.text_area("📝 Enter case facts or summary:", height=180, placeholder="The husband earned income while the wife supported his education...")

    if st.button("🔍 Find Similar Cases", use_container_width=True) and user_text.strip():

        #from src.vectorize import build_factor_vector
       # from src.similarity import find_most_similar_cases

        # --- Analyze user case ---
        with st.spinner("⏳ Analyzing case..."):
            user_result = analyze_user_case(user_text)

        result = user_result["analysis"]
        similar_cases = user_result["similar_cases"]
        # --- User Case Analysis ---
        st.divider()
        st.subheader("📊 Case Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            if result["most_weighted"]:
                st.metric(
                    "Primary Factor",
                    result["most_weighted"][0].replace("_"," ").title()
                )

        with col2:
            st.metric("Confidence", result["confidence"].title())

        with col3:
            st.metric("Factors Detected", len(result["most_weighted"]))

        st.divider()

        st.subheader("Model Explanation")

        st.info(result["explanation"])

        

        # --- Summary Statistics ---
        st.divider()
        st.subheader("🎯 Match Summary")
        
        scores = [c["score"] for c in similar_cases]
        if scores:
            avg_score = sum(scores) / len(scores)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Match", f"{avg_score*100:.0f}%")
            with col2:
                best_match = max(scores) * 100
                st.metric("Best Match", f"{best_match:.0f}%")
            with col3:
                top_factors = [c["top_factor"] for c in similar_cases if c["top_factor"]]
                if top_factors:
                    predicted = Counter(top_factors).most_common(1)[0][0]
                    st.metric("Common Factor", predicted.replace("_", " ").title())

        # --- Similar Cases ---
        st.divider()
        st.subheader("📚 Most Similar Cases")
        
        if not similar_cases:
            st.warning("❌ No similar cases found.")
        else:
            for s in similar_cases:

                score = float(s["score"]) if s["score"] else 0.0
                pct = round(score * 100)

                case_title = s["file"].replace(".txt","").replace("_"," ").title()

                judge = s.get("judge","Unknown")
                court = s.get("metadata",{}).get("COURT","—")
                year = s.get("metadata",{}).get("YEAR","—")

                top_factor = (
                    s["top_factor"].replace("_"," ").title()
                    if s.get("top_factor")
                    else "Unknown"
                )

                st.markdown(
                    f"""
                    <div class="case-card">
                    <b>{case_title}</b><br>
                    Judge: {judge} | Court: {court} | Year: {year}<br>
                    Dominant Factor: {top_factor}<br>
                    Match Score: <b>{pct}%</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.progress(score)

        # --- Summary recommendation ---
        st.divider()
        st.subheader("💡 Summary")
        
        if result["most_weighted"]:
            readable = [f.replace("_", " ").title() for f in result["most_weighted"]]
            summary_text = f"Your case emphasizes **{', '.join(readable)}**. Similar cases demonstrate how courts weigh these factors in comparable situations."
        else:
            summary_text = "Unable to identify primary factors. Try entering more specific case details."
        
        st.info(summary_text)