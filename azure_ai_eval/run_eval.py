import os
import argparse
import time
import html
from datetime import datetime
from dotenv import load_dotenv
from azure_ai_eval.utils.agent_client import AgentClient
from azure_ai_eval.utils.prompt_loader import PromptLoader
from azure_ai_eval.evaluators.evaluators import AzureEvaluators

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Azure AI Evaluation Framework CLI")
    parser.add_argument("--all", action="store_true", help="Run all evaluations (default behavior if no filters)")
    parser.add_argument("--category", type=str, help="Filter by prompt category (e.g., 'Category L')")
    parser.add_argument("--name", type=str, help="Filter by prompt name")
    parser.add_argument("--refresh", action="store_true", help="Force refresh of the prompt cache")
    args = parser.parse_args()

    # Configuration for Evaluators
    model_config = {
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"),
        "api_key": os.getenv("AZURE_OPEN_AI_KEY"),
        "api_version": os.getenv("API_VERSION", "2024-05-01-preview")
    }

    loader = PromptLoader()
    agent = AgentClient()
    evaluators = AzureEvaluators(model_config)

    # 1. Load and Filter Prompts
    all_prompts = loader.load_prompts(force_refresh=args.refresh)
    filtered_prompts = loader.filter_prompts(all_prompts, category=args.category, name=args.name)

    if not filtered_prompts:
        print("No prompts found matching your criteria.")
        return

    print(f"Executing {len(filtered_prompts)} evaluations...")
    results = []

    # 2. Execution Loop
    for p in filtered_prompts:
        name = p.get('name', 'Unknown')
        category = p.get('category', 'Unknown')
        prompt_text = p.get('prompt', '')

        print(f"\n[Testing] [{category}] {name}")
        
        start_counter = time.perf_counter()
        agent_out = agent.call_agent(prompt_text)
        latency = time.perf_counter() - start_counter
        
        agent_response = agent_out.get("response", "")
        context_text = agent_out.get("context", "")
        
        print(f"Response received in {latency:.2f}s. Evaluating with Context: {'Yes' if context_text else 'No'}...")
        
        # Pass the actual retrieved context for groundedness and retrieval metrics
        eval_scores = evaluators.evaluate_response(
            query=prompt_text, 
            response=agent_response, 
            context=context_text
        )
        
        results.append({
            "category": category,
            "name": name,
            "prompt": prompt_text,
            "response": agent_response,
            "latency": latency,
            "eval_scores": eval_scores
        })

    # 3. Generate HTML Report
    generate_report(results)

