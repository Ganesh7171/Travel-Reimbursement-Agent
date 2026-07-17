# Travel Reimbursement Approval Agent

This project contains an AI agent that automatically evaluates employee travel reimbursement claims against corporate policy using the Google Gemini API (function-calling/tools).

## Delivery Formats
This project includes two ways to run the agent:
1. **Jupyter Notebook**: `TravelReimbursementAgent.ipynb` - a single, self-contained notebook to run all claims and generate a visual dashboard.
2. **Streamlit App (Standalone Project)**: `app.py` - an interactive web UI.

---

## 🚀 Running the Streamlit Web App

### Prerequisites
Make sure you have Python 3.10+ installed.

### Setup
1. Open a terminal in this project folder (`c:\Users\balag\Downloads\Travel Reimbursement Agent`).
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```
4. A web browser will open automatically at `http://localhost:8501`.
5. Enter your Google AI Studio API Key in the left sidebar to start evaluating claims.

---

## 📓 Running the Jupyter Notebook
1. Start Jupyter Notebook/Lab in this folder.
2. Open `TravelReimbursementAgent.ipynb`.
3. Provide your API Key in Cell 3 when prompted.
4. Click **Restart & Run All** to process all 5 sample claims automatically.
5. The notebook will produce a structured JSON array and save a visual dashboard as `UI SS_1.png`.

---

## Architecture Overview
*   **Agentic loop (`agent.py`)**: The agent uses a `while` loop, allowing Gemini to repeatedly decide which tools to call until it reaches a final decision (APPROVE, PARTIAL_APPROVE, REJECT, or MANUAL_REVIEW).
*   **Policy Rules (`policy.py`)**: All math, threshold checking, and policy definitions are strictly enforced in deterministic Python code, exposed as tools to the LLM to eliminate hallucinations.
*   **Zero hallucinated data**: The system evaluates only the exact 5 claims from the provided Appendix B.
