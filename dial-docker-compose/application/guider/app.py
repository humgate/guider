"""
A DIAL application which guides user for choosing a book from defined set of books.
"""
from pathlib import Path

import uvicorn

from aidial_sdk import DIALApp
from aidial_sdk.chat_completion import ChatCompletion, Request, Response
from openai import OpenAI
from util import utils

openai_client = OpenAI(
    base_url="http://192.168.0.195:11434/v1",
    api_key='ollama'  # required, but unused
)
model = "llama3.1"
consideration_limit = 6  # how many relevant books from dataset to consider in interaction with user
books_file_path = "data/books_400.json"


# ChatCompletion is an abstract class for applications and model adapters
class GuiderApplication(ChatCompletion):
    def __init__(self):
        super().__init__()
        self.books = utils.load_books(Path(books_file_path))
        self.conversation_initiation = True

    async def chat_completion(
            self, request: Request, response: Response
    ) -> None:
        # Get last message (the newest) from the history
        last_user_message = request.messages[-1]

        # Generate response with a single choice
        with response.create_single_choice() as choice:
            # Conversion init
            if self.conversation_initiation:
                initial_prompt = utils.create_base_prompt(initial_conversation=True, model=model)
                openai_client.chat.completions.create(**initial_prompt)
                self.conversation_initiation = False

            # Extract keywords from user prompt
            keyword_prompt = utils.create_few_shot_keyword_prompt(
                user_query=last_user_message.content,
                model=model,
                max_tokens=50
            )
            keywords_response = openai_client.chat.completions.create(**keyword_prompt)
            keywords = keywords_response.choices[0].message.content
            # Get relevant books matching keywords
            relevant_books = utils.get_relevant_books(keywords, self.books, consideration_limit)

            # Construct base prompt and get main response for user
            base_prompt = utils.create_base_prompt(
                initial_conversation=self.conversation_initiation,
                user_query=last_user_message.content,
                relevant_books=relevant_books,
                model=model)
            base_response = openai_client.chat.completions.create(**base_prompt)
            completion = base_response.choices[0].message.content
            choice.append_content(completion or "")


# DIALApp extends FastAPI to provide a user-friendly interface for routing requests to your applications
app = DIALApp()
app.add_chat_completion("guider", GuiderApplication())

# Run built app
if __name__ == "__main__":
    uvicorn.run(app, port=5000, host="0.0.0.0")
