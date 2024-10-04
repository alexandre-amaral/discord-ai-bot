import os
import openai

# Configurar a chave da API do OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def chat_with_openai(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=150
    )
    return response.choices[0].message['content'].strip()

if __name__ == "__main__":
    print("Digite 'sair' para encerrar o chat.")
    while True:
        user_input = input("Você: ")
        if user_input.lower() == 'sair':
            break
        response = chat_with_openai(user_input)
        print(f"Bot: {response}")