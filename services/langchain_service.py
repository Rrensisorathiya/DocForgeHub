from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os


def get_llm():
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_LLM_KEY"),
        api_version=os.getenv("AZURE_LLM_API_VERSION"),
        deployment_name=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI"),
        temperature=0.3,
    )


def generate_document_with_langchain(prompt_text: str) -> str:
    llm = get_llm()

    prompt = PromptTemplate(
        input_variables=["content"],
        template="{content}",
    )

    chain = LLMChain(llm=llm, prompt=prompt)

    result = chain.run(content=prompt_text)

    return result
