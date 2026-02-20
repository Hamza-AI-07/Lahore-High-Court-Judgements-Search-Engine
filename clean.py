import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Ensure nltk resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

stop_words = set(stopwords.words('english'))

def clean_text(text):
    if not text:
        return []
    
    # Lowercase
    text = text.lower()
    
    # Remove special characters/numbers if needed (optional based on summary)
    # Keeping numbers might be useful for case numbers, years, etc.
    # But usually for search we want clean words.
    # Let's keep alphanumeric but remove punctuation.
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Tokenize
    tokens = word_tokenize(text)
    
    # Filter
    cleaned_tokens = []
    for token in tokens:
        if token in stop_words:
            continue
        if len(token) < 2: # Min token length
            continue
        if token.isdigit(): # Optional number handling - user said "optional number handling"
            # Let's keep numbers for now as they are often important in legal docs (sections, years)
            pass
        
        cleaned_tokens.append(token)
        
    return cleaned_tokens

if __name__ == "__main__":
    # Test
    sample = "Judgment of 2023. The court rules in favor of the plaintiff."
    print(clean_text(sample))
