import os
import argparse
from smolagents import CodeAgent, OpenAIServerModel, LiteLLMModel
from smolagents.agents import ActionStep
from smolagents.monitoring import LogLevel
from datasets import load_dataset, load_from_disk

from huggingface_hub import login, hf_hub_download

# Constants
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

def clean_reasoning_trace(agent: CodeAgent) -> list:
  for step in agent.logs:
      # Remove memory from logs to make them more compact.
      if hasattr(step, "memory"):
          step.memory = None
      if isinstance(step, ActionStep):
          step.agent_memory = None
  return agent.logs

def generate_detailed_reasoning_trace(agent: CodeAgent, api_base: str, api_key: str) -> str:
    model = OpenAIServerModel(
            model_id=agent.model.model_id,
            api_base=api_base,
            api_key=api_key
        )
    
    cleaned_steps = []
    step_count = 1
    
    for step in agent.logs:
        if isinstance(step, ActionStep):          
            # Clean up this individual step
            response = model.client.chat.completions.create(
                model=agent.model.model_id,
                messages=[{"role": "user", "content": f"without additional narrative,tidy up this text so it's more readable as plain text: {step}"}]
            )
            cleaned_step = response.choices[0].message.content
            cleaned_steps.append(cleaned_step)
            step_count += 1
            print(f"Step {step_count}: {cleaned_step}")
    
    # Join all cleaned steps with double newlines for spacing
    return "\n\n".join(cleaned_steps)

def parse_args():
    parser = argparse.ArgumentParser(description='Run DABstep with configurable model and API settings')
    parser.add_argument('--model-id', type=str, default="gpt-4o-mini",
                       help='Model ID to use (default: gpt-4o-mini)')
    parser.add_argument('--api-base', type=str,
                       help='API base URL')
    parser.add_argument('--api-key-var', type=str, default="OPENAI_API_KEY",
                       help='Environment variable name for API key (default: OPENAI_API_KEY)')
    return parser.parse_args()

def check_tokens(args):
    hf_token = os.getenv("HF_TOKEN")
    if hf_token is None:
        raise ValueError("HF_TOKEN is not set in your environment")
    login(token=hf_token, new_session=True)

    api_key = os.getenv(args.api_key_var)
    if api_key is None:
        raise ValueError(f"{args.api_key_var} is not set in your environment")
    # print out the api key var and the value 
    print(f"Using {args.api_key_var}={api_key}")
    return api_key

def setup_data_dir():
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

    context_files = [f"{DATA_DIR}/{filename}" for filename in CONTEXT_FILENAMES]

    # Verify all files exist
    missing_files = []
    for file in context_files:
        if os.path.exists(file):
            print(f"✓ {file} exists.")
        else:
            print(f"✗ {file} does not exist!")
            missing_files.append(file)

    if missing_files:
        raise FileNotFoundError(f"Missing required files: {', '.join(missing_files)}")
    
    return context_files

def print_clean_reasoning_trace(trace):
    for step in clean_reasoning_trace(trace):
        print(step)

def create_agent(args):
    MAX_STEPS = 7
    agent = CodeAgent(
        tools=[],
        verbosity_level=LogLevel.DEBUG,
        model=OpenAIServerModel(
            model_id=args.model_id,
            api_base=args.api_base,
            api_key=os.getenv(args.api_key_var)
        ),
        additional_authorized_imports=["numpy", "pandas", "json", "csv", "os", "glob", "markdown"],
        max_steps=MAX_STEPS,
    )
    agent.python_executor.static_tools.update({"open": open})
    return agent

def load_cached_dataset(split: str, max_tasks: int) -> datasets.Dataset:
    """Load the dataset from cache if it exists, otherwise download and cache it."""
    cache_path = os.path.join(DATA_DIR, "datasets", f"tasks_{split}_{max_tasks}.cache")
    
    if os.path.exists(cache_path):
        print(f"Loading cached dataset from {cache_path}")
        return load_from_disk(cache_path)
    
    print(f"Downloading dataset for split={split}, max_tasks={max_tasks}")
    dataset = load_dataset("adyen/DABstep", name="tasks", split=f"{split}[:{max_tasks}]")
    
    # Save to our cache
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    dataset.save_to_disk(cache_path)
    print(f"Cached dataset to {cache_path}")
    
    return dataset