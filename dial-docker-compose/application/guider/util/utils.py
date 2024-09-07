import copy
import json


# Main prompt to LLM containing system prompt, relevant books selected by keywords and user prompt
def create_base_prompt(user_query=None, relevant_books=None, initial_conversation=False, model="llama3.1"):
    messages = []
    if initial_conversation:
        initial_system_messages = [
            {
                "role": "system",
                "content": "Act as a professional bookstore manager and guide the user through choosing the right book "
                           "without explicitly mentioning the source of the books. You have a collection of books that "
                           "you can recommend based on the user's needs.",
            },
            {
                "role": "system",
                "content": "Make your recommendations seem natural and based on your knowledge without saying they come"
                           "from a provided list.",
            },
            {
                "role": "system",
                "content": "Always provide structured responses and help the user make an informed choice.",
            }
        ]
        messages = initial_system_messages
    else:
        formatted_books = format_books_for_llm(relevant_books)
        system_messages = [
            {
                "role": "system",
                "content": "You have the following books in your knowledge base that might help the user:\n"
                           + formatted_books
            },
        ]
        user_message = {"role": "user", "content": user_query}
        messages = system_messages + [user_message]

    return {
        "messages": messages,
        "model": model,
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 768

    }


# Prompt to get keywords from user prompt
def create_few_shot_keyword_prompt(user_query, model, max_tokens):
    system_message = {
        "role": "system",
        "content": "Extract important keywords from the user's query for the purpose of filtering a book data."
                   "Respond with comma separated list of keywords. "
                   "Do not include any other text or labels or explanations"
    }
    # Few-shot examples
    examples = [
        {"role": "user", "content": "I want to find a book on Python programming for beginners."},
        {"role": "assistant", "content": "Python, programming, book, beginners"}
    ]
    user_message = {"role": "user", "content": user_query}

    return {
        "messages": [system_message] + examples + [user_message],
        "model": model,
        "stream": False,
        "max_tokens": max_tokens
    }


def load_books(file_path):
    with open(file_path, 'r') as file:
        books = json.load(file)

    return books


def get_relevant_books(keywords, books, consideration_limit):
    relevant_books = []
    keywords_list = [keyword.strip() for keyword in keywords.split(',')]
    for book in books:
        for keyword in keywords_list:
            if (
                    keyword.lower() in book['title'].lower() and
                    any(keyword.lower() in category.lower() for category in book.get('categories', []))
            ):
                relevant_books.append(book)
                break
        if len(relevant_books) >= consideration_limit:  # Limit number of books to avoid exceeding token limit
            break

    return compact_books(relevant_books)


# Removing not critical book attributes to save on base prompt size
def compact_books(books):
    books_copy = copy.deepcopy(books)
    for book in books_copy:
        if 'longDescription' in book:
            del book['longDescription']
        if 'shortDescription' in book:
            del book['shortDescription']
        if 'thumbnailUrl' in book:
            del book['thumbnailUrl']
        if 'status' in book:
            del book['status']
        if 'publishedDate' in book:
            published_date = book.get('publishedDate', {}).get('$date')
            book['publishedDate'] = published_date.split('T')[0]

    return books_copy


# Formatted message for the relevant books
def format_books_for_llm(books):
    formatted_books = []
    for book in books:
        formatted_books.append(
            f"Title: {book['title']}, "
            f"Authors: {', '.join(book['authors'])}, "
            f"Description: {book.get('shortDescription', '')}")

    return "\n".join(formatted_books)
