# services/azure_client.py

import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# ==============================
# Validate Required ENV Vars
# ==============================

required_env_vars = [
    "AZURE_OPENAI_LLM_KEY",
    "AZURE_LLM_API_VERSION",
    "AZURE_LLM_ENDPOINT",
    "AZURE_LLM_DEPLOYMENT_41_MINI",
]

for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"❌ Missing required environment variable: {var}")


# ==============================
# Azure OpenAI Client
# ==============================

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_LLM_KEY"),
    api_version=os.getenv("AZURE_LLM_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT"),
)

LLM_DEPLOYMENT = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI")


# ==============================
# LLM Completion Function
# ==============================

def generate_completion(prompt: str, temperature: float = 0.2) -> str:
    """
    Generates document completion using Azure OpenAI.
    Low temperature = stable enterprise documents.
    """

    try:
        response = client.chat.completions.create(
            model=LLM_DEPLOYMENT,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional enterprise SaaS document generation assistant. Follow instructions strictly."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=4000,
        )

        return response.choices[0].message.content

    except Exception as e:
        print("❌ Azure OpenAI Error:", str(e))
        raise

# # services/azure_client.py

# import os
# from openai import AzureOpenAI
# from dotenv import load_dotenv

# load_dotenv()

# client = AzureOpenAI(
#     api_key=os.getenv("AZURE_OPENAI_LLM_KEY"),
#     api_version=os.getenv("AZURE_LLM_API_VERSION"),
#     azure_endpoint=os.getenv("AZURE_LLM_ENDPOINT")
# )

# LLM_DEPLOYMENT = os.getenv("AZURE_LLM_DEPLOYMENT_41_MINI")


# def generate_completion(prompt: str, temperature: float = 0.2):
#     response = client.chat.completions.create(
#         model=LLM_DEPLOYMENT,
#         messages=[
#             {"role": "system", "content": "You are a professional enterprise document generation assistant."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=temperature,
#         max_tokens=4000
#     )

#     return response.choices[0].message.content
