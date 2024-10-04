import discord
import openai
import PyPDF2
import io
import os

# Configure seu token do Discord e chave da API OpenAI
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Memórias para armazenamento de PDFs e conversas gerais
pdf_content = {}
general_memory = {}

# Função para extrair texto do PDF e dividir em partes menores
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""

    # Dividir o texto em partes menores para evitar exceder o limite de tokens
    max_tokens = 3000
    parts = [text[i:i + max_tokens] for i in range(0, len(text), max_tokens)]
    return parts

@client.event
async def on_ready():
    print(f'Logado como {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Comando !pdf para carregar o PDF
    if message.content.startswith("!pdf") and message.attachments:
        attachment = message.attachments[0]
        if attachment.filename.endswith('.pdf'):
            await message.channel.send("⏳ **Iniciando o processamento do PDF...**")

            try:
                pdf_bytes = await attachment.read()
                pdf_file = io.BytesIO(pdf_bytes)

                # Extraindo o texto do PDF
                pdf_text_parts = extract_text_from_pdf(pdf_file)

                # Verificar se o PDF é muito grande para ser processado de uma só vez
                total_tokens = sum(len(part) for part in pdf_text_parts)
                max_tokens_limit = 30000  # Limite do modelo gpt-4o

                if total_tokens > max_tokens_limit:
                    await message.channel.send("⚠️ O PDF enviado é muito grande para ser processado de uma vez só. Tentarei resumir o conteúdo para otimizar o processamento.")

                    # Abordagem alternativa: resumir partes do PDF para otimizar o processamento
                    summarized_parts = []
                    progress_message = await message.channel.send("🔄 **Resumindo o PDF... 0%**")
                    for i, part in enumerate(pdf_text_parts):
                        response = openai.ChatCompletion.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "Resuma o seguinte conteúdo de forma concisa:"},
                                {"role": "user", "content": part}
                            ]
                        )
                        summarized_parts.append(response.choices[0].message['content'])
                        await progress_message.edit(content=f"🔄 **Resumindo o PDF... {int((i + 1) / len(pdf_text_parts) * 100)}%**")

                    # Armazenar o resumo em vez do conteúdo completo
                    pdf_content[message.channel.id] = summarized_parts
                    await message.channel.send("✅ **PDF resumido e processado com sucesso!** Agora você pode usar `!gepetopdf` para fazer perguntas sobre o conteúdo.")
                else:
                    # Armazenar as partes do texto para futuras consultas
                    pdf_content[message.channel.id] = pdf_text_parts
                    await message.channel.send("✅ **PDF processado com sucesso!** Agora você pode usar `!gepetopdf` para fazer perguntas sobre o conteúdo.")
            except Exception as e:
                await message.channel.send(f"❌ **Erro ao processar o PDF:** {e}")
        else:
            await message.channel.send("⚠️ **Por favor, envie um arquivo em formato PDF.**")

    # Comando !gepetopdf para fazer perguntas sobre o PDF carregado
    elif message.content.startswith("!gepetopdf"):
        if message.channel.id not in pdf_content:
            await message.channel.send("⚠️ **Nenhum PDF foi carregado neste canal.** Por favor, envie um PDF usando `!pdf` primeiro.")
            return

        user_question = message.content[len("!gepetopdf"):].strip()
        if not user_question:
            await message.channel.send("⚠️ **Por favor, faça uma pergunta após o comando `!gepetopdf`.**")
            return

        await message.channel.send("⏳ **Analisando o conteúdo do PDF, por favor aguarde...**")

        try:
            # Preparar mensagens para a API da OpenAI
            messages = [
                {"role": "system", "content": "Você é um assistente que responde perguntas sobre o conteúdo de um documento."},
            ]

            # Adicionar cada parte do conteúdo do PDF como contexto
            for part in pdf_content[message.channel.id]:
                messages.append({"role": "user", "content": f"Conteúdo do PDF: {part[:2000]}"})  # Limite para evitar erro do Discord

            # Adicionar a pergunta do usuário
            messages.append({"role": "user", "content": user_question[:2000]})  # Limite para evitar erro do Discord

            # Fazer a solicitação à API da OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=messages
            )

            # Extrair e enviar a resposta
            answer = response.choices[0].message['content']

            # Enviar a resposta em partes se necessário
            for i in range(0, len(answer), 2000):
                await message.channel.send(f"**Resposta:**\n{answer[i:i+2000]}")

        except Exception as e:
            await message.channel.send(f"❌ **Erro ao se comunicar com a API da OpenAI:** {e}")

    # Comando !gepeto para fazer perguntas gerais
    elif message.content.startswith("!gepeto"):
        user_question = message.content[len("!gepeto"):].strip()
        if not user_question:
            await message.channel.send("⚠️ **Por favor, faça uma pergunta após o comando `!gepeto`.**")
            return

        await message.channel.send("⏳ **Analisando sua pergunta, por favor aguarde...**")

        try:
            # Manter a memória do contexto das perguntas anteriores
            if message.channel.id not in general_memory:
                general_memory[message.channel.id] = []

            # Adicionar a pergunta do usuário ao contexto
            general_memory[message.channel.id].append({"role": "user", "content": user_question})

            # Fazer a solicitação à API da OpenAI com o contexto completo
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=general_memory[message.channel.id]
            )

            # Extrair e enviar a resposta
            answer = response.choices[0].message['content']
            general_memory[message.channel.id].append({"role": "assistant", "content": answer})

            # Enviar a resposta em partes se necessário
            for i in range(0, len(answer), 2000):
                await message.channel.send(f"**Resposta:**\n{answer[i:i+2000]}")

        except Exception as e:
            await message.channel.send(f"❌ **Erro ao se comunicar com a API da OpenAI:** {e}")

client.run(DISCORD_TOKEN)