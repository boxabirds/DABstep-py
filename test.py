from utils import create_agent, parse_args, check_tokens, setup_data_dir, CONTEXT_FILENAMES, generate_detailed_reasoning_trace
import os

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
question = "What are the unique set of merchants in the payments data?"
guidelines = "Answer with a comma separated list"

PROMPT = PROMPT.format(
    context_files=context_files,
    question=question,
    guidelines=guidelines
)

answer = agent.run(PROMPT)

print("\n\n==== REASONING TRACE ====")
print(generate_detailed_reasoning_trace(agent, args.api_base, os.getenv(args.api_key_var)))
