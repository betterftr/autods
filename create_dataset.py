import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# List of dependencies
dependencies = ['PyPDF2', 'nltk', 'requests', 'bs4', 'openai', 'transformers', 'sentencepiece', 'selenium']

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
import sentencepiece
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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException


# Webpage_or_PDF = './online_or_local.pdf'
Webpage_or_PDF = 'https://www.somewebsite.com/'

#Prompt stuff, include your models needs like ### Instruction: ### Response:
system_message = 'You are an API that converts bodies of text into JSON. Json pairs format: "question" and "answer" lowercase. Each JSON contains a single question with a single answer. There cant be any backslashes or symbols nor brackets. Only respond with the JSON. Maximum 3 "question" "answer" pairs. In case there are urls output them with only the domain name. Be descriptive and truthful to original wording in the answers and short with the questions.'
user_message = ''
assistant_message = ''

client = OpenAI(base_url="http://localhost:8081/v1", api_key="not-needed") # For LM Studio

directory = "./jsons/"
tmp_file = './tmp.txt'

# Chunk size for PDFs
PDF_CHUNK_SIZE = 512

# Chunk size for web pages
WEBPAGE_CHUNK_SIZE = 128

# limit on crawling websites
DEPTH_LIMIT = 1

# customize html processing and crawling
tags_to_process = ['h1'] # leave it empty to process (and send to the tokenizer) the content every tag on the page: like so '[]'
classes_to_crawl = ['.rel-link', '.story-short-title'] # leave it empty to crawl everything on the page for urls: like so '[]'

# Scroll settings
depth_limit_0_scrolling = True
depth_limit_1_scrolling = False
depth_limit_2_scrolling = False

# Global variables
global_token_count = 0
questions_answers = []
chunks_processed = 0
existing_pairs = set()
unique_qa_pairs = set()
visited_urls = set()
tab_stack = []

# tokenize text using nltk
def tokenize_text(text):
    return nltk.word_tokenize(text)

# tokenize text with transformers tokenizer
# from transformers import AutoTokenizer # If you want to use transformers tokenizer
# tokenizer = AutoTokenizer.from_pretrained('SnypzZz/Llama2-13b-Language-translate') # If you want to use transformers tokenizer
# def tokenize_text(text):
#     return tokenizer.tokenize(text)

parsed_url = urlparse(Webpage_or_PDF)
basename = os.path.basename(parsed_url.path.rstrip('/'))
# Directory path

output_file = f"{directory}/{basename}_cleaned.json"
# Ensure directory exists and create file if not exist
os.makedirs(directory, exist_ok=True)
if not os.path.exists(output_file):
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write('')

with open(tmp_file, "w", encoding="utf-8") as txt_file:
    print(f"Cleaning tmp.txt...")
    # Write an empty string to clear the file
    txt_file.write("")

with open(output_file, "w", encoding="utf-8") as txt_file:
    print(f"Cleaning existing output...")
    # Write an empty string to clear the file
    txt_file.write("")

######################
###Selenium Options###
######################
# Set up Selenium WebDriver
options = Options()
# block image loading
# options.experimental_options['prefs'] = {
#     'profile.managed_default_content_settings.images': 2,
#     'profile.managed_default_content_settings.javascript': 2
# }
# options.add_argument('--headless') # You can comment this out if you want to hide the browser, but it's not recommended
options.add_argument("--window-size=1280,720")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
options.add_argument("--disable-popup-blocking")  # Disable popup blocking
options.add_argument("--disable-extensions")  # Disable extensions
options.add_argument("--new-tab")
options.add_argument("--enable-chrome-browser-cloud-management")
driver = webdriver.Chrome(
options=options
)
######################
###Selenium Options###
######################

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
        # Ensure the text is encoded in UTF-8
        text_chunk = text_chunk.encode('utf-8', 'ignore').decode('utf-8')
        
        process_text_for_api(text_chunk)
        token_count = len(tokenize_text(text_chunk))
        global_token_count += token_count
        print(f"Token count for this chunk: {token_count}")
        print(f"Global token count: {global_token_count}")
        chunks_processed += 1
    except Exception as e:
        print(f"Error processing chunk: {str(e)}")

def open_webpage_in_new_tab(url, depth, driver):
    global tab_stack
    if depth <= DEPTH_LIMIT:
        # Get the current window handle (parent tab)
        parent_tab_handle = driver.current_window_handle
        
        driver.execute_script("window.open();")
        # Switch to the new tab
        new_window_handles = driver.window_handles
        new_tab_handle = new_window_handles[-1]
        driver.switch_to.window(new_tab_handle)
        # Push the new tab handle and parent tab handle onto the stack
        tab_stack.append((new_tab_handle, parent_tab_handle))
        # Wait for the page to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        # Process the webpage
        process_webpage(url, depth, driver)
        # Check for alerts
        try:
            alert = driver.switch_to.alert
            if alert is not None:
                alert.accept()
        except NoAlertPresentException:
            pass
        return new_tab_handle
    else:
        print("Depth limit reached. Not opening new tab.")
        return None

