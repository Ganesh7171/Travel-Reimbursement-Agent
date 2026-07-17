import streamlit as st
import json
import pandas as pd
import PyPDF2
from io import BytesIO
from agent import process_claim_generator, initialize_vector_store
from policy import CLAIMS, POLICY_RULES

st.set_page_config(page_title="Travel Agent UI", page_icon="🧳", layout="centered")

st.title("🧳 Travel Reimbursement Agent")
st.markdown("Evaluate employee travel claims dynamically using RAG (Vector Database) and Google Gemini.")

# --- 1. Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Google AI Studio API Key", type="password", help="Get a key from https://aistudio.google.com/app/apikey")
    
    st.divider()
    st.header("📄 1. Load Policy (RAG)")
    policy_file = st.file_uploader("Upload Corporate Policy (TXT, PDF)", type=['txt', 'pdf'])
    
    policy_text = ""
    if policy_file:
        if policy_file.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(BytesIO(policy_file.read()))
            policy_text = "\\n\\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        else:
            policy_text = policy_file.getvalue().decode("utf-8")
        st.success(f"Extracted {len(policy_text)} characters.")
    else:
        st.info("No policy uploaded. Using default strict policy.")
        # Fallback to the original policy string representation
        policy_text = "\\n\\n".join([f"{k}: {v}" for k, v in POLICY_RULES.items()])
        
    if api_key and policy_text:
        if st.button("Initialize Knowledge Base", type="primary"):
            with st.spinner("Embedding policy into Vector DB..."):
                try:
                    num_chunks = initialize_vector_store(api_key, policy_text)
                    st.success(f"Database initialized with {num_chunks} chunks!")
                    st.session_state['db_ready'] = True
                except Exception as e:
                    st.error(f"Failed to embed policy: {e}")

# --- 2. Main Area: Input ---
st.header("📝 2. Claim Input")
st.markdown("Switch between the Interactive Form or raw JSON Editor.")

tab_form, tab_json = st.tabs(["Interactive Form", "JSON Editor"])

# Select a sample to pre-fill
sample_claim_options = {f"{c['claim_id']} - {c['purpose']}": c for c in CLAIMS}
selected_sample = st.selectbox("Pre-fill with a sample claim:", list(sample_claim_options.keys()))
default_claim = sample_claim_options[selected_sample]

# --- TAB 1: FORM ---
with tab_form:
    col_a, col_b = st.columns(2)
    with col_a:
        f_emp = st.text_input("Employee Name", value=default_claim['employee'])
        f_purp = st.text_input("Purpose", value=default_claim['purpose'])
    with col_b:
        f_start = st.text_input("Trip Start (YYYY-MM-DD)", value=default_claim['trip_start'])
        f_end = st.text_input("Trip End (YYYY-MM-DD)", value=default_claim['trip_end'])
    
    f_sub = st.text_input("Submission Date", value=default_claim['submission_date'])
    f_total = st.number_input("Total Claimed ($)", value=float(default_claim['total_claimed']))
    
    st.markdown("#### Line Items")
    # Convert default line items to DataFrame for the data editor
    if 'line_items_df' not in st.session_state or st.session_state.get('last_sample') != selected_sample:
        st.session_state['line_items_df'] = pd.DataFrame(default_claim['line_items'])
        st.session_state['last_sample'] = selected_sample
    
    # Ensure all required columns exist in the dataframe
    for col in ['category', 'description', 'amount', 'receipt_attached', 'days', 'is_business_class']:
        if col not in st.session_state['line_items_df'].columns:
            st.session_state['line_items_df'][col] = None
            
    edited_df = st.data_editor(
        st.session_state['line_items_df'], 
        num_rows="dynamic",
        column_config={
            "category": st.column_config.SelectboxColumn("Category", options=["airfare", "lodging", "meals", "ground_transport", "conference_fees", "spa", "minibar"]),
            "amount": st.column_config.NumberColumn("Amount ($)"),
            "receipt_attached": st.column_config.CheckboxColumn("Receipt?"),
            "is_business_class": st.column_config.CheckboxColumn("Business Class?"),
            "days": st.column_config.NumberColumn("Days")
        },
        use_container_width=True
    )
    
    # Reconstruct the claim dict from the form
    form_claim_dict = {
        "claim_id": default_claim['claim_id'],
        "employee": f_emp,
        "purpose": f_purp,
        "trip_start": f_start,
        "trip_end": f_end,
        "submission_date": f_sub,
        "total_claimed": f_total,
        "line_items": edited_df.dropna(how='all').to_dict('records') # Drop empty rows
    }
    
    # Clean up NaN values from the pandas conversion back to dict
    for item in form_claim_dict['line_items']:
        for k, v in list(item.items()):
            if pd.isna(v):
                del item[k]

# --- TAB 2: JSON ---
with tab_json:
    st.info("Editing this JSON will override the form above when executing.")
    json_str = st.text_area("JSON Editor", value=json.dumps(form_claim_dict, indent=2), height=400)
    try:
        final_claim_to_run = json.loads(json_str)
    except json.JSONDecodeError:
        st.error("Invalid JSON format.")
        final_claim_to_run = None

st.divider()

# --- 3. Main Area: Execution & Results (Vertical Layout) ---
st.header("🚀 3. Execution & Results")

is_ready = bool(api_key) and st.session_state.get('db_ready', False) and final_claim_to_run is not None
if not is_ready:
    st.warning("Please provide an API Key and click 'Initialize Knowledge Base' in the sidebar.")
    
run_button = st.button("Evaluate Claim", type="primary", disabled=not is_ready, use_container_width=True)

if run_button:
    status_placeholder = st.empty()
    log_expander = st.expander("🛠️ RAG Agent Reasoning Logs", expanded=True)
    
    final_result = None
    
    with st.spinner("Agent is searching policy and reasoning..."):
        for step in process_claim_generator(final_claim_to_run, api_key):
            if step["type"] == "info":
                status_placeholder.info(step["message"])
            elif step["type"] == "tool_call":
                log_expander.markdown(f"**Executing Search:** `{step['tool']}`\n```json\n{json.dumps(step['args'], indent=2)}\n```")
            elif step["type"] == "tool_result":
                log_expander.markdown(f"**Retrieved Policy Chunks:**\n```json\n{json.dumps(step['result'], indent=2)}\n```")
                log_expander.divider()
            elif step["type"] == "error":
                st.error(step["message"])
            elif step["type"] == "result":
                final_result = step["data"]
                status_placeholder.empty()
    
    if final_result:
        decision = final_result.get("decision", "UNKNOWN")
        
        st.success("Agent evaluation complete!")
        
        metric_cols = st.columns(3)
        metric_cols[0].metric("Decision", decision)
        metric_cols[1].metric("Approved Amount", f"${final_result.get('approved_amount', 0):.2f}")
        metric_cols[2].metric("Deducted Amount", f"${final_result.get('deducted_amount', 0):.2f}")
        
        st.markdown("### Decision Explanation")
        st.info(final_result.get("explanation", "No explanation provided."))
        
        st.markdown("### Structured Output")
        st.json(final_result)
