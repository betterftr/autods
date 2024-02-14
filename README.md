# Autods
**Automatic Dataset creation tool for LLM's in python**

OpenAI API compatible simple python file to automatically create JSON datasets for LLM's from local or remote .pdf files or from webpages (with some basic crawl functionality).

Usage:

Edit client:
>example
`client = OpenAI(base_url="http://localhost:8081/v1", api_key="not-needed") # This for example is for LM Studio`

Edit role:
>example
`role = 'You are an API that converts bodies of text into JSON "question" "answer" format. Each JSON contains a single question with a single answer. You format the JSON question-answer pairs: There cant be any backslashes or symbols nor brackets. Only respond with the JSON and no additional text. Maximum 3 question-answer pairs. In case there are urls output them with only the domain name. Be descriptive in the answers and not in the questions'`

Edit Chunk sizes:
>example
`PDF_CHUNK_SIZE = 512
WEBPAGE_CHUNK_SIZE = 128`

LLM used in my tests:
>mistral-7b-instruct-v0.2.Q4_0.gguf