# Modify the switch_back_to_previous_tab function to handle NoSuchWindowException
def switch_back_to_previous_tab(driver):
    try:
        # Close the current tab
        driver.close()
        # Pop the tab handle and parent tab handle from the stack
        previous_tab_handle, parent_tab_handle = tab_stack.pop()
        # Switch back to the previous tab (parent tab)
        driver.switch_to.window(parent_tab_handle)
    except IndexError:
        print("No more tabs to switch back to.")
    except NoSuchWindowException:
        print("Previous window no longer exists.")


# Function to extract text from a webpage and process it
def process_webpage(url, depth=0, driver=None):
    print(f"Processing URL: {url}, Depth: {depth}")
    if driver is None:
        response = requests.get(url)
        if response.status_code == 200:  # Check if the request was successful
            soup = BeautifulSoup(response.content, 'html.parser')
            extract_and_process_content(soup, driver, depth)  # Pass the depth parameter
    else:
        driver.get(url)
        time.sleep(1)  # Wait for page to load (adjust as needed)
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        extract_and_process_content(driver, depth)  # Pass the depth parameter

# Function to crawl a website and extract text from all pages
def crawl_website(url, depth=0, base_domain=None, main_tab=True):
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
    if main_tab:
        process_webpage(url, depth, driver)
    else:
        new_tab_handle = open_webpage_in_new_tab(url, depth, driver)

    if depth < DEPTH_LIMIT:
        if not classes_to_crawl:
            # If classes_to_crawl is empty, crawl every element for new URLs
            links = driver.find_elements(By.XPATH, '//a[@href]')
            for link in links:
                sub_url = link.get_attribute('href')
                crawl_website(sub_url, depth=depth + 1, base_domain=base_domain, main_tab=False)
        else:
            # Find all links with classes specified in classes_to_crawl
            for class_name in classes_to_crawl:
                links = driver.find_elements(By.CSS_SELECTOR, class_name)
                for link in links:
                    try:
                        sub_url = link.get_attribute('href')
                        if sub_url:
                            crawl_website(sub_url, depth=depth + 1, base_domain=base_domain, main_tab=False)
                    except StaleElementReferenceException:
                        print("StaleElementReferenceException occurred. Skipping this link.")

    if not main_tab:
        switch_back_to_previous_tab(driver)  # Switch back to the main tab


# Function to scroll down a webpage using Selenium
def scroll_down(driver, depth, scroll_pause_time=1):
    global depth_limit_0_scrolling, depth_limit_1_scrolling, depth_limit_2_scrolling
    
    if depth == 0 and depth_limit_0_scrolling:
        # Scroll down only if depth is 0 and depth_limit_0_scrolling is True
        # Get current page height
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep(scroll_pause_time)
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    elif depth == 1 and depth_limit_1_scrolling:
        # Scroll down only if depth is 1 and depth_limit_1_scrolling is True
        # Get current page height
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep(scroll_pause_time)
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    elif depth == 2 and depth_limit_2_scrolling:
        # Scroll down only if depth is 2 and depth_limit_2_scrolling is True
        # Get current page height
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep(scroll_pause_time)
            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height


# Function to extract and process content
def extract_and_process_content(driver, depth):
    global tags_to_process
    if not tags_to_process:
        # Get all tags present on the webpage
        all_tags = driver.find_elements(By.XPATH, '//*')
        
        # Extract and process text content from each tag
        for tag in all_tags:
            text = tag.text.strip()  # Strip any leading or trailing whitespace
            if text:
                process_text_in_chunks(text, WEBPAGE_CHUNK_SIZE, process_text_chunk)
    else:
        # Define tags to extract and process
        tags_to_extract = [(tag, '') for tag in tags_to_process]  # Add more tags as needed

        for tag_name, text_variable in tags_to_extract:
            elements = driver.find_elements(By.TAG_NAME, tag_name)
            text = ' '.join([element.text for element in elements])
            process_text_in_chunks(text, WEBPAGE_CHUNK_SIZE, process_text_chunk)
    
    # Scroll down to load more content
    scroll_down(driver, depth)
        
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

# usage:
pdf_or_webpage = Webpage_or_PDF
crawl_website(pdf_or_webpage)
driver.quit()
