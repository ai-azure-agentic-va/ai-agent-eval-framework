# Azure AI Evaluation Framework: Fresh DEV Setup

This guide provides a step-by-step process to set up the **Azure AI Evaluation Framework** in a fresh environment. This framework is designed to benchmark RAG performance, detect security vulnerabilities, and measure system latency.

---

## 📋 Prerequisites & RBAC Roles

Before starting, ensure your Azure environment and local machine meet these requirements:

- **Python**: v3.9+ (v3.10+ recommended).
- **Azure CLI**: Installed and updated.
- **Mandatory RBAC Roles**:
    - **Cognitive Services OpenAI User**: Required on the Azure OpenAI resource to execute Judge evaluations.
    - **Azure AI Developer**: Required on the Project to message Agents and create threads.
    - **Storage Blob Data Contributor**: Required if your project logs evaluation traces to cloud storage.

---

## 📦 Step 1: Environment Initialization

### 1.1 Secure Authentication
The framework uses `DefaultAzureCredential`. You **must** authenticate via the CLI before running any scripts.
```bash
az login
```

### 1.2 Virtual Environment Setup
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 1.3 Install dependencies
```bash
# Installs verified versions of azure-ai-evaluation, azure-ai-projects, etc.
pip install -r requirements_eval.txt
```

---

## 🚀 Step 2: Configuration (.env)

