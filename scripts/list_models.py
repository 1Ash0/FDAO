"""List available Groq models using keys from .env"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

import openai

keys = [v for k, v in sorted(os.environ.items())
        if k == "GROQ_API_KEY" or (k.startswith("GROQ_API_KEY_") and v)]

if not keys:
    print("No GROQ keys found")
    sys.exit(1)

c = openai.OpenAI(api_key=keys[0], base_url="https://api.groq.com/openai/v1")
models = c.models.list()
for m in sorted(m.id for m in models.data):
    print(m)
