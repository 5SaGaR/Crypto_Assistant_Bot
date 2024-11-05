import gradio as gr
from dotenv import load_dotenv
from CryptoBot import CryptoBot

# Load environment variables
load_dotenv()

class Error(Exception):
    '''Other than API-related errors'''

# Create Gradio interface
def create_gradio_interface():
# Initializes and launches a Gradio interface to interact with CryptoBot. 
# This function creates a chat interface with example queries and custom styling, allowing users to interact with the bot in a conversational setting.

    bot = CryptoBot()
    
    def respond(message: str, history: list) -> str:
        try:
            return bot.process_user_query(message, history)
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"

    interface = gr.ChatInterface(
        respond,
        title="Crypto Assistant Bot",
        description="Ask me anything about cryptocurrencies!",
        theme=gr.themes.Soft(),
        examples=[
            "What's the current price of Bitcoin?",
            "Show me the top 10 cryptocurrencies",
            "Tell me about Ethereum's market cap"
        ]
    )
    
    return interface

if __name__ == "__main__":
    try:
        interface = create_gradio_interface()
        interface.launch(share=True)
    except Exception as e:
        raise Error("Gradio application failed to start")
