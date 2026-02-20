import re
from flask import Flask, render_template_string, request, send_from_directory
from query import QueryProcessor
import os

app = Flask(__name__)
qp = None

# Configuration for file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, 'data', 'pdfs')
TXT_DIR = os.path.join(BASE_DIR, 'data', 'extracted')

def highlight_text(text, terms):
    if not terms or not text:
        return text
    
    unique_terms = sorted(list(set([t.lower() for t in terms])), key=len, reverse=True)
    if not unique_terms:
        return text
        
    term_map = {t: i % 6 for i, t in enumerate(unique_terms)} # 6 colors
    
    # Create regex pattern
    patterns = []
    for t in unique_terms:
        if ' ' in t:
            # Phrase pattern: Replace spaces with \W+ (non-word characters)
            # This handles newlines, tabs, punctuation, etc.
            # E.g. "writ petition" -> "writ[\W_]+petition"
            parts = [re.escape(p) for p in t.split()]
            pat = r'\b' + r'[\W_]+'.join(parts) + r'\b'
            patterns.append(pat)
        else:
            patterns.append(r'\b' + re.escape(t) + r'\b')
    
    full_pattern = r'(' + '|'.join(patterns) + r')'
    pattern = re.compile(full_pattern, re.IGNORECASE)
    
    def replace_func(match):
        word = match.group(0)
        # For mapping, we need to match it back to the term.
        # This is tricky because "writ petition" matches "writ  petition".
        # We can try to find which pattern matched.
        
        # Simple heuristic: try to find matching term in unique_terms
        # Clean the match to see if it matches a term
        clean_match = " ".join([w.lower() for w in re.split(r'[\W_]+', word) if w])
        
        # If clean_match is in term_map, use it.
        # If not (maybe stopword diffs), fallback to first term or hash.
        idx = term_map.get(clean_match, 0)
        
        # Fallback: if not found, just use hash of lower word
        if clean_match not in term_map:
             # Try to find partial match or just random color
             idx = abs(hash(clean_match)) % 6
             
        return f'<span class="highlight term-{idx}">{word}</span>'
        
    return pattern.sub(replace_func, text)

