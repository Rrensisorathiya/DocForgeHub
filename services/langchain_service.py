import os
from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

# Document length → max tokens mapping
DOCUMENT_MAX_TOKENS = {
    "short":  1000,   # 1 page
    "medium": 4000,   # 4-8 pages
    "long":   12000,  # 35+ pages
}

def get_llm(max_tokens: int = 4000):
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_LLM_KEY"),
        api_version=os.getenv("AZURE_LLM_API_VERSION"),
        deployment_name=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI"),
        temperature=0.3,
        max_tokens=max_tokens,  # ← KEY FIX
    )

def generate_document_with_langchain(prompt_text: str, doc_type: str = "") -> str:
    """
    Generate document with correct max_tokens based on document length.
    Long docs (Employee Handbook etc) get 12000 tokens = 35+ pages.
    """
    # Detect length from prompt
    if "15000-20000 words" in prompt_text or "35+ pages" in prompt_text:
        max_tokens = DOCUMENT_MAX_TOKENS["long"]
    elif "2000-4000 words" in prompt_text or "4-8 pages" in prompt_text:
        max_tokens = DOCUMENT_MAX_TOKENS["medium"]
    else:
        max_tokens = DOCUMENT_MAX_TOKENS["short"]

    logger.info(f"Generating doc — max_tokens: {max_tokens}")

    llm = get_llm(max_tokens=max_tokens)
    prompt = PromptTemplate(
        input_variables=["content"],
        template="{content}",
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run(content=prompt_text)
# import os
# from langchain_openai import AzureChatOpenAI
# from langchain.prompts import PromptTemplate
# from langchain.chains import LLMChain
# from dotenv import load_dotenv
# from utils.logger import setup_logger

# load_dotenv()

# logger = setup_logger(__name__)

# def get_llm():
#     return AzureChatOpenAI(
#         azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
#         api_key=os.getenv("AZURE_OPENAI_LLM_KEY"),
#         api_version=os.getenv("AZURE_LLM_API_VERSION"),
#         deployment_name=os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI"),
#         temperature=0.3,
#     )

# def generate_document_with_langchain(prompt_text: str) -> str:
#     llm = get_llm()
#     prompt = PromptTemplate(
#         input_variables=["content"],
#         template="{content}",
#     )
#     chain = LLMChain(llm=llm, prompt=prompt)
#     return chain.run(content=prompt_text)