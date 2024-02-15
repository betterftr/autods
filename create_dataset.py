import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# List of dependencies
dependencies = ['PyPDF2', 'nltk', 'requests', 'bs4', 'openai']

# Check and install dependencies if not already installed
for dependency in dependencies:
    try:
        __import__(dependency)
    except ImportError:
        print(f"{dependency} is not installed. Installing...")
        install(dependency)

# Additional setup for nltk
try:
    import nltk
    nltk.data.find('punkt')
except LookupError:
    print("Downloading NLTK data...")
    nltk.download('punkt')

import PyPDF2
import os
import time
import json
import nltk
import requests
from bs4 import BeautifulSoup, Tag
from openai import OpenAI
from urllib.parse import urljoin, urlparse
import re
from collections import defaultdict, deque
from combine_dataset import main

# Webpage_or_PDF = 'C:/files/test2.pdf'
Webpage_or_PDF = 'https://www.somewebsite.com/'

#Prompt stuff, include your models needs like ### Instruction: ### Response:
system_message = 'You are an API that converts bodies of text into JSON. Json pairs format: "question" and "answer" lowercase. Each JSON contains a single question with a single answer. There cant be any backslashes or symbols nor brackets. Only respond with the JSON. Maximum 3 "question" "answer" pairs. In case there are urls output them with only the domain name. Be descriptive and truthful to original wording in the answers and short with the questions.'
user_message = ''
assistant_message = ''

client = OpenAI(base_url="http://localhost:8081/v1", api_key="not-needed") # For LM Studio

parsed_url = urlparse(Webpage_or_PDF)
basename = os.path.basename(parsed_url.path.rstrip('/'))
# Directory path
directory = "./jsons/"
output_file = f"{directory}/{basename}_cleaned.json"
# Ensure directory exists and create file if not exist
os.makedirs(directory, exist_ok=True)
if not os.path.exists(output_file):
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write('')

tmp_file = './tmp.txt'

# Chunk size for PDFs
PDF_CHUNK_SIZE = 512

# Chunk size for web pages
WEBPAGE_CHUNK_SIZE = 128

# Global variables
DEPTH_LIMIT = 2
global_token_count = 0
questions_answers = []
chunks_processed = 0
existing_pairs = set()
unique_qa_pairs = set()
visited_urls = set()


with open(tmp_file, "w", encoding="utf-8") as txt_file:
    print(f"Cleaning tmp.txt...")
    # Write an empty string to clear the file
    txt_file.write("")

with open(output_file, "w", encoding="utf-8") as txt_file:
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


# Function to chunk text and process each chunk
def process_text_in_chunks(text, chunk_size, process_text_chunk):
    tokens = tokenize_text(text)
    token_chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
    for i, chunk in enumerate(token_chunks):
        print(f"Processing chunk {i+1}/{len(token_chunks)}")
        process_text_chunk(' '.join(chunk))

# Function to process a chunk of text
def process_text_chunk(text_chunk):
    global global_token_count, chunks_processed
    try:
        process_text_for_api(text_chunk)
        token_count = len(tokenize_text(text_chunk))
        global_token_count += token_count
        print(f"Token count for this chunk: {token_count}")
        print(f"Global token count: {global_token_count}")
        chunks_processed += 1
    except Exception as e:
        print(f"Error processing chunk: {str(e)}")

# Function to extract text from a webpage and process it
def process_webpage(url, depth=0):
    response = requests.get(url)
    if response.status_code == 200:  # Check if the request was successful
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = ' '.join([paragraph.get_text() for paragraph in paragraphs])
        process_text_in_chunks(text, WEBPAGE_CHUNK_SIZE, process_text_chunk)
        if depth > 0:
            links = soup.find_all('a', href=True)
            for link in links:
                if link['href'].startswith('http'):
                    sub_url = urljoin(url, link['href'])
                    process_webpage(sub_url, depth=depth - 1)


