import os
from dotenv import load_dotenv
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from datasets import Dataset

load_dotenv()

test_data = {
    "question": ["Hi"],
    "answer": ["Hello"],
    "contexts": [["Greeting"]],
    "ground_truth": ["Greeting"]
}
dataset = Dataset.from_dict(test_data)

llm = ChatOpenAI(model="gpt-4o")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

print("Running evaluate...")
result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision],
    llm=llm,
    embeddings=embeddings
)
print(result)
