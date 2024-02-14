import os
import json
import re

def extract_qa_pairs_from_file(file_path):
    pairs = []
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.readlines()
        for line in content:
            match = re.search(r'"question"\s*:\s*"([^"]+)"\s*,\s*"answer"\s*:\s*"([^"]+)"', line)
            if match:
                pairs.append((match.group(1), match.group(2)))
    return pairs

def extract_qa_pairs_from_folder(folder_path):
    qa_pairs = set()  # Using a set to store unique pairs
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            qa_pairs.update(extract_qa_pairs_from_file(file_path))
    return qa_pairs

def write_to_json(qa_pairs, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        formatted_qa_pairs = [{"question": q, "answer": a} for q, a in qa_pairs]
        json.dump(formatted_qa_pairs, file, indent=4, ensure_ascii=False)

def main():
    folder_path = "./jsons"
    output_file = "./DATASET.json"
    qa_pairs = extract_qa_pairs_from_folder(folder_path)
    write_to_json(qa_pairs, output_file)
    print("Conversion complete.")

if __name__ == "__main__":
    main()
