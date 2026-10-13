# ORION Version 2

ORION is a customer support and general-purpose chat assistant powered by LangChain and Google AI Studio. It keeps conversation context, classifies support issues and sentiment, and creates tickets for escalations.

## Setup

1. Set `GOOGLE_API_KEY` in `.env` (`Gemini_API_KEY` is also accepted for existing local configuration).
2. Optionally set `GEMINI_MODEL` in `.env` (default: `gemini-3.5-flash-lite`; `Gemini_MODEL` is also accepted).
3. Install dependencies with `python3 -m pip install -r requirements.txt`.
4. Start the app with `python3 -m streamlit run orion/app.py --server.headless true --server.port 8502`.

ORION checks the Google AI Studio key and sends a small Gemini test prompt when the session starts. The selected model, connection state, test result, and provider errors appear in the diagnostics panel.

## Support Intelligence

- `orion/knowledge_base.md` contains the customer-support policies and communication standards used for retrieval.
- `orion/knowledge_base.py` embeds the policy sections with Gemini Embeddings and retrieves relevant guidance from a persistent Chroma vector store before every answer.
- `orion/business_rules.py` determines deterministic ticket, escalation, and priority decisions before the model generates a response.
- `orion/ticket_manager.py` persists ticket IDs, status, priority, customer/order details, summary, and creation timestamp in SQLite.
- `.orion_data/` stores the local vector index and ticket database and is excluded from source control.

## Project structure

- `orion/app.py`: Streamlit chat interface and session lifecycle
- `orion/config.py`: `.env` loading and Gemini connection validation
- `orion/support_chain.py`: LangChain Gemini generation, prompts, and escalation
- `orion/knowledge_base.py`: Gemini embeddings and persistent policy retrieval
- `orion/knowledge_base.md`: business support policies
- `orion/business_rules.py`: deterministic issue/ticket/escalation rules
- `orion/memory_manager.py`: conversation history and customer context
- `orion/sentiment.py`: issue classification and escalation priority
- `orion/ticket_manager.py`: support ticket creation