VIEW_DOC_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>View Document - {{ doc_id }}</title>
    <style>
        body { font-family: 'Courier New', Courier, monospace; max-width: 1000px; margin: 0 auto; padding: 20px; line-height: 1.6; }
        .controls { position: fixed; top: 20px; right: 20px; background: white; padding: 10px; border: 1px solid #ccc; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .highlight { font-weight: bold; border-radius: 3px; padding: 0 2px; }
        .term-0 { background-color: #ffeeba; color: #856404; } /* Yellow */
        .term-1 { background-color: #c3e6cb; color: #155724; } /* Green */
        .term-2 { background-color: #b8daff; color: #004085; } /* Blue */
        .term-3 { background-color: #f5c6cb; color: #721c24; } /* Red */
        .term-4 { background-color: #bee5eb; color: #0c5460; } /* Teal */
        .term-5 { background-color: #d6d8d9; color: #1b1e21; } /* Grey */
        .current-match { outline: 2px solid red; box-shadow: 0 0 5px red; }
        button { padding: 5px 10px; cursor: pointer; }
    </style>
    <script>
        let matches = [];
        let currentIndex = -1;

        window.onload = function() {
            matches = document.querySelectorAll('.highlight');
            document.getElementById('match-count').innerText = matches.length + " matches found";
            
            if (matches.length > 0) {
                // Optional: Scroll to first match automatically
                // jumpTo(0);
            }
        };

        function nextMatch() {
            if (matches.length === 0) return;
            currentIndex = (currentIndex + 1) % matches.length;
            jumpTo(currentIndex);
        }

        function prevMatch() {
            if (matches.length === 0) return;
            currentIndex = (currentIndex - 1 + matches.length) % matches.length;
            jumpTo(currentIndex);
        }

        function jumpTo(index) {
            // Remove current style from all
            matches.forEach(m => m.classList.remove('current-match'));
            
            // Add to current
            let el = matches[index];
            el.classList.add('current-match');
            el.scrollIntoView({behavior: "smooth", block: "center"});
            
            document.getElementById('current-pos').innerText = (index + 1) + " / " + matches.length;
        }
    </script>
</head>
<body>
    <div class="controls">
        <div><strong>Navigation</strong></div>
        <div id="match-count">0 matches found</div>
        <div id="current-pos" style="margin: 5px 0;">0 / 0</div>
        <button onclick="prevMatch()">Previous</button>
        <button onclick="nextMatch()">Next</button>
        <br><br>
        <a href="javascript:window.close()">Close</a>
    </div>

    <h1>Document: {{ doc_id }}</h1>
    <div class="content">
        {{ content|safe }}
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Legal IR System</title>
    <style>
        :root {
            /* Green Theme */
            --primary-gradient: linear-gradient(135deg, #134E5E 0%, #71B280 100%); /* Marin Blue to Spring Green */
            --secondary-color: #2c3e50;
            --accent-color: #27ae60; /* Emerald */
            --bg-color: #f4f7f6;
            --card-bg: rgba(255, 255, 255, 0.95);
            --text-color: #2c3e50;
            --border-radius: 15px;
            --box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            background-image: url('https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Lahore_High_Court.jpg/1200px-Lahore_High_Court.jpg');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: var(--text-color);
            margin: 0;
            padding: 0;
            line-height: 1.6;
            min-height: 100vh;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 40px;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            min-height: 100vh;
            box-shadow: 0 0 50px rgba(0,0,0,0.3);
        }

        header {
            text-align: center;
            margin-bottom: 50px;
            padding: 20px;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }

        h1 {
            color: #134E5E;
            margin-bottom: 15px;
            font-size: 3.2em;
            font-weight: 800;
            letter-spacing: -1.5px;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.1));
        }

        .subtitle {
            color: #5d6d7e;
            font-size: 1.2em;
            font-weight: 500;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .features-badges {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }

        .feature-badge {
            background: rgba(19, 78, 94, 0.1);
            color: #134E5E;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 600;
            border: 1px solid rgba(19, 78, 94, 0.2);
            transition: var(--transition);
        }

        .feature-badge:hover {
            background: #134E5E;
            color: white;
            transform: translateY(-2px);
        }

        .search-card {
            background: var(--card-bg);
            padding: 40px;
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
            margin-bottom: 40px;
            border: 1px solid rgba(255,255,255,0.5);
            transition: var(--transition);
        }
        
        .search-card:hover {
            box-shadow: 0 15px 50px rgba(0, 0, 0, 0.15);
        }

        .search-form {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }

        .input-group {
            display: flex;
            gap: 15px;
            position: relative;
        }

        input[type="text"] {
            flex-grow: 1;
            padding: 20px 30px;
            font-size: 18px;
            border: 2px solid #e0e6ed;
            border-radius: 50px;
            background: #fdfdfd;
            transition: var(--transition);
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.02);
        }

        input[type="text"]:focus {
            border-color: var(--accent-color);
            outline: none;
            background: #fff;
            box-shadow: 0 0 0 5px rgba(39, 174, 96, 0.15);
        }

        button.search-btn {
            padding: 0 50px;
            background: var(--primary-gradient);
            color: white;
            border: none;
            border-radius: 50px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: 0 5px 15px rgba(19, 78, 94, 0.3);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        button.search-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(19, 78, 94, 0.4);
        }

        .options {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            padding-top: 10px;
        }

        .option-label {
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
            font-size: 0.95em;
            color: #555;
            user-select: none;
            padding: 10px 20px;
            border-radius: 30px;
            transition: var(--transition);
            background: #f8f9fa;
            border: 1px solid #eee;
        }
        
        .option-label:hover {
            background: #fff;
            border-color: var(--accent-color);
            color: var(--accent-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }

        input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
            accent-color: var(--accent-color);
        }

        .examples {
            text-align: center;
            margin-bottom: 50px;
        }

        .example-tag {
            display: inline-block;
            background: rgba(255,255,255,0.8);
            color: #444;
            padding: 10px 20px;
            border-radius: 50px;
            margin: 8px;
            text-decoration: none;
            font-size: 0.95em;
            transition: var(--transition);
            border: 1px solid rgba(0,0,0,0.1);
            backdrop-filter: blur(5px);
        }

        .example-tag:hover {
            background: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(39, 174, 96, 0.3);
        }

        .results-section h2 {
            color: #134E5E;
            font-size: 1.8em;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .results-section h2::after {
            content: '';
            flex-grow: 1;
            height: 3px;
            background: linear-gradient(to right, #71B280, transparent);
            border-radius: 2px;
        }

        .result-card {
            background: var(--card-bg);
            padding: 30px;
            border-radius: var(--border-radius);
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            margin-bottom: 30px;
            transition: var(--transition);
            border-left: 6px solid transparent;
            position: relative;
            overflow: hidden;
        }

        .result-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.1);
            border-left-color: var(--accent-color);
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }

        .result-title {
            font-size: 1.4em;
            color: #134E5E;
            margin: 0;
            font-weight: 700;
            line-height: 1.3;
        }

        .score-badge {
            background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
            color: #555;
            padding: 8px 15px;
            border-radius: 12px;
            font-size: 0.9em;
            font-weight: 600;
            border: 1px solid #e1e4e8;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            line-height: 1.2;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
        }
        
        .score-label {
            font-size: 0.7em;
            text-transform: uppercase;
            color: #999;
            letter-spacing: 1px;
            margin-bottom: 2px;
        }
        
        .score-value {
            color: var(--accent-color);
            font-size: 1.2em;
            font-weight: 800;
        }

        .result-meta {
            color: #7f8c8d;
            font-size: 0.95em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-style: italic;
        }

        .result-snippet {
            color: #444;
            margin-bottom: 25px;
            font-size: 1.05em;
            line-height: 1.8;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #eef2f7;
            position: relative;
        }
        
        .result-snippet::before {
            content: '"';
            font-size: 3em;
            color: #e1e4e8;
            position: absolute;
            top: -10px;
            left: 10px;
            font-family: serif;
        }

        .result-actions {
            display: flex;
            gap: 15px;
        }

        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-top: 20px;
        }

        .action-link {
            text-decoration: none;
            color: #555;
            font-weight: 600;
            font-size: 0.95em;
            padding: 10px 20px;
            background: white;
            border-radius: 8px;
            transition: var(--transition);
            border: 1px solid #eee;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }

        .action-link:hover {
            background: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
            transform: translateY(-2px);
        }
        
        .action-link.primary {
            background: #e8f6f3;
            color: #138d75;
            border-color: #d1f2eb;
        }
        
        .action-link.primary:hover {
            background: #138d75;
            color: white;
            border-color: #138d75;
        }

        .alert {
            padding: 25px;
            border-radius: var(--border-radius);
            margin-bottom: 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: var(--box-shadow);
        }

        .alert-warning {
            background: linear-gradient(to right, #fff8e1, #fff);
            color: #b7950b;
            border-left: 5px solid #f1c40f;
        }

        .suggestions-box {
            background: #fff;
            padding: 25px;
            border-radius: var(--border-radius);
            border-top: 5px solid #e67e22;
            margin-bottom: 40px;
            box-shadow: var(--box-shadow);
        }

        .suggestion-item {
            cursor: pointer;
            color: #d35400;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 6px;
            transition: all 0.2s;
            background: #fef5e7;
            margin: 0 2px;
        }
        
        .suggestion-item:hover {
            background: #d35400;
            color: white;
            text-decoration: none;
        }
        
        /* Highlighting styles */
        .highlight { font-weight: bold; border-radius: 4px; padding: 0 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .term-0 { background-color: #fff3cd; color: #856404; border-bottom: 2px solid #ffecb5; }
        .term-1 { background-color: #d4edda; color: #155724; border-bottom: 2px solid #c3e6cb; }
        .term-2 { background-color: #d1ecf1; color: #0c5460; border-bottom: 2px solid #bee5eb; }
        .term-3 { background-color: #f8d7da; color: #721c24; border-bottom: 2px solid #f5c6cb; }
        .term-4 { background-color: #e2e3e5; color: #383d41; border-bottom: 2px solid #d6d8d9; }

        @media (max-width: 600px) {
            .container { padding: 20px; }
            .input-group { flex-direction: column; }
            .options { flex-direction: column; gap: 10px; align-items: flex-start; }
            h1 { font-size: 2.2em; }
            .search-card { padding: 20px; }
        }
    </style>
    <script>
        function updateQuery(newQuery) {
            document.getElementById('queryInput').value = newQuery;
            document.getElementById('searchForm').submit();
        }
    </script>
</head>
<body>
    <div class="container">
        <header>
            <h1>LHC Judgments Search Engine</h1>
            <div class="subtitle">Advanced Boolean Retrieval System with TF-IDF Ranking</div>
            <div class="features-badges">
                <span class="feature-badge">Boolean Logic</span>
                <span class="feature-badge">TF-IDF Ranking</span>
                <span class="feature-badge">Cosine Similarity</span>
                <span class="feature-badge">Wildcard Search (*)</span>
                <span class="feature-badge">Exact Phrase (" ")</span>
                <span class="feature-badge">Spelling Correction</span>
            </div>
        </header>

        <div class="search-card">
            <form method="get" action="/" class="search-form" id="searchForm">
                <div class="input-group">
                    <input type="text" id="queryInput" name="q" placeholder="Search judgments (e.g., murder AND bail)..." value="{{ query }}">
                    <button type="submit" class="search-btn">Search</button>
                </div>
                
                <div class="options">
                    <label class="option-label" title="Uses Length-Normalized Cosine Similarity (unchecked uses Dot Product)">
                        <input type="checkbox" name="use_cosine" {% if use_cosine %}checked{% endif %}> Use Cosine Similarity
                    </label>
                    
                    <label class="option-label" title="Enable wildcard expansion (*)">
                        <input type="checkbox" name="wildcard" {% if wildcard %}checked{% endif %}> Enable Wildcards
                    </label>
                    
                    <label class="option-label" title="Enable spelling correction">
                        <input type="checkbox" name="spellcheck" {% if spellcheck %}checked{% endif %}> Auto-Correction
                    </label>
                </div>
                <!-- Hidden field to detect submission -->
                <input type="hidden" name="submitted" value="1">
            </form>
        </div>

        <div class="examples">
            <a href="/?q=murder&use_cosine=on&wildcard=on" class="example-tag">murder</a>
            <a href="/?q=bail+AND+murder&use_cosine=on&wildcard=on" class="example-tag">bail AND murder</a>
            <a href="/?q=%22constitution+petition%22&use_cosine=on&wildcard=on" class="example-tag">"constitution petition"</a>
            <a href="/?q=%22writ+petition%22&use_cosine=on&wildcard=on" class="example-tag">"writ petition"</a>
            <a href="/?q=civil+revision&use_cosine=on&wildcard=on" class="example-tag">civil revision</a>
            <a href="/?q=judge*&use_cosine=on&wildcard=on" class="example-tag">judge*</a>
        </div>

        {% if results is not none %}
            
            {% if corrected_query and corrected_query != query %}
                <div class="alert alert-warning">
                    <div>
                        <strong>Spelling Corrected</strong><br>
                        Showing results for <strong>{{ corrected_query }}</strong>
                    </div>
                    <div>
                        <a href="javascript:updateQuery('{{ query|replace("'", "\\'") }}')" style="color: inherit; text-decoration: underline;">Search for <em>{{ query }}</em> instead</a>
                    </div>
                </div>
            {% endif %}

            {% if suggestions %}
                <div class="suggestions-box">
                    <strong>💡 Did you mean?</strong>
                    <ul style="list-style: none; padding-left: 0; margin-top: 10px;">
                    {% for term, suggs in suggestions.items() %}
                        <li style="margin-bottom: 5px;">For <em style="color:#e74c3c;">{{ term }}</em>: 
                            {% for s in suggs %}
                                <span class="suggestion-item" onclick="updateQuery('{{ query.replace(term, s)|replace("'", "\\'") }}')">{{ s }}</span>{% if not loop.last %}, {% endif %}
                            {% endfor %}
                        </li>
                    {% endfor %}
                    </ul>
                </div>
            {% endif %}

            <div class="results-section">
                <h2>Found {{ total_results }} Documents</h2>
                
                {% if not results %}
                    <div style="text-align: center; padding: 50px; color: #95a5a6;">
                        <div style="font-size: 3em; margin-bottom: 20px;">🔍</div>
                        <p style="font-size: 1.2em;">No documents found matching your query.</p>
                        <p>Try different keywords or enable wildcards.</p>
                    </div>
                {% endif %}

                {% if total_results %}
                    <div style="color:#7f8c8d; margin-bottom: 15px;">
                        Showing {{ start_index + 1 }}–{{ end_index }} of {{ total_results }}
                    </div>
                {% endif %}

                {% for res in paginated_results %}
                    <div class="result-card">
                        <div class="result-header">
                            <h3 class="result-title">{{ res.id }}</h3>
                            <div class="score-badge">
                                <span class="score-label">{% if use_cosine %}Cosine Similarity{% else %}TF-IDF Score{% endif %}</span>
                                <span class="score-value">{{ "%.4f"|format(res.score) }}</span>
                            </div>
                        </div>
                        <div class="result-meta">📂 {{ res.path }}</div>
                        <div class="result-snippet">
                            ... {{ highlight_func(res.snippet, ranking_terms)|safe }} ...
                        </div>
                        <div class="result-actions">
                            <a href="/view/doc/{{ res.id }}?q={{ (corrected_query if corrected_query else query)|urlencode }}&use_cosine={{ 'on' if use_cosine else '' }}&wildcard={{ 'on' if wildcard else '' }}" target="_blank" class="action-link primary">
                                📄 Enhanced View
                            </a>
                            <a href="/view/txt/{{ res.id }}" target="_blank" class="action-link">
                                📝 Raw Text
                            </a>
                            <a href="/view/pdf/{{ res.id }}" target="_blank" class="action-link">
                                📑 Original PDF
                            </a>
                        </div>
                    </div>
                {% endfor %}

                {% if total_pages > 1 %}
                    <div class="pagination">
                        <a href="/?q={{ query|urlencode }}&use_cosine={{ 'on' if use_cosine else '' }}&wildcard={{ 'on' if wildcard else '' }}&spellcheck={{ 'on' if spellcheck else '' }}&submitted=1&page={{ page - 1 }}"
                           class="action-link"
                           {% if page <= 1 %}style="pointer-events:none;opacity:0.5"{% endif %}>Prev</a>

                        {% for p in pages %}
                            <a href="/?q={{ query|urlencode }}&use_cosine={{ 'on' if use_cosine else '' }}&wildcard={{ 'on' if wildcard else '' }}&spellcheck={{ 'on' if spellcheck else '' }}&submitted=1&page={{ p }}"
                               class="action-link{% if p == page %} primary{% endif %}">{{ p }}</a>
                        {% endfor %}

                        <a href="/?q={{ query|urlencode }}&use_cosine={{ 'on' if use_cosine else '' }}&wildcard={{ 'on' if wildcard else '' }}&spellcheck={{ 'on' if spellcheck else '' }}&submitted=1&page={{ page + 1 }}"
                           class="action-link"
                           {% if page >= total_pages %}style="pointer-events:none;opacity:0.5"{% endif %}>Next</a>
                    </div>
                {% endif %}
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    global qp
    if qp is None:
        try:
            qp = QueryProcessor()
        except Exception as e:
            return f"Error initializing index: {e}. Please run build.py first."

    query = request.args.get("q", "")
    
    is_submitted = request.args.get("submitted") == "1"
    
    if is_submitted:
        use_cosine = request.args.get("use_cosine") == "on"
        wildcard = request.args.get("wildcard") == "on"
        spellcheck = request.args.get("spellcheck") == "on"
    else:
        use_cosine = request.args.get("use_cosine", "on") == "on"
        wildcard = request.args.get("wildcard", "on") == "on"
        spellcheck = request.args.get("spellcheck", "on") == "on" # Default spellcheck ON

    results = None
    corrected_query = None
    ranking_terms = []
    suggestions = {}
    page = 1
    per_page = 10
    
    if query:
        search_query = query
        
        # Get suggestions regardless of auto-correct
        suggestions = qp.analyze_query_spelling(query)
        
        if spellcheck:
            corrected_query = qp.correct_query(query)
            if corrected_query != query:
                search_query = corrected_query
                # If we auto-corrected, maybe we don't need to show individual suggestions,
                # or maybe we do. Let's keep them if they differ from the corrected one?
                # Actually, analyze_query_spelling gives suggestions for the *original* terms.
                pass

        results, ranking_terms = qp.process_query(
            search_query, 
            enable_ranking=True, 
            use_cosine=use_cosine, 
            enable_wildcards=wildcard
        )
        try:
            page = int(request.args.get("page", "1"))
        except:
            page = 1
        if page < 1:
            page = 1
        total_results = len(results)
        total_pages = (total_results + per_page - 1) // per_page if total_results > 0 else 1
        if page > total_pages:
            page = total_pages
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_results)
        paginated_results = results[start_index:end_index]
        pages = list(range(1, total_pages + 1))
    else:
        total_results = 0
        total_pages = 0
        start_index = 0
        end_index = 0
        paginated_results = []
        pages = []

    return render_template_string(
        HTML_TEMPLATE, 
        query=query, 
        results=results,
        paginated_results=paginated_results,
        ranking_terms=ranking_terms,
        highlight_func=highlight_text,
        use_cosine=use_cosine,
        wildcard=wildcard,
        spellcheck=spellcheck,
        corrected_query=corrected_query,
        suggestions=suggestions,
        total_results=total_results,
        total_pages=total_pages,
        page=page,
        start_index=start_index,
        end_index=end_index,
        pages=pages
    )

@app.route("/view/doc/<doc_id>")
def view_doc(doc_id):
    # Get params to reconstruct query processing (to get terms)
    # Or simply pass terms in query params (but process_query does cleaning/expansion)
    # Re-running process_query is safer to get exact same terms.
    
    global qp
    if qp is None:
        qp = QueryProcessor()
        
    query = request.args.get("q", "")
    wildcard = request.args.get("wildcard") == "on"
    
    ranking_terms = []
    if query:
        # We don't care about ranking, just parsing to get terms
        # We assume spelling correction was already applied if it's in the query string
        # But wait, the link from UI passes the original query. 
        # Ideally we should pass the corrected query if it was corrected.
        # But for now let's just re-process.
        _, ranking_terms = qp.process_query(query, enable_ranking=False, enable_wildcards=wildcard)
    
    filename = f"{doc_id}.txt"
    filepath = os.path.join(TXT_DIR, filename)
    
    if not os.path.exists(filepath):
        return "File not found", 404
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Highlight
    highlighted_content = highlight_text(content, ranking_terms)
    # Replace newlines with <br> for display
    highlighted_content = highlighted_content.replace("\n", "<br>")
    
    return render_template_string(
        VIEW_DOC_TEMPLATE,
        doc_id=doc_id,
        content=highlighted_content
    )

@app.route("/view/pdf/<doc_id>")
def view_pdf(doc_id):
    filename = f"{doc_id}.pdf"
    return send_from_directory(PDF_DIR, filename)

@app.route("/view/txt/<doc_id>")
def view_txt(doc_id):
    filename = f"{doc_id}.txt"
    # We serve it as plain text in browser
    return send_from_directory(TXT_DIR, filename, mimetype='text/plain')

if __name__ == "__main__":
    app.run(debug=True, port=5000)
