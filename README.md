# Auto DS
**Automatic Dataset creation tool for LLM's in python**

OpenAI API compatible simple python file to automatically create JSON datasets for LLM's from local or remote .pdf files or from webpages (with some basic crawl functionality).

Set up a local or remote model (like Oogabooga or LM studio) and let the LLM do the rest.

Usage:

Edit client:
>example
`client = OpenAI(base_url="http://localhost:8081/v1", api_key="not-needed") # This for example is for LM Studio`

Edit your instruction:
>example
`user_message = 'You are an API that converts bodies of text into JSON "question" "answer" format. Each JSON contains a single question with a single answer. You format the JSON question-answer pairs: There cant be any backslashes or symbols nor brackets. Only respond with the JSON and no additional text. Maximum 3 question-answer pairs. In case there are urls output them with only the domain name. Be descriptive in the answers and not in the questions'`

Edit prompt template to fit your model:
>example
`assistant_message = '### Response: '`

Edit Chunk sizes:
>example
`PDF_CHUNK_SIZE = 512
WEBPAGE_CHUNK_SIZE = 128`

Tested with:
>LM Studio + `mistral-7b-instruct-v0.2.Q4_0.gguf`



Working:

![1](https://github.com/betterftr/autods/assets/84087448/a6c97232-cb37-4684-a4ca-e48957bd7e13)


Example output in DATASET:

![2](https://github.com/betterftr/autods/assets/84087448/630a6538-763c-40d9-9e79-131d63300d47)

