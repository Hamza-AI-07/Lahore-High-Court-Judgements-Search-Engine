import os
import glob
import json
import gzip
from tqdm import tqdm
from clean import clean_text

EXTRACTED_DIR = r"data/extracted"
INDEX_DIR = r"data/index"

def build_index():
    if not os.path.exists(INDEX_DIR):
        os.makedirs(INDEX_DIR)

    txt_files = glob.glob(os.path.join(EXTRACTED_DIR, "*.txt"))
    
    corpus_path = os.path.join(INDEX_DIR, "corpus.jsonl")
    preprocess_path = os.path.join(INDEX_DIR, "preprocess.json")
    index_path = os.path.join(INDEX_DIR, "positional_index.json.gz")
    vocab_path = os.path.join(INDEX_DIR, "vocab.txt")

    preprocess_data = {}
    positional_index = {}
    vocab = set()

    print("Building corpus and processing text...")
    with open(corpus_path, "w", encoding="utf-8") as f_corpus:
        for txt_file in tqdm(txt_files):
            filename = os.path.basename(txt_file)
            doc_id = os.path.splitext(filename)[0]
            
            with open(txt_file, "r", encoding="utf-8") as f:
                text = f.read()
            
            # Save to corpus
            doc_obj = {
                "id": doc_id,
                "path": txt_file,
                "text": text # Storing full text for retrieval display
            }
            f_corpus.write(json.dumps(doc_obj) + "\n")

            # Preprocess
            tokens = clean_text(text)
            preprocess_data[doc_id] = tokens
            
            # Update Index
            for pos, term in enumerate(tokens):
                vocab.add(term)
                if term not in positional_index:
                    positional_index[term] = {}
                if doc_id not in positional_index[term]:
                    positional_index[term][doc_id] = []
                positional_index[term][doc_id].append(pos)

    print("Saving artifacts...")
    
    # Save preprocess.json
    with open(preprocess_path, "w", encoding="utf-8") as f:
        json.dump(preprocess_data, f)
        
    # Save positional index (compressed)
    with gzip.open(index_path, "wt", encoding="utf-8") as f:
        json.dump(positional_index, f)

    # Save vocab
    with open(vocab_path, "w", encoding="utf-8") as f:
        for term in sorted(list(vocab)):
            f.write(term + "\n")

    print("Indexing complete.")

if __name__ == "__main__":
    build_index()
