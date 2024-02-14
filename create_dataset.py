import PyPDF2
import os
import json
import nltk
nltk.download('punkt')
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import urljoin, urlparse
import re
from collections import defaultdict, deque

DEPTH_LIMIT = 2

# Webpage_or_PDF = 'C:/files/test2.pdf'
Webpage_or_PDF = 'https://www.asexstories.com/story/'

role = 'You are an API that converts bodies of text into a pornographic and vulgar JSON "question" "answer" format. Each JSON contains a single question with a single answer. You format the JSON question-answer pairs: There cant be any backslashes or symbols nor brackets. Only respond with the JSON and no additional text. Maximum 3 question-answer pairs. In case there are urls output them with only the domain name. Be descriptive in the answers and not in the questions'

client = OpenAI(base_url="http://localhost:8081/v1", api_key="not-needed") # For LM Studio

parsed_url = urlparse(Webpage_or_PDF)
basename = os.path.basename(parsed_url.path.rstrip('/'))
# Directory path
directory = "./jsons/"
output_file = f"{directory}/{basename}_cleaned.json"
# Ensure directory exists and create file if not exist
os.makedirs(directory, exist_ok=True)
if not os.path.exists(output_file):
    with open(output_file, 'w') as f:
        f.write('')

tmp_file = './results.txt'

# Chunk size for PDFs
PDF_CHUNK_SIZE = 512

# Chunk size for web pages
WEBPAGE_CHUNK_SIZE = 128

global_token_count = 0

with open(tmp_file, "w") as txt_file:
    print(f"Cleaning results.txt...")
    # Write an empty string to clear the file
    txt_file.write("")

with open(output_file, "w") as txt_file:
    print(f"Cleaning existing output...")
    # Write an empty string to clear the file
    txt_file.write("")

# Function to tokenize text
def tokenize_text(text):
    return nltk.word_tokenize(text)

