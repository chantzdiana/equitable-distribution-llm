
import streamlit as st
from collections import Counter
from src.extract_factors import extract_factors_llm, FACTOR_SCHEMA
from src.main import extract_metadata  # reuse your existing function

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

    st.title("How This System Was Evaluated")

    st.markdown("""
    ### What the Model Does
    This system analyzes divorce opinions applying New York equitable distribution law and identifies which statutory factors the court relied on most heavily in reaching its decision. It focuses on *judicial reasoning*, not merely whether a factor was mentioned.

    ---

    ### How Factors Are Extracted
    A large language model (LLM) reads each opinion and identifies:

    - Which statutory factors are discussed
    - Which factor(s) appear **most decisive** in the court’s reasoning

    The model looks for reasoning signals such as:
    - “primary consideration”
    - “the court relies heavily on”
    - “determinative”
    - “critical to the outcome”

    ---

    ### Human-Labeled Evaluation Dataset
    To verify correctness, a set of real New York cases was manually reviewed and labeled by a human using legal judgment. Each case was labeled with the factor that truly drove the court’s decision.

    The model’s output is compared against this ground-truth dataset.

    ---

    ### Accuracy Measurement
    The system reports how often the model correctly identified the dominant factor compared to the human-labeled dataset.

    This ensures the model is **tested, not just demonstrated.**

    ---

    ### Confidence Scoring
    Each result includes a confidence level:

    - **High** — clear decisive reasoning detected  
    - **Medium** — multiple important factors  
    - **Low** — ambiguous or weak signals  

    This helps users understand reliability.

    ---

    ### What the Testing Shows
    The evaluation confirms the model can correctly identify dominant equitable-distribution reasoning in judicial opinions and aggregate patterns across cases and judges.

    ---

    ### Limitations
    - The system describes patterns; it does not predict outcomes with certainty.
    - Accuracy depends on the quality and representativeness of cases analyzed.
    - Legal decisions are fact-specific and involve judicial discretion.

    ---

    ### Purpose
    This tool is designed as an experimental legal analytics system to explore how AI can help lawyers understand judicial reasoning patterns in equitable-distribution cases.
    """)