# Function to crawl a website and extract text from all pages
def crawl_website(url, depth=0, base_domain=None):
    global visited_urls
    if depth > DEPTH_LIMIT or url in visited_urls:
        return
    visited_urls.add(url)
    print(f"Visiting URL: {url}, Depth: {depth}")
    if base_domain is None:
        base_domain = urlparse(url).netloc
    if urlparse(url).netloc != base_domain:
        return
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
        if depth < DEPTH_LIMIT:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    sub_url = urljoin(url, link['href'])
                    crawl_website(sub_url, depth=depth + 1, base_domain=base_domain)


      
# Function to process text for the API
def process_text_for_api(text):
    global questions_answers  # Declare as global to modify the global variable
    # Initialize an empty list to store responses for this chunk
    all_responses = []
    try:
        # Initialize history for the chunk
        history = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message + text},
        ]
        
        # Append history to tmp.txt
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
        
        new_message = {"role": "assistant", "content": assistant_message}
        for response_chunk in completion:
            if response_chunk.choices[0].delta.content:
                print(response_chunk.choices[0].delta.content, end="", flush=True)
                new_message["content"] += response_chunk.choices[0].delta.content
        
        if new_message["content"].strip():
            all_responses.append(new_message)
            
            # Save all_responses to text file
            with open(tmp_file, "a", encoding="utf-8") as txt_file:  # Use "a" for append mode
                for response in all_responses:
                    txt_file.write(f"\"role\": \"{response['role']}\"\n")
                    txt_file.write(f"\"content\": \"{response['content']}\"\n\n")
                    

            if chunks_processed % 2 == 0:
                all_responses.clear()
                questions_answers.clear()
                existing_pairs.clear()
                unique_qa_pairs.clear()
                extract_qa_and_save(tmp_file, output_file)
                with open(tmp_file, "w", encoding="utf-8") as txt_file:
                    print(f"Cleaning tmp.txt...")
                    # Write an empty string to clear the file
                    txt_file.write("")
                main()
                
        
        extract_qa_and_save(tmp_file, output_file)       
    except Exception as e:
        print("Error occurred:", str(e))


# Function to extract questions and answers and save them to a new file
def extract_qa_and_save(tmp_file, output_file):
    try:

        
        # Parse the content of the tmp file
        with open(tmp_file, 'r', encoding='utf-8') as file:
            data = file.read()  # Read the entire file as a single string
            data = data.replace('\\', '') 
            # Define the pattern to extract question-answer pairs
            pattern = r'"question"\s*:\s*"([^"]+)"\s*,\s*"answer"\s*:\s*"([^"]+(?:https?://[^\s]+)*)"'
            matches = re.findall(pattern, data)

            # Iterate over matches and add them to unique_qa_pairs set
            for match in matches:
                question = match[0].strip()  # Strip to remove any leading/trailing spaces
                answer = match[1].strip()
                unique_qa_pairs.add((question, answer))

        # Read existing content of the output file to avoid duplicates

        try:
            with open(output_file, 'r', encoding='utf-8') as json_file:
                for line in json_file:
                    try:
                        qa_pair = json.loads(line)
                        existing_pairs.add((qa_pair["question"], qa_pair["answer"]))
                    except json.JSONDecodeError:
                        print("Error decoding JSON:", line)  # Log the line causing the error
                        pass  # If JSON decoding fails, skip this line
        except FileNotFoundError:
            pass  # If the file doesn't exist yet, no need to worry about duplicates
            
        # Append only unique question-answer pairs to the output file
        with open(output_file, 'a', encoding='utf-8') as json_file:
            for question, answer in unique_qa_pairs:
                if (question, answer) not in existing_pairs:
                    json.dump({"question": question, "answer": answer}, json_file, ensure_ascii=False)
                    json_file.write('\n')  # Add a new line for separation
    except Exception as e:
        print("Error occurred during extraction:", str(e))

# Example usage:
pdf_or_webpage = Webpage_or_PDF  # Webpage URL or pdf
crawl_website(pdf_or_webpage)
