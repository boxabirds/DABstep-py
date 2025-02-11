from utils import create_agent, parse_args, check_tokens, setup_data_dir, CONTEXT_FILENAMES, generate_detailed_reasoning_trace, load_cached_dataset


def run_benchmark(dataset: datasets.Dataset, agent: CodeAgent) -> list[dict]:
  agent_answers = []
  for task in dataset:
    tid = task['task_id']

    prompt = PROMPT.format(
      context_files=CONTEXT_FILENAMES,
      question=task['question'],
      guidelines=task['guidelines']
    )

    answer = agent.run(prompt)

    task_answer = {
        "task_id": str(tid),
        "agent_answer": str(answer),
        "reasoning_trace": str(clean_reasoning_trace(agent.logs))
    }

    agent_answers.append(task_answer)

  return agent_answers

MAX_STEPS = 7
args = parse_args()
check_tokens(args)
context_files = setup_data_dir()
agent = create_agent(args)

PROMPT = """You are an expert data analyst and you will answer factoid questions by loading and referencing the files/documents listed below.
You have these files available:
{context_files}
Don't forget to reference any documentation in the data dir before answering a question.

Here is the question you need to answer:
{question}

Here are the guidelines you must follow when answering the question above:
{guidelines}
"""

SPLIT = "dev"
MAX_TASKS = 3 # It takes ~20 min to run the agent on all the dev set, so lets start just with the 2 first tasks
RUN_ID = int(time.time())


# Load dataset with explicit caching
dev_task_dataset = load_cached_dataset(split=SPLIT, max_tasks=MAX_TASKS)
agent_answers = run_benchmark(dataset=dev_task_dataset, agent=agent)

# Lets visualize the answers from our agent
pd.DataFrame(agent_answers)

# Now we evaluate the answers
agent_answers = pd.DataFrame(agent_answers)
tasks_df = dev_task_dataset.to_pandas()
task_scores = evaluate(agent_answers=agent_answers, tasks_with_gt=tasks_df)

# Inspect scores
task_scores = pd.DataFrame(task_scores)
task_scores["correct_answer"] = tasks_df["answer"]
task_scores["question"] = tasks_df["question"]
print(task_scores)
