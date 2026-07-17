import json
from typing import Any
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from google import genai
from google.genai import types

# --- Gemini Embedding Function for ChromaDB ---
class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        
    def __call__(self, input: Documents) -> Embeddings:
        response = self.client.models.embed_content(
            model='gemini-embedding-001',
            contents=input,
        )
        # Handle single vs multiple inputs based on API response structure
        if isinstance(input, str):
             return [response.embeddings[0].values]
        return [e.values for e in response.embeddings]

# --- Vector Database Manager ---
class PolicyVectorStore:
    def __init__(self, api_key: str):
        self.chroma_client = chromadb.Client()
        self.embedding_fn = GeminiEmbeddingFunction(api_key)
        
        # Delete old collection if it exists to refresh the policy
        try:
            self.chroma_client.delete_collection("travel_policy")
        except Exception:
            pass
            
        self.collection = self.chroma_client.create_collection(
            name="travel_policy",
            embedding_function=self.embedding_fn
        )

    def load_document(self, text: str):
        """Simple chunking by paragraphs/newlines for the policy document."""
        chunks = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 10]
        if not chunks:
            chunks = [text[i:i+500] for i in range(0, len(text), 500)] # Fallback character chunking
            
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        self.collection.add(
            documents=chunks,
            ids=ids
        )
        return len(chunks)

    def search(self, query: str, n_results: int = 3) -> list[str]:
        if self.collection.count() == 0:
            return ["No policy document loaded in the database."]
            
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results['documents'][0] if results['documents'] else []

# Global store reference (to be initialized by UI)
global_vector_store: PolicyVectorStore | None = None

# --- Gemini Tool: Search Policy ---
def search_policy_database(query: str) -> dict:
    """Searches the vector database for relevant policy clauses."""
    if not global_vector_store:
        return {'error': 'Vector store not initialized. No policy uploaded.'}
    try:
        results = global_vector_store.search(query, n_results=4)
        return {
            'query': query,
            'found_clauses': results
        }
    except Exception as e:
        return {'error': str(e)}

TOOL_REGISTRY = {
    'search_policy_database': search_policy_database,
}

GEMINI_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name='search_policy_database',
            description='Searches the uploaded corporate travel policy document for rules, limits, or guidelines based on a semantic query (e.g., "What is the per-diem limit for meals?", "Are business class flights allowed?", "Receipt requirements").',
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'query': types.Schema(type=types.Type.STRING, description='The question or topic to search for in the policy.')
                },
                required=['query']
            )
        )
    ])
]

SYSTEM_PROMPT = """\
You are an advanced Travel Reimbursement Approval Agent. Your task is to evaluate employee travel expense claims dynamically against the company's uploaded policy document.

## Core Instructions
1. You DO NOT have hardcoded policy limits. You must use the `search_policy_database` tool to discover the specific rules, per-diem limits, receipt requirements, and approval thresholds applicable to the claim you are evaluating.
2. For EVERY expense category in the claim (e.g., meals, lodging, airfare), search the policy database to verify if it is eligible and what limits apply.
3. Search for receipt requirements and timeliness rules.
4. Calculate any necessary deductions mathematically based on the limits you discover.
5. Make a final decision based on your findings.

## Decision Rules
- APPROVE: All items eligible, all receipts present (if required by policy), within per-diem limits, and within your approval authority.
- PARTIAL_APPROVE: Valid claim but some amounts exceed per-diem caps; reimburse up to the cap, deduct the excess.
- REJECT: All claimed items are explicitly ineligible per the policy.
- MANUAL_REVIEW: Any ambiguity, policy exception, missing receipt (if required by policy), or if the total amount exceeds the auto-approval or manager-approval thresholds defined in the policy. 
- *Note: If a policy rule says an item requires "pre-approval" or "manager approval" but you cannot verify it, route to MANUAL_REVIEW.*

## Output Format
After using the search tool as many times as needed to gather all rules, respond ONLY with a JSON object (no markdown fences, no extra text):
{
  "claim_id": "CLM-XXX",
  "decision": "APPROVE|PARTIAL_APPROVE|REJECT|MANUAL_REVIEW",
  "approved_amount": 0.0,
  "deducted_amount": 0.0,
  "missing_docs": [],
  "policy_refs": ["Quote short snippets of the relevant rules you found"],
  "confidence": 0.95,
  "explanation": "Provide a detailed explanation of your math and reasoning based on the policy clauses you retrieved.",
  "tools_used": ["search_policy_database"]
}
"""