The framework relies on these specific variables for judging, agent interaction, and reporting. Duplicate [**`.env-template`**](file:///c:/projects/python/azure-rag-research/.env-template) to `.env` and configure accordingly:

### 2.1 Complete Property Inventory
| Property Key | Example Value | Description |
| :--- | :--- | :--- |
| **`AZURE_OPENAI_ENDPOINT`** | `https://res-name.openai.azure.com/` | The endpoint for the Azure OpenAI Judge model. |
| **`AZURE_OPEN_AI_KEY`** | `abcd...1234` | API Key for the GPT-4o judge resource. |
| **`AZURE_OPENAI_DEPLOYMENT_NAME`** | `gpt-4o` | The deployment name for the Judge model. |
| **`API_VERSION`** | `2024-05-01-preview` | The specific API version for judge inference. |
| **`AZURE_EXISTING_AGENT_ID"** | `550e8400-e29b-...` | The UUID of the Agent implementation to be tested. |
| **`AZURE_EXISTING_AIPROJECT_ENDPOINT`** | `https://eastus2.api.azureml.ms/...` | The AI Project endpoint for metrics & context access. |
| **`AZURE_EXISTING_AIPROJECT_RESOURCE_ID`** | `/subscriptions/.../workspaces/proj` | Full Resource ID for cloud-backed evaluation runs. |

### 2.2 Task-to-Command Mapping
| Evaluation Task | Primary Scenario | Validated CLI Command |
| :--- | :--- | :--- |
| **Retrieval Accuracy** | Top-K Retrieval Logic | `python -m azure_ai_eval.run_rag_benchmark --category "Category M"` |
| **Benchmark Citations** | Source Reference Integrity | `python -m azure_ai_eval.run_rag_benchmark --category "Category P"` |
| **Adversarial Security** | Adversarial Jailbreaks | `python run_red_team_eval.py --deployment gpt-4o` |
| **Wide-scale Perf Sweep** | All Knowledge Categories | `python -m azure_ai_eval.run_eval --all --refresh` |
| **Custom Scenario Integration** | Bespoke JSON tests | `python -m azure_ai_eval.run_rag_benchmark --file my_tests.json` |

---

## 🔗 Target Agent & URL Configuration

All three utilities (`run_rag_benchmark`, `run_eval`, and `run_red_team_eval`) target the same Azure AI Agent to ensure benchmark consistency.

---

## ✅ Recent Issues Fixed (Changelog)

1.  **Citation Accuracy**: Fixed halluncinations where the SDK could not map numeric citations back to source PDF metadata.
2.  **UI Parity Fallback**: Fixed an issue where the SDK trace environment throws 400 errors but the UI works; evaluators now fall back to response precision.
3.  **Thread Contamination**: Now creates a *fresh thread* for every evaluation to prevent prompt bias.

---

## 🔬 Evaluator Architecture (SDK vs. Custom)

| Evaluator Source | Class / Metric | Logic |
| :--- | :--- | :--- |
| **Azure AI SDK** | `Relevance` | Standard query/response alignment. |
| **Azure AI SDK** | `Groundedness` | Verifies claims against context snippets. |
| **Custom Built-in** | `RetrievalEvaluator` | Measures Top-K quality; handles SDK 400-error fallbacks. |
| **Custom Built-in** | `CitationEvaluator` | Verifies citations match actual source metadata. |
| **Custom Built-in** | `FallbackEvaluator` | Validates refusals for out-of-scope prompts. |
| **Post-Processor** | **p95 Latency** | Measures end-to-end response time across all categories. |

---

## 📊 Usage Examples & End-User Impact

Below are the validated runtime flags for every script and their expected impact on evaluation results. **All commands must be run from the project root.**

| Goal | Entry Point | End-User Impact |
| :--- | :--- | :--- |
| **Primary RAG Benchmark** | `python -m azure_ai_eval.run_rag_benchmark --refresh` | **Syncs RAG Baselines**: Re-ingests Category M-R prompts for **Retrieval, Relevance, and Citation** accuracy tests. |
| **General SDK Performance** | `python -m azure_ai_eval.run_eval --refresh` | **Updates Scenarios**: Syncs security probes for **Adversarial Jailbreaks and Persona Extraction**. |
| **Adversarial Security Sweep** | `python run_red_team_eval.py` | **100% Security Parity**: Bypasses cache to parse the markdown library directly for safety. |

---

## 🛠️ Developer Workflow: Adding a Custom Evaluator

1.  **Define**: Add a class in `evaluators.py` with `__init__` and `__call__`.
2.  **Register**: Instantiate in `AzureEvaluators`.
3.  **Map**: Add result to the `evaluate_response` loop.
4.  **Report**: Update HTML templates in `run_eval.py` or `run_rag_benchmark.py`.

---

## ❓ FAQ & Troubleshooting

This section compiles common environmental hurdles and the specific framework fixes implemented to ensure "Professional" class benchmarks.

### 🛡️ Core Environmental Fixes
- **Q: Why does the SDK show "Bad Request (400)" but the UI works?**
    - **A (UI Parity Fallback)**: The SDK environment often lacks internal secrets/tracing IDs used by the standard AI Foundry UI. We have implemented a **FallbackEvaluator** that ignores technical trace timeouts and evaluates the "Top-K" and "Groundedness" based on the actual agent response precision.
- **Q: Citations point to sources that don't exist?**
    - **A (Hallucination Guard)**: Fixed an issue where the standard SDK failed to map numeric citations (e.g., [1]) to the retrieved PDF snippet. The **CitationEvaluator** now performs direct quote verification against current metadata traces.
- **Q: Does past context bias the current evaluation?**
    - **A (Thread Reset)**: Yes. The framework now creates a **fresh thread** for every single evaluation prompt to ensure past history is discarded (Thread Decoupling).

### 🛠️ Developer Setup Issues
- **Q: `AuthenticationError` despite valid keys?**
    - **A**: Ensure you have run `az login` in your terminal session. The framework prioritizes your active CLI identity to prevent key-management leakage.
- **Q: `ModuleNotFoundError: No module named 'azure_ai_eval'`?**
    - **A**: The framework is developed as a package. You **must** be in the project root folder (not the sub-folder) and use the module flag: `python -m azure_ai_eval.run_eval`.
- **Q: The LLM Judge gives low scores for valid banking queries?**
    - **A**: Verify the Judge model is **GPT-4o**. Small models (e.g., GPT-4o-mini, GPT-3.5) lack the reasoning required for complex RAG benchmarking.
- **Q: Why am I getting 0 representation for p95 Latency?**
    - **A**: Latency calculation requires at least 2 runs. For statistical significance, a full category sweep (5-10 prompts) is recommended.

---

## 📂 Framework Directory Structure (Expanded)

This visual guide ensures all critical components are in place. **Do not modify the internal package structure** to maintain the integrity of prompt loading and evaluation traces.

```text
/ (Project Root)
├── .env-template              # Clean template for credentials
├── requirements_eval.txt      # Specialized dependencies (Verified Versions)
├── run_red_team_eval.py       # Standalane security sweep script
├── red_team_prompt_library.md # Markdown Source of Truth for all prompts
└── azure_ai_eval/             # Primary Evaluation Module (Package Root)
    ├── __init__.py            # Module entry (Imports run_eval and benchmarks)
    ├── run_eval.py            # Logic for general SDK-driven performance/security
    ├── run_rag_benchmark.py   # Primary logic for RAG Benchmarking & HTML reporting
    ├── prompts/               # [FOLDER] Structured scenario storage
    │   ├── custom_prompts.json    # Manually defined scenarios for bespoke tests
    │   └── processed_prompts.json # LLM-extracted cache for rapid script execution
    ├── evaluators/            # [FOLDER] Judge logic implementation
    │   ├── __init__.py            # Sub-module initialization
    │   └── evaluators.py          # Custom metric definitions (Citation/Fallback)
    └── utils/                 # [FOLDER] Core shared utilities
        ├── __init__.py            # SDK-level shared helpers
        ├── agent_client.py        # Interface for thread/message/trace extraction
        ├── custom_cred.py         # Handles multi-flow Azure authentication
        └── prompt_loader.py       # Logic to synchronize MD library with JSON cache
```

### 📄 File-by-File Inventory & Usage

| File Path | Description / Usage |
| :--- | :--- |
| **`azure_ai_eval/run_eval.py`** | General SDK evaluation script; generates `eval_framework_results.html`. |
| **`azure_ai_eval/run_rag_benchmark.py`** | Primary RAG benchmark utility; generates `rag_benchmark_report.html`. |
| **`azure_ai_eval/prompts/custom_prompts.json`** | Manually defined retrieval scenarios for benchmark integration. |
| **`azure_ai_eval/prompts/processed_prompts.json`** | **Auto-Cache**: Structured JSON version of the markdown library. |
| **`azure_ai_eval/evaluators/evaluators.py`** | Critical script containing custom logic for **Citations & Fallbacks**. |
| **`azure_ai_eval/utils/agent_client.py`** | Core engine for creating threads and extracting Tool Call context. |
| **`azure_ai_eval/utils/prompt_loader.py`** | Library parser that manages the Markdown-to-JSON caching cycle. |