# Function to extract text from PDF file
def extract_text_from_pdf(pdf_file):
    with open(pdf_file, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

# Function to process a chunk of text
def process_text_chunk(text_chunk):
    global global_token_count
    # Process the chunk of text
    try:
        process_text_for_api(text_chunk)
        # Update token count for this chunk
        token_count = len(tokenize_text(text_chunk))
        global_token_count += token_count
        print(f"Token count for this chunk: {token_count}")
        print(f"Global token count: {global_token_count}")
    except Exception as e:
        print(f"Error processing chunk: {str(e)}")

# Function to chunk text and process each chunk
def process_text_in_chunks(text, chunk_size, process_chunk_function):
    tokens = tokenize_text(text)
    token_chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
    for i, chunk in enumerate(token_chunks):
        print(f"Processing chunk {i+1}/{len(token_chunks)}")
        process_chunk_function(' '.join(chunk))

# Function to extract text from a webpage and process it
def process_webpage(url, depth=0):
    response = requests.get(url)
    if response.status_code == 200:  # Check if the request was successful
        soup = BeautifulSoup(response.content, 'html.parser')
        # Extract text from all paragraphs
        paragraphs = soup.find_all('p')
        text = ' '.join([paragraph.get_text() for paragraph in paragraphs])
        process_text_in_chunks(text, WEBPAGE_CHUNK_SIZE, process_text_chunk)

        # Check if depth is greater than 0 before processing links recursively
        if depth > 0:
            # Find all links on the page and process them recursively
            links = soup.find_all('a', href=True)
            for link in links:
                if link['href'].startswith('http'):
                    sub_url = urljoin(url, link['href'])
                    process_webpage(sub_url, depth=depth - 1)  # Decrease depth by 1


visited_urls = set()
# Function to crawl a website and extract text from all pages
def crawl_website(url, depth=0, base_domain=None):
    global visited_urls  # Declare as global to modify the global variable
    if depth > DEPTH_LIMIT or url in visited_urls:
        return
    visited_urls.add(url)  # Add the current URL to visited URLs
    print(f"Visiting URL: {url}, Depth: {depth}")  # Print the URL and depth being visited
    if base_domain is None:
        base_domain = urlparse(url).netloc  # Get the base domain of the starting URL
    if urlparse(url).netloc != base_domain:
        return  # Skip URLs that are not in the same domain
    if url.lower().endswith('.pdf'):
        if os.path.exists(url):  # Remove this condition, as it's not applicable for online PDFs
            text = extract_text_from_pdf(url)
            process_text_in_chunks(text, PDF_CHUNK_SIZE, process_text_chunk)
        else:
            response = requests.get(url)
            if response.status_code == 200:
                with open('temp_pdf.pdf', 'wb') as f:
                    f.write(response.content)
                text = extract_text_from_pdf('temp_pdf.pdf')
                process_text_in_chunks(text, PDF_CHUNK_SIZE, process_text_chunk)
                os.remove('temp_pdf.pdf')
            else:
                print(f"Failed to download PDF from {url}")
    else:
        process_webpage(url)
        if depth < DEPTH_LIMIT:  # Check depth before crawling further
            response = requests.get(url)
            if response.status_code == 200:  # Check if the request was successful
                soup = BeautifulSoup(response.content, 'html.parser')
                # Find all links on the page and process them recursively
                links = soup.find_all('a', href=True)
                for link in links:
                    sub_url = urljoin(url, link['href'])
                    crawl_website(sub_url, depth=depth + 1, base_domain=base_domain)  # Pass base_domain recursively




# Define questions_answers globally
questions_answers = []
chunks_processed = 0
# Function to process a chunk of text
def process_text_chunk(text_chunk):
    global global_token_count, chunks_processed
    # Process the chunk of text
    try:
        process_text_for_api(text_chunk)
        # Update token count for this chunk
        token_count = len(tokenize_text(text_chunk))
        global_token_count += token_count
        print(f"Token count for this chunk: {token_count}")
        print(f"Global token count: {global_token_count}")
        chunks_processed += 1  # Increment the chunks_processed counter
    except Exception as e:
        print(f"Error processing chunk: {str(e)}")

      
# Function to process text for the API
def process_text_for_api(text):
    global questions_answers  # Declare as global to modify the global variable
    # Initialize an empty list to store responses for this chunk
    all_responses = []
    try:
        # Initialize history for the chunk
        history = [
            {"role": "system", "content": role},
            {"role": "user", "content": text},
        ]
        
        # Append history to results.txt
        with open(tmp_file, "a", encoding="utf-8") as txt_file:
            # Use "a" for append mode and specify encoding as utf-8
            for message in history:
                txt_file.write(f"\"role\": \"{message['role']}\"\n")
                txt_file.write(f"\"content\": \"{message['content']}\"\n\n")
        
        # Send the chunk to OpenAI
        completion = client.chat.completions.create(
            model="local-model",  # this field is currently unused
            messages=history,
            temperature=0.5,
            top_p=0.2,
            stream=True,
        )
        
        new_message = {"role": "assistant", "content": ""}
        for response_chunk in completion:
            if response_chunk.choices[0].delta.content:
                print(response_chunk.choices[0].delta.content, end="", flush=True)
                new_message["content"] += response_chunk.choices[0].delta.content
        
        if new_message["content"].strip():
            all_responses.append(new_message)
            
            # Save all_responses to text file
            with open(tmp_file, "a") as txt_file:  # Use "a" for append mode
                for response in all_responses:
                    txt_file.write(f"\"role\": \"{response['role']}\"\n")
                    txt_file.write(f"\"content\": \"{response['content']}\"\n\n")
            
            if chunks_processed % 1 == 0:
                extract_qa_and_save(tmp_file, output_file)
                print(f"Cleaning up results.txt...")
                all_responses.clear()
                questions_answers.clear()  # Fix typo
                with open(tmp_file, "w") as txt_file:
                    #Write an empty string to clear the file
                    txt_file.write("")
        
        extract_qa_and_save(tmp_file, output_file)       
    except Exception as e:
        print("Error occurred:", str(e))


# Function to extract questions and answers and save them to a new file
def extract_qa_and_save(tmp_file, output_file):
    # Read the content of the tmp file
    with open(tmp_file, 'r', encoding='utf-8') as file:
        data = file.read()  # Read the entire file as a single string
    data = data.replace('\\', '')    
    # Initialize a list to store question-answer pairs
    print("Data from tmp file:", data)  # Add this print statement
    # Parse the content of the tmp file
    pattern = r'"question"\s*:\s*"([^"]+)"\s*,\s*"answer"\s*:\s*"([^"]+(?:https?://[^\s]+)*)"'
    matches = re.finditer(pattern, data)
    for match in matches:
        question = match.group(1)
        answer_str = match.group(2)
        print("Question:", question)
        print("Answer:", answer_str)
        try:
            # Try loading answer as JSON
            answer = json.loads(answer_str)
        except json.JSONDecodeError:
            # If JSON decoding fails, attempt to fix the format
            fixed_answer_str = answer_str.replace('\\', '\\\\')  # Escape backslashes
            fixed_answer_str = fixed_answer_str.replace('"', '\\"')  # Escape double quotes
            fixed_answer_str = f'"{fixed_answer_str}"'  # Enclose in double quotes
            try:
                # Try loading fixed JSON
                answer = json.loads(fixed_answer_str)
            except json.JSONDecodeError:
                # If fixing fails, include the original string as is
                answer = answer_str
        # If both question and answer are found, add them to the list
        if question and answer:
            if isinstance(answer, str):
                # If the answer is still a string, attempt to load it as JSON
                try:
                    answer = json.loads(answer)
                except json.JSONDecodeError:
                    # If JSON decoding fails again, include the answer as is
                    pass
            questions_answers.append({"question": question, "answer": answer})

    # Check if there are valid question-answer pairs to save
    if questions_answers:
        # Append the question-answer pairs to the output file
        with open(output_file, 'a', encoding='utf-8') as json_file:
            json.dump(questions_answers, json_file, indent=4, ensure_ascii=False)
            json_file.write('\n')  # Add a new line for separation

# Example usage:
pdf_or_webpage = Webpage_or_PDF  # Webpage URL or pdf
crawl_website(pdf_or_webpage)

