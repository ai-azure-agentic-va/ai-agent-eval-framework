import os
from azure.ai.projects import AIProjectClient
from azure_ai_eval.utils.custom_cred import CustomAzureCliCredential
from azure.ai.agents.models import ListSortOrder
from dotenv import load_dotenv

load_dotenv()

class AgentClient:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_EXISTING_AIPROJECT_ENDPOINT")
        self.agent_id = os.getenv("AZURE_EXISTING_AGENT_ID")
        self.credential = CustomAzureCliCredential()
        self.project_client = AIProjectClient(
            credential=self.credential,
            endpoint=self.endpoint
        )

    def call_agent(self, prompt):
        """Creates a new thread, sends message, and extracts RAG context from run steps."""
        try:
            thread = self.project_client.agents.threads.create()
            self.project_client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            run = self.project_client.agents.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self.agent_id
            )
            
            # Fetch error if present
            run_error = str(run.last_error) if getattr(run, 'last_error', None) else None
            
            # Fetch messages (Assistant Response)
            # ItemPaged is iterable directly
            messages_pager = self.project_client.agents.messages.list(thread_id=thread.id)
            messages_list = list(messages_pager)
            response_text = ""
            
            # Extract text from the latest assistant message
            for message in reversed(messages_list):
                if message.role == "assistant":
                    if hasattr(message, 'text_messages') and message.text_messages:
                        response_text = message.text_messages[-1].text.value
                    elif hasattr(message, 'content') and message.content:
                        # Fallback for standard SDK content format
                        for item in message.content:
                            if hasattr(item, 'text') and hasattr(item.text, 'value'):
                                response_text = item.text.value
                                break
                    if response_text: break

            # If no text but run failed, show the error
            if not response_text and run_error:
                response_text = f"Run failed: {run_error}"

            # Extract RAG Context from Run Steps (Tool Calls)
            context_text = ""
            steps_pager = self.project_client.agents.run_steps.list(thread_id=thread.id, run_id=run.id)
            for step in steps_pager:
                if step.step_details and hasattr(step.step_details, 'tool_calls'):
                    for tc in step.step_details.tool_calls:
                        t_type = getattr(tc, 'type', 'unknown')
                        
                        if t_type == 'file_search':
                            context_text += f"[File Search]: {getattr(tc, 'file_search', 'Active Reference')}\n"
                        elif t_type == 'code_interpreter':
                            context_text += f"[Code Interpreter]: {getattr(tc.code_interpreter, 'input', 'CI Logic')}\n"
                        elif t_type in ['function', 'openapi']:
                            obj = getattr(tc, 'function', getattr(tc, 'openapi', None))
                            if obj:
                                tool_name = getattr(obj, 'name', 'api_call')
                                tool_out = getattr(obj, 'output', 'No Output/Environment Error')
                                context_text += f"[Tool: {tool_name}]: {tool_out}\n"

            # Fallback to annotations (Citations)
            if not context_text:
                for message in reversed(messages_list):
                    if message.role == "assistant" and hasattr(message, 'text_messages') and message.text_messages:
                        for ann in message.text_messages[-1].text.annotations:
                            if hasattr(ann, 'file_citation'):
                                context_text += f"[Citation]: {ann.file_citation.quote}\n"

            return {"response": response_text, "context": context_text}
        except Exception as e:
            return {"response": f"Agent Exception: {str(e)}", "context": ""}
