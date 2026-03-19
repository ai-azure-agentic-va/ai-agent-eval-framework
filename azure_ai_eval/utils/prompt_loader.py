import os
import json
import re
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Local Path Configurations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_LIBRARY_PATH = os.path.join(os.path.dirname(BASE_DIR), "red_team_prompt_library.md")
CACHE_PATH = os.path.join(BASE_DIR, "prompts", "processed_prompts.json")

class PromptLoader:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPEN_AI_KEY"),
            api_version=os.getenv("API_VERSION", "2024-05-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

    def load_prompts(self, force_refresh=False):
        """Loads prompts from cache or extracts them from markdown if refresh is forced."""
        if not force_refresh and os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        print("Extracting prompts from library (Manual Parser -> JSON)...")
        with open(PROMPT_LIBRARY_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        prompts = []
        current_category = "Unknown"
        
        # Split by sections and entries
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Identify Category
            if line.startswith('### Category'):
                current_category = line.replace('###', '').strip()
                continue
            
            # Identify Prompt Entry: 1. **Name**: prompt
            # Or 1. **Name**:\n > prompt
            match = re.match(r'^\d+\.\s+\*\*(.*?)\*\*[:\s]*(.*)', line)
            if match:
                name = match.group(1).strip()
                text = match.group(2).strip()
                
                # Check next lines for blockquote if text is empty or just starts blockquote
                if not text or text.startswith('>'):
                    # This is handled by a lookahead in a more complex parser, 
                    # but for this specific library, most prompts are in the same line or next block
                    pass
                
                prompts.append({
                    "category": current_category,
                    "name": name,
                    "prompt": text if text else "See library for multi-turn details"
                })

        # Final cleanup: if prompt text is empty or starts with '>', 
        # we might need to grab the full block in a second pass
        # For the red_team_prompt_library.md specifically:
        prompts = []
        sections = re.split(r'### Category', content)
        for section in sections[1:]:
            lines = section.split('\n')
            cat_name = lines[0].strip()
            entries = re.split(r'\n\d+\.\s+\*\*', section)
            for entry in entries[1:]:
                parts = entry.split('**', 1)
                if len(parts) < 2: continue
                name = parts[0].strip()
                # Find the prompt text inside blockquote or after colon
                prompt_text = parts[1].strip()
                # Remove common markdown artifacts
                prompt_text = re.sub(r'^[:\s]*', '', prompt_text)
                prompt_text = re.sub(r'^>\s*', '', prompt_text, flags=re.MULTILINE)
                prompt_text = prompt_text.split('\n\n')[0] # Grab first block
                
                prompts.append({
                    "category": f"Category {cat_name}",
                    "name": name,
                    "prompt": prompt_text.strip().replace('"', '')
                })

        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, indent=2)
            
        return prompts

    def filter_prompts(self, prompts, category=None, name=None):
        if category:
            prompts = [p for p in prompts if category.lower() in p.get('category', '').lower()]
        if name:
            prompts = [p for p in prompts if name.lower() in p.get('name', '').lower()]
        return prompts
