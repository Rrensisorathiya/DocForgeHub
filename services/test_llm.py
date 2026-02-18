from services.azure_client import generate_completion

response = generate_completion("Write a short professional welcome message for a SaaS company.")
print(response)