def generate_report(results):
    report_path = "eval_framework_results.html"
    
    # Calculate Summary Metrics
    latencies = sorted([r['latency'] for r in results])
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0
    
    # Aggregate scores
    metrics = {
        'relevance': [],
        'retrieval': [],
        'citations': [],
        'groundedness': [],
        'jailbreak': []
    }
    
    for r in results:
        for m_name in metrics.keys():
            score_obj = r['eval_scores'].get(m_name, {})
            # Try to fetch numeric value
            val = None
            if m_name == 'jailbreak': val = score_obj.get('rating')
            elif m_name == 'retrieval': val = score_obj.get('retrieval_score')
            elif m_name == 'citations': val = score_obj.get('citation_scores', {}).get('accuracy')
            else: val = score_obj.get(m_name)
            
            if isinstance(val, (int, float)):
                metrics[m_name].append(val)

    def avg(lst): return sum(lst) / len(lst) if lst else 0

    # Group results by category
    grouped_results = {}
    for r in results:
        cat = r['category']
        if cat not in grouped_results: grouped_results[cat] = []
        grouped_results[cat].append(r)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Azure AI Evaluation Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f3f2f1; line-height: 1.5; }}
        .header-card {{ background: #0078d4; color: white; padding: 25px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 25px; }}
        .summary-item {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #edebe9; }}
        .summary-item h3 {{ margin: 0; color: #605e5c; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }}
        .summary-item p {{ margin: 8px 0 0 0; font-size: 1.8em; font-weight: 700; color: #0078d4; }}
        .category-header {{ background: #323130; color: white; padding: 12px 20px; border-radius: 4px; margin-top: 30px; margin-bottom: 15px; font-weight: 600; }}
        table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        th, td {{ border: 1px solid #edebe9; padding: 15px; text-align: left; vertical-align: top; }}
        th {{ background-color: #f3f2f1; color: #323130; font-weight: 600; font-size: 0.9em; }}
        .metric-label {{ font-weight: 600; color: #323130; font-size: 0.85em; }}
        .pass-bg {{ background: #dff6dd; color: #107c10; border-radius: 4px; padding: 2px 6px; font-weight: 700; }}
        .fail-bg {{ background: #fde7e9; color: #d13438; border-radius: 4px; padding: 2px 6px; font-weight: 700; }}
        .score-row {{ border-bottom: 1px solid #f3f2f1; padding: 10px 0; }}
        .score-row:last-child {{ border-bottom: none; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; font-size: 0.9em; margin: 0; color: #444; }}
    </style>
</head>
<body>
    <div class="header-card">
        <h1>Red Team & RAG Evaluation Dashboard</h1>
        <p>Enterprise AI Test Suite | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="summary-grid">
        <div class="summary-item"><h3>Total Prompts</h3><p>{len(results)}</p></div>
        <div class="summary-item"><h3>Top-K Retrieval</h3><p>{avg(metrics['retrieval']):.2f}/5</p></div>
        <div class="summary-item"><h3>Response Relevance</h3><p>{avg(metrics['relevance']):.2f}/5</p></div>
        <div class="summary-item"><h3>Faithfulness (Grounded)</h3><p>{avg(metrics['groundedness']):.2f}/5</p></div>
        <div class="summary-item"><h3>Citation Accuracy</h3><p>{avg(metrics['citations']):.2f}/5</p></div>
        <div class="summary-item"><h3>Avg Latency</h3><p>{avg_latency:.2f}s</p></div>
        <div class="summary-item"><h3>p95 Latency</h3><p>{p95_latency:.2f}s</p></div>
    </div>
"""
    for category, cat_results in grouped_results.items():
        html_content += f'<div class="category-header">{html.escape(category)}</div>'
        html_content += """
        <table>
            <tr>
                <th style="width: 20%">Test Case</th>
                <th style="width: 30%">Prompt / Response</th>
                <th style="width: 40%">Metric Evaluation (SDK + Custom)</th>
                <th style="width: 10%">Perf</th>
            </tr>
        """
        for r in cat_results:
            scores_html = ""
            for m_name, score_obj in r['eval_scores'].items():
                if not score_obj: continue
                
                label = m_name.replace('_', ' ').capitalize()
                val = "N/A"
                reason = ""
                status = "pass"
                
                if m_name == 'jailbreak':
                    val = f"{score_obj.get('rating', 'N/A')}/5"
                    status = "fail" if score_obj.get('jailbreak_detected') else "pass"
                    reason = score_obj.get('reasoning', '')
                elif m_name == 'retrieval':
                    val = f"{score_obj.get('retrieval_score', 'N/A')}/5"
                    status = "pass" if score_obj.get('retrieval_score', 0) >= 3 else "fail"
                    reason = score_obj.get('reasoning', '')
                elif m_name == 'citations':
                    val = f"{score_obj.get('citation_scores', {}).get('accuracy', 'N/A')}/5"
                    status = "pass" if score_obj.get('citation_scores', {}).get('accuracy', 0) >= 3 else "fail"
                    reason = score_obj.get('reasoning', '')
                else:
                    val = f"{score_obj.get(m_name, 'N/A')}/5"
                    status = "pass" if (isinstance(score_obj.get(m_name), (int, float)) and score_obj.get(m_name) >= 3) else "fail"
                    reason = score_obj.get(f"{m_name}_reason", "")

                status_class = "pass-bg" if status == "pass" else "fail-bg"
                scores_html += f"""
                <div class="score-row">
                    <span class="metric-label">{label}:</span> 
                    <span class="score-box {status_class}">{val}</span><br>
                    <span style="font-size: 0.8em; color: #605e5c;">{html.escape(str(reason))}</span>
                </div>
                """

            html_content += f"""
            <tr>
                <td><strong>{html.escape(r['name'])}</strong></td>
                <td>
                    <div style="margin-bottom: 10px; border-bottom: 1px dashed #edebe9; padding-bottom: 5px;">
                        <small class="metric-label">PROMPT:</small><br><pre>{html.escape(r['prompt'])}</pre>
                    </div>
                    <div>
                        <small class="metric-label">RESPONSE:</small><br><pre>{html.escape(r['response'])}</pre>
                    </div>
                </td>
                <td>{scores_html}</td>
                <td style="text-align: center;">
                    <div class="summary-item" style="padding: 10px; box-shadow: none;">
                        <h3>LATENCY</h3>
                        <p style="font-size: 1.1em; margin: 0;">{r['latency']:.2f}s</p>
                    </div>
                </td>
            </tr>
            """
        html_content += "</table>"

    html_content += "</body></html>"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\nReport generated: {report_path}")

if __name__ == "__main__":
    main()
