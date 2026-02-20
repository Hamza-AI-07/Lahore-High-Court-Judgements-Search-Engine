import json
import gzip
import math
import os
from collections import defaultdict, Counter

class TFIDFRanker:
    def __init__(self, index_dir="data/index"):
        self.index_dir = index_dir
        self.index_path = os.path.join(index_dir, "positional_index.json.gz")
        self.preprocess_path = os.path.join(index_dir, "preprocess.json")
        
        self.index = {}
        self.doc_lengths = {} # Number of tokens per doc
        self.doc_norms = {} # L2 norm of document vectors
        self.N = 0
        self.idf = {}
        
        self.load_data()

    def load_data(self):
        print("Loading index for ranking...")
        with gzip.open(self.index_path, "rt", encoding="utf-8") as f:
            self.index = json.load(f)
            
        with open(self.preprocess_path, "r", encoding="utf-8") as f:
            preprocess_data = json.load(f)
            self.N = len(preprocess_data)
        
        # Compute IDF
        print("Computing IDF...")
        for term, doc_dict in self.index.items():
            df = len(doc_dict)
            self.idf[term] = math.log10(self.N / df) if df > 0 else 0

        # Compute Document Norms
        print("Computing Document Norms...")
        for doc_id, tokens in preprocess_data.items():
            self.doc_lengths[doc_id] = len(tokens)
            
            # Compute term frequencies
            tf_counts = Counter(tokens)
            norm_sq = 0
            for term, count in tf_counts.items():
                if term in self.idf:
                    w_td = (1 + math.log10(count)) * self.idf[term]
                    norm_sq += w_td ** 2
            self.doc_norms[doc_id] = math.sqrt(norm_sq)

    def score(self, query_terms, candidate_docs, use_cosine=False):
        # query_terms: list of terms in query
        # candidate_docs: set of doc_ids to score
        
        scores = defaultdict(float)
        
        # Query TF-IDF
        query_counts = defaultdict(int)
        for t in query_terms:
            query_counts[t] += 1
            
        query_vec_len = 0
        for t, count in query_counts.items():
            if t in self.idf:
                w_tq = (1 + math.log10(count)) * self.idf[t]
                query_vec_len += w_tq ** 2
            else:
                w_tq = 0
                
        query_vec_len = math.sqrt(query_vec_len)

        for doc_id in candidate_docs:
            dot_product = 0
            
            for t in query_terms:
                if t in self.index and doc_id in self.index[t]:
                    # TF in doc
                    tf_d = len(self.index[t][doc_id])
                    # Log normalization
                    w_td = (1 + math.log10(tf_d)) * self.idf[t]
                    
                    # Weight in query
                    q_tf = query_counts[t]
                    w_tq = (1 + math.log10(q_tf)) * self.idf[t]
                    
                    dot_product += w_td * w_tq
            
            if use_cosine:
                doc_norm = self.doc_norms.get(doc_id, 0)
                if doc_norm > 0 and query_vec_len > 0:
                    scores[doc_id] = dot_product / (doc_norm * query_vec_len)
                else:
                    scores[doc_id] = 0
            else:
                scores[doc_id] = dot_product

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked
