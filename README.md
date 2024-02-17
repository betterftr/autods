# Auto DS
**Automatic Dataset creation tool for LLM's in python**

OpenAI API compatible simple python file to automatically create JSON datasets for LLM's from local or remote .pdf files or from webpages (with some basic crawl functionality).

Set up a local or remote model (like Oogabooga or LM studio) and let the LLM do the rest.

Usage:

Edit client:
>example
`client = OpenAI(base_url="http://localhost:8081/v1", api_key="not-needed") # This for example is for LM Studio`

Change mode:
>Image mode needs some work still because it has issues with well hidden nested wraps, but for a lot of sites it works (default behaviour is to save the assistant's response as .txt with the same names as the images)

>DATASET_MODE = False/True

>IMAGE_CAPTION_MODE = False/True

Edit your instruction:
>example
`system_message = 'You are an API that converts bodies of text into JSON "question" "answer" format. Each JSON contains a single question with a single answer. You format the JSON question-answer pairs: There cant be any backslashes or symbols nor brackets. Only respond with the JSON and no additional text. Maximum 3 question-answer pairs. In case there are urls output them with only the domain name. Be descriptive in the answers and not in the questions'`

Edit prompt template to fit your model:
>example
`assistant_message = '### Response: '`

Edit Chunk sizes:
>example
`PDF_CHUNK_SIZE = 512
WEBPAGE_CHUNK_SIZE = 128`

Customize processing:
>select_by_CSS_SELECTOR = [] # Example: ["a[href*='/pin/']"]. Select content by selenium css selector to process. Leave it empty to process everything on page: like so '[]'
>
>select_by_TAG_NAME = ['h1'] # Example: ['a', 'h1']. Select content by selenium tag selector on the pages to process. Leave it empty to process everything on page: like so '[]'
>
>classes_to_crawl = ['.rel-link'] # Example: ['.rel-link', '.story-short-title']. Url crawling restriction to certain classes. Leave it empty to crawl everything on the page for urls: like so '[]'
>
>image_div_name = 'a' # check html source, excamples: if your images is located <img, then you input 'img'; if <a, then 'a'
>
>images_to_download = ['cdni.pornpics.com/1280'] # Partial image url in to look for
>
>depth_limit_0/1/2_scrolling = False/True





Tested with:
>LM Studio + `mistral-7b-instruct-v0.2.Q4_0.gguf`

Working:

![1](https://github.com/betterftr/autods/assets/84087448/a6c97232-cb37-4684-a4ca-e48957bd7e13)


Example output in DATASET:

![2](https://github.com/betterftr/autods/assets/84087448/630a6538-763c-40d9-9e79-131d63300d47)

Note: For JSON keys other than "question" and "answer", just edit the files and replace them with whatever you want
