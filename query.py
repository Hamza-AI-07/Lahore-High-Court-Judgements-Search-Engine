import json
import gzip
import re
import os
import fnmatch
import difflib
from clean import clean_text
from tfidf import TFIDFRanker

class QueryProcessor:
    def __init__(self, index_dir="data/index"):
        self.index_dir = index_dir
        self.ranker = TFIDFRanker(index_dir)
        self.index = self.ranker.index
        self.vocab = list(self.index.keys())
        
        # Load corpus for snippets (optional, maybe just paths)
        self.corpus = {}
        with open(os.path.join(index_dir, "corpus.jsonl"), "r", encoding="utf-8") as f:
            for line in f:
                doc = json.loads(line)
                self.corpus[doc['id']] = doc

    def correct_term(self, term):
        """
        Corrects a single term using the vocabulary.
        """
        # Don't correct if wildcard
        if '*' in term:
            return term
        
        # Don't correct if operator
        if term.upper() in ('AND', 'OR', 'NOT'):
            return term
            
        # Clean term to match vocab format (lowercase, no punctuation)
        ct = clean_text(term)
        if not ct:
            return term # Stopword or empty, return as is
        
        # We assume the term maps to the first token if multiple (unlikely for single word)
        clean_t = ct[0]
        
        if clean_t in self.index:
            return term # It's a valid word in vocab
            
        # Try to find match
        # cutoff=0.7 means 70% similarity required.
        matches = difflib.get_close_matches(clean_t, self.vocab, n=1, cutoff=0.7)
        if matches:
            return matches[0] # Return the corrected lowercase term
        
        return term

    def get_term_suggestions(self, term, n=5):
        """
        Returns a list of spelling suggestions for a term.
        """
        if '*' in term or term.upper() in ('AND', 'OR', 'NOT'):
            return []
            
        ct = clean_text(term)
        if not ct:
            return []
            
        clean_t = ct[0]
        if clean_t in self.index:
            return [] # Correctly spelled
            
        return difflib.get_close_matches(clean_t, self.vocab, n=n, cutoff=0.6)

    def analyze_query_spelling(self, query_str):
        """
        Returns a dictionary of {misspelled_term: [suggestions]}.
        """
        if not query_str:
            return {}
            
        tokens = re.findall(r'\(|\)|"[^"]+"|\S+', query_str)
        suggestions = {}
        
        for t in tokens:
            if t in ('(', ')') or t.startswith('"'):
                continue
                
            suggs = self.get_term_suggestions(t)
            if suggs:
                suggestions[t] = suggs
                
        return suggestions

    def correct_query(self, query_str):
        """
        Parses the query and applies spelling correction to terms.
        Returns the corrected query string.
        """
        if not query_str:
            return query_str

        # Tokenize preserving quotes and parens
        tokens = re.findall(r'\(|\)|"[^"]+"|\S+', query_str)
        corrected_tokens = []
        
        for t in tokens:
            if t in ('(', ')') or t.startswith('"'):
                corrected_tokens.append(t)
                continue
            
            # It's a term or operator
            corrected = self.correct_term(t)
            corrected_tokens.append(corrected)
            
        return " ".join(corrected_tokens)

    def expand_wildcard(self, term):
        if '*' not in term:
            return [term]
        # Regex matching for wildcard
        pattern = fnmatch.translate(term)
        regex = re.compile(pattern)
        matches = [w for w in self.vocab if regex.match(w)]
        return matches

    def get_postings(self, term):
        # Handle wildcards (assuming caller handled enable_wildcards check or passed raw term)
        if '*' in term:
            expanded = self.expand_wildcard(term)
            result = set()
            for t in expanded:
                if t in self.index:
                    result.update(self.index[t].keys())
            return result
        
        if term in self.index:
            return set(self.index[term].keys())
        return set()

    def get_phrase_postings(self, phrase_tokens):
        if not phrase_tokens:
            return set()
        
        # Intersection of docs
        docs = self.get_postings(phrase_tokens[0])
        for token in phrase_tokens[1:]:
            docs &= self.get_postings(token)
            
        # Check positions
        final_docs = set()
        for doc_id in docs:
            # Check if tokens are adjacent
            # We need the positions for each token in this doc
            # positions is list of list of positions
            positions = []
            valid_doc = True
            for token in phrase_tokens:
                if token not in self.index or doc_id not in self.index[token]:
                    valid_doc = False; break
                positions.append(self.index[token][doc_id])
            
            if not valid_doc: continue

            # Find if there is a sequence p1, p2, p3 such that p2=p1+1, p3=p2+1...
            # We can use a recursive check or iterative
            if self.has_sequence(positions):
                final_docs.add(doc_id)
        
        return final_docs

    def has_sequence(self, positions_list):
        # positions_list: [[1, 10], [2, 12], [3]] for phrase "A B C"
        # We need 1, 2, 3
        if not positions_list: return False
        
        current_positions = positions_list[0]
        for next_positions in positions_list[1:]:
            temp_positions = []
            for p in current_positions:
                if (p + 1) in next_positions:
                    temp_positions.append(p + 1)
            current_positions = temp_positions
            if not current_positions:
                return False
        return True

    def process_query(self, query_str, enable_ranking=True, use_cosine=False, enable_wildcards=True):
        # Tokenize preserving quotes
        tokens = re.findall(r'\(|\)|"[^"]+"|\S+', query_str)
        
        ranking_terms = []
        display_terms = []
        
        # Step 1: Parse into abstract tokens (TERM, PHRASE, OP)
        parsed = []
        for t in tokens:
            if t.upper() in ["AND", "OR", "NOT"]:
                parsed.append(("OP", t.upper()))
            elif t.startswith('"') and t.endswith('"'):
                content = t[1:-1]
                # Clean phrase content
                pt = clean_text(content)
                parsed.append(("PHRASE", pt))
                ranking_terms.extend(pt)
                display_terms.append(" ".join(pt))
            else:
                # Term or Wildcard
                if enable_wildcards and '*' in t:
                     parsed.append(("WILDCARD", t.lower()))
                     expanded = self.expand_wildcard(t.lower())
                     ranking_terms.extend(expanded)
                     display_terms.extend(expanded)
                else:
                    ct = clean_text(t)
                    if ct:
                        # If multiple tokens (e.g. "judge-made" -> "judge", "made"), add all
                        for term in ct:
                            parsed.append(("TERM", term))
                            ranking_terms.append(term)
                            display_terms.append(term)
        
        # Step 2: Evaluate Boolean
        if not parsed:
            return [], []

        current_docs = self.evaluate_atom(parsed[0])
        idx = 1
        
        while idx < len(parsed):
            item_type, item_val = parsed[idx]
            
            if item_type == "OP":
                op = item_val
                idx += 1
                if idx >= len(parsed): break
                next_atom = parsed[idx]
                next_docs = self.evaluate_atom(next_atom)
                
                if op == "AND":
                    current_docs &= next_docs
                elif op == "OR":
                    current_docs |= next_docs
                elif op == "NOT":
                    current_docs -= next_docs
            else:
                # Implicit AND
                next_docs = self.evaluate_atom((item_type, item_val))
                current_docs &= next_docs
            
            idx += 1
            
        # Step 3: Rank
        if enable_ranking:
            ranked_results = self.ranker.score(ranking_terms, current_docs, use_cosine=use_cosine)
        else:
            # No ranking, just return docs with 0 score (or 1.0)
            ranked_results = [(doc_id, 1.0) for doc_id in sorted(list(current_docs))]
        
        # Return enriched results
        output = []
        for doc_id, score in ranked_results:
            doc_info = self.corpus.get(doc_id, {})
            output.append({
                "id": doc_id,
                "score": score,
                "path": doc_info.get("path", ""),
                "snippet": doc_info.get("text", "")[:200] + "..." # simple snippet
            })
            
        return output, display_terms

    def evaluate_atom(self, atom):
        atype, aval = atom
        if atype == "TERM":
            return self.get_postings(aval)
        elif atype == "WILDCARD":
            return self.get_postings(aval)
        elif atype == "PHRASE":
            return self.get_phrase_postings(aval)
        return set()

if __name__ == "__main__":
    # Test
    pass
