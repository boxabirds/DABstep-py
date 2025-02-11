import time
import os
import json
import datasets
import pandas as pd
from smolagents import CodeAgent, OpenAIServerModel
from smolagents.agents import ActionStep
from huggingface_hub import login, hf_hub_download
from dabstep_benchmark.utils import evaluate
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run DABstep with configurable model and API settings')
parser.add_argument('--model-id', type=str, default="deepseek-coder:6.7b-instruct-q4_K_M",
                   help='Model ID to use (default: deepseek-coder:6.7b-instruct-q4_K_M)')
parser.add_argument('--api-base', type=str, default="http://gruntus:11434/v1",
                   help='API base URL (default: http://gruntus:11434/v1)')
args = parser.parse_args()

token = os.getenv("HF_TOKEN")
if token is None:
    raise ValueError("HF_TOKEN is not set in your environment")
login(token=token, new_session=True)


CONTEXT_FILENAMES = [
    "data/context/acquirer_countries.csv",
    "data/context/payments-readme.md",
    "data/context/payments.csv",
    "data/context/merchant_category_codes.csv",
    "data/context/fees.json",
    "data/context/merchant_data.json",
    "data/context/manual.md",
]
DATA_DIR = "DABstep-data"

# Create the data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Download files only if they don't exist
for filename in CONTEXT_FILENAMES:
    local_path = os.path.join(DATA_DIR, filename)
    
    # Create subdirectories if they don't exist
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    if not os.path.exists(local_path):
        print(f"Downloading {filename}...")
        hf_hub_download(
            repo_id="adyen/DABstep",
            repo_type="dataset",
            filename=filename,
            local_dir=DATA_DIR,
            force_download=False
        )
    else:
        print(f"File already exists: {local_path}")

CONTEXT_FILENAMES = [f"{DATA_DIR}/{filename}" for filename in CONTEXT_FILENAMES]

# Verify all files exist
missing_files = []
for file in CONTEXT_FILENAMES:
    if os.path.exists(file):
        print(f"✓ {file} exists.")
    else:
        print(f"✗ {file} does not exist!")
        missing_files.append(file)

if missing_files:
    raise FileNotFoundError(f"Missing required files: {', '.join(missing_files)}")


# Configuration
MAX_STEPS = 7


# Create agent with Ollama configuration
agent = CodeAgent(
    tools=[],
    model=OpenAIServerModel(
        model_id=args.model_id,
        api_base=args.api_base,
    ),
    additional_authorized_imports=["numpy", "pandas", "json", "csv", "os", "glob", "markdown"],
    max_steps=MAX_STEPS,
)

# Enable file operations
agent.python_executor.static_tools.update({"open": open})


PROMPT = """You are an expert data analyst and you will answer factoid questions by loading and referencing the files/documents listed below.
You have these files available:
{context_files}
Don't forget to reference any documentation in the data dir before answering a question.

Here is the question you need to answer:
{question}

Here are the guidelines you must follow when answering the question above:
{guidelines}
"""
question = "What are the unique set of merchants in the payments data?"
guidelines = "Answer with a comma separated list"

PROMPT = PROMPT.format(
    context_files=CONTEXT_FILENAMES,
    question=question,
    guidelines=guidelines
)

answer = agent.run(PROMPT)
