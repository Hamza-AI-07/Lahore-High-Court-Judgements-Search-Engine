
import unittest
from query import QueryProcessor
import os
import shutil
import json
import gzip

class TestPhraseQuery(unittest.TestCase):
    def setUp(self):
        # Create a temporary index directory
        self.test_dir = "test_data_phrase"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Create dummy index
        # Doc1: "apple banana orange" -> positions: apple:0, banana:1, orange:2
        # Doc2: "apple orange banana" -> positions: apple:0, orange:1, banana:2
        # Doc3: "banana apple" -> positions: banana:0, apple:1
        
        positional_index = {
            "apple": {"doc1": [0], "doc2": [0], "doc3": [1]},
            "banana": {"doc1": [1], "doc2": [2], "doc3": [0]},
            "orange": {"doc1": [2], "doc2": [1]}
        }
        
        # Save index
        with gzip.open(os.path.join(self.test_dir, "positional_index.json.gz"), "wt") as f:
            json.dump(positional_index, f)
            
        # Save vocab
        with open(os.path.join(self.test_dir, "vocab.txt"), "w") as f:
            f.write("apple\nbanana\norange\n")
            
        # Save corpus (needed for QueryProcessor init although we won't use it for search result display)
        with open(os.path.join(self.test_dir, "corpus.jsonl"), "w") as f:
            f.write(json.dumps({"id": "doc1", "text": "apple banana orange"}) + "\n")
            f.write(json.dumps({"id": "doc2", "text": "apple orange banana"}) + "\n")
            f.write(json.dumps({"id": "doc3", "text": "banana apple"}) + "\n")

        # Save preprocess (needed for ranking load_data)
        with open(os.path.join(self.test_dir, "preprocess.json"), "w") as f:
            json.dump({
                "doc1": ["apple", "banana", "orange"],
                "doc2": ["apple", "orange", "banana"],
                "doc3": ["banana", "apple"]
            }, f)

        self.qp = QueryProcessor(index_dir=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_phrase_apple_banana(self):
        # "apple banana" should match doc1 only
        # doc1: apple(0), banana(1) -> adjacent
        # doc2: apple(0), banana(2) -> not adjacent
        # doc3: apple(1), banana(0) -> reverse order
        
        # We test get_phrase_postings directly
        postings = self.qp.get_phrase_postings(["apple", "banana"])
        self.assertIn("doc1", postings)
        self.assertNotIn("doc2", postings)
        self.assertNotIn("doc3", postings)

    def test_phrase_apple_orange(self):
        # "apple orange" should match doc2
        postings = self.qp.get_phrase_postings(["apple", "orange"])
        self.assertIn("doc2", postings)
        self.assertNotIn("doc1", postings) # doc1 is apple banana orange (apple(0), orange(2)) - gap of 1

    def test_query_parsing(self):
        # Test full query processing
        results, terms = self.qp.process_query('"apple banana"')
        doc_ids = [r['id'] for r in results]
        self.assertIn("doc1", doc_ids)
        self.assertNotIn("doc2", doc_ids)
        
        # Test "banana apple"
        results, terms = self.qp.process_query('"banana apple"')
        doc_ids = [r['id'] for r in results]
        self.assertIn("doc3", doc_ids)

if __name__ == '__main__':
    unittest.main()