def execute_tool(tool_name: str, tool_args: dict) -> Any:
    if tool_name not in TOOL_REGISTRY:
        return {'error': f'Tool "{tool_name}" not found.'}
    try:
        return TOOL_REGISTRY[tool_name](**tool_args)
    except Exception as e:
        return {'error': str(e), 'tool': tool_name, 'args': tool_args}

def initialize_vector_store(api_key: str, policy_text: str) -> int:
    global global_vector_store
    global_vector_store = PolicyVectorStore(api_key)
    return global_vector_store.load_document(policy_text)

def process_claim_generator(claim: dict, api_key: str):
    """Generator version of process_claim for streaming UI updates."""
    client = genai.Client(api_key=api_key)
    MODEL_NAME = 'gemini-3.1-flash-lite'
    claim_id = claim.get('claim_id', 'UNKNOWN')
    
    yield {"type": "info", "message": f"Processing claim {claim_id}: {claim.get('purpose', '')}"}

    user_message = f"""Evaluate this travel reimbursement claim and produce a decision.
Claim JSON:
{json.dumps(claim, indent=2)}

Steps:
1. Search the policy database for rules concerning every category in the claim.
2. Search for overall claim rules (receipts, time limits, approval thresholds).
3. Apply the rules mathematically.
4. Produce the final JSON decision object.
"""
    conversation_history = [types.Content(role='user', parts=[types.Part(text=user_message)])]
    tools_used = set()
    turn = 0
    max_turns = 12 # Give it a bit more turns for RAG searching

    while turn < max_turns:
        turn += 1
        yield {"type": "info", "message": f"Turn {turn}: Reasoning and Searching..."}
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=conversation_history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=GEMINI_TOOLS,
                temperature=0.1,
            )
        )
        
        conversation_history.append(response.candidates[0].content)
        
        function_calls = [part for part in response.candidates[0].content.parts if hasattr(part, 'function_call') and part.function_call is not None]
        
        if not function_calls:
            text = ''.join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text') and part.text)
            try:
                clean = text.strip()
                if clean.startswith('```'):
                    clean = clean.split('```')[1]
                    if clean.startswith('json'): clean = clean[4:]
                result = json.loads(clean.strip())
                result['tools_used'] = sorted(tools_used)
                yield {"type": "result", "data": result}
                return
            except json.JSONDecodeError as e:
                yield {"type": "error", "message": f"JSON parse error: {e}"}
                yield {"type": "result", "data": {
                    'claim_id': claim_id, 'decision': 'MANUAL_REVIEW',
                    'approved_amount': 0.0, 'deducted_amount': 0.0,
                    'missing_docs': [], 'policy_refs': [], 'confidence': 0.0,
                    'explanation': f'Agent output could not be parsed: {e}',
                    'tools_used': sorted(tools_used),
                }}
                return

        tool_response_parts = []
        for part in function_calls:
            fc = part.function_call
            tool_name = fc.name
            tool_args = dict(fc.args)
            tools_used.add(tool_name)
            
            yield {"type": "tool_call", "tool": tool_name, "args": tool_args}
            
            tool_result = execute_tool(tool_name, tool_args)
            yield {"type": "tool_result", "tool": tool_name, "result": tool_result}
            
            tool_response_parts.append(
                types.Part(function_response=types.FunctionResponse(name=tool_name, response={'result': tool_result}))
            )
            
        conversation_history.append(types.Content(role='tool', parts=tool_response_parts))

    yield {"type": "result", "data": {
        'claim_id': claim_id, 'decision': 'MANUAL_REVIEW',
        'approved_amount': 0.0, 'deducted_amount': 0.0,
        'missing_docs': [], 'policy_refs': [], 'confidence': 0.0,
        'explanation': 'Agent exceeded maximum turns. Routing to Manual Review.',
        'tools_used': sorted(tools_used),
    }}
