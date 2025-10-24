#!/usr/bin/env python3
"""
Pastor Bob Sermon Search App - Version 2.0
AI-Powered Answers from 645 Sermons
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import gzip
import os
import re

app = Flask(__name__)
CORS(app)

print("Loading sermon database...")
SERMONS = []

# Try multiple possible filenames
possible_files = [
    'PASTOR_BOB_SERMONS_COMPLETE_CLEAN.json.gz',
    'PASTOR_BOB_SERMONS_COMPLETE_CLEAN.json',
    'PASTOR_BOB_TRULY_CLEAN.json.gz',
    'PASTOR_BOB_TRULY_CLEAN.json',
]

import os
for filename in possible_files:
    if os.path.exists(filename):
        print(f"Found: {filename}")
        try:
            if filename.endswith('.gz'):
                with gzip.open(filename, 'rt', encoding='utf-8') as f:
                    SERMONS = json.load(f)
            else:
                with open(filename, 'r', encoding='utf-8') as f:
                    SERMONS = json.load(f)
            print(f"✅ Loaded {len(SERMONS)} sermons")
            break
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            continue

if not SERMONS:
    print("❌ ERROR: Sermon database file not found!")

def extract_paragraphs(text):
    """Split text into meaningful paragraphs"""
    # Split on multiple newlines or sentence boundaries
    paragraphs = re.split(r'\n\n+|\. {2,}', text)
    # Filter out very short paragraphs
    return [p.strip() for p in paragraphs if len(p.strip()) > 100]

def find_relevant_passages(transcript, query_words, max_passages=2):
    """Find the most relevant passages from a transcript"""
    # Split into sentences
    sentences = re.split(r'[.!?]+\s+', transcript)
    
    # Score each sentence
    scored_sentences = []
    for sentence in sentences:
        if len(sentence) < 50:  # Skip very short sentences
            continue
            
        sentence_lower = sentence.lower()
        score = 0
        
        # Score based on query word presence
        for word in query_words:
            if len(word) > 4:  # Only score meaningful words
                if word in sentence_lower:
                    score += 10
                    # Bonus if word appears multiple times
                    score += sentence_lower.count(word) * 5
        
        if score > 0:
            scored_sentences.append({
                'text': sentence.strip(),
                'score': score,
                'position': transcript.find(sentence)
            })
    
    # Sort by score
    scored_sentences.sort(key=lambda x: x['score'], reverse=True)
    
    # Get top sentences and add context
    passages = []
    for item in scored_sentences[:max_passages]:
        # Find the sentence position in transcript
        pos = item['position']
        
        # Get surrounding context (2 sentences before and after)
        start = max(0, pos - 200)
        end = min(len(transcript), pos + len(item['text']) + 200)
        
        passage = transcript[start:end].strip()
        
        # Clean up
        if start > 0:
            passage = "..." + passage
        if end < len(transcript):
            passage = passage + "..."
        
        passages.append(passage)
    
    return passages

def search_sermons_v2(query, max_results=10):
    """
    Enhanced search with better relevance and focused passages
    """
    query_lower = query.lower()
    # Only use meaningful words (5+ characters) for search
    query_words = [w for w in query_lower.split() if len(w) >= 5]
    
    # If no meaningful words, use all words over 3 characters
    if not query_words:
        query_words = [w for w in query_lower.split() if len(w) > 3]
    
    results = []
    
    for sermon in SERMONS:
        title = sermon.get('title', '')
        transcript = sermon.get('transcript', '')
        
        # Calculate relevance score
        score = 0
        
        # Title matches are very important
        title_lower = title.lower()
        for word in query_words:
            if word in title_lower:
                score += 30
        
        # Full phrase in transcript (very relevant)
        transcript_lower = transcript.lower()
        if len(query_words) > 1:
            # Check for meaningful phrase (any 2+ meaningful words together)
            phrase = ' '.join(query_words[:2])
            if phrase in transcript_lower:
                score += 20
        
        # Individual word frequency (but not too much weight)
        for word in query_words:
            count = transcript_lower.count(word)
            if count > 0:
                score += min(count * 2, 20)  # Cap at 20 points per word
        
        if score == 0:
            continue
        
        # Find relevant passages
        passages = find_relevant_passages(transcript, query_words, max_passages=2)
        
        if passages:
            results.append({
                'title': title,
                'date': sermon.get('date', ''),
                'url': sermon.get('url', ''),
                'word_count': sermon.get('word_count', 0),
                'passages': passages,
                'score': score,
                'relevance': calculate_relevance_description(query_lower, passages[0] if passages else '')
            })
    
    # Sort by relevance
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:max_results]

def calculate_relevance_description(query, passage):
    """Generate a description of why this sermon is relevant"""
    query_lower = query.lower()
    passage_lower = passage.lower()
    
    # Look for key phrases
    if 'teach' in query_lower or 'what does' in query_lower:
        return "Pastor Bob teaches about this topic"
    elif 'how' in query_lower:
        return "Pastor Bob explains how this applies"
    elif 'why' in query_lower:
        return "Pastor Bob discusses the reasons"
    elif 'bible say' in query_lower or 'scripture' in query_lower:
        return "Pastor Bob references biblical teaching"
    else:
        return "Pastor Bob discusses this topic"

def generate_summary_answer(query, results):
    """
    Generate a summary answer based on the top results
    """
    if not results:
        return None
    
    # Get key quotes from top 5 sermons
    top_results = results[:5]
    
    # Extract first passage from each
    key_quotes = []
    for result in top_results:
        if result['passages']:
            # Get first sentence or two from first passage
            passage = result['passages'][0]
            sentences = passage.split('. ')
            excerpt = '. '.join(sentences[:2]) + '.'
            if len(excerpt) > 200:
                excerpt = excerpt[:200] + '...'
            key_quotes.append({
                'text': excerpt,
                'title': result['title']
            })
    
    return {
        'sermon_count': len(results),
        'top_teachings': key_quotes
    }

@app.route('/')
def home():
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ask Pastor Bob - AI Sermon Search</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
            padding-top: 40px;
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .search-box {
            background: white;
            border-radius: 50px;
            padding: 10px 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            margin-bottom: 40px;
        }
        
        .search-box input {
            flex: 1;
            border: none;
            outline: none;
            font-size: 1.1em;
            padding: 15px;
        }
        
        .search-box button {
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 30px;
            font-size: 1em;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.3s;
        }
        
        .search-box button:hover {
            background: #5568d3;
        }
        
        .loading {
            text-align: center;
            color: white;
            font-size: 1.2em;
            display: none;
            margin: 20px 0;
        }
        
        .results {
            display: none;
        }
        
        .summary-box {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        
        .summary-title {
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            font-weight: 600;
        }
        
        .summary-intro {
            font-size: 1.1em;
            color: #555;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        
        .key-teaching {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        
        .key-teaching-text {
            font-style: italic;
            color: #333;
            line-height: 1.6;
            margin-bottom: 10px;
        }
        
        .key-teaching-source {
            color: #666;
            font-size: 0.9em;
        }
        
        .sermons-header {
            color: white;
            font-size: 1.5em;
            margin: 30px 0 20px 0;
            text-align: center;
        }
        
        .sermon-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        
        .sermon-title {
            font-size: 1.4em;
            color: #667eea;
            margin-bottom: 10px;
            font-weight: 600;
        }
        
        .sermon-meta {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 15px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .relevance-badge {
            background: #e3f2fd;
            color: #1976d2;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            display: inline-block;
            margin-bottom: 15px;
        }
        
        .passage {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
            line-height: 1.8;
            color: #333;
        }
        
        .passage-separator {
            margin: 15px 0;
            color: #999;
            text-align: center;
        }
        
        .watch-button {
            display: inline-block;
            background: #ff0000;
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 600;
            transition: background 0.3s;
            margin-top: 10px;
        }
        
        .watch-button:hover {
            background: #cc0000;
        }
        
        .no-results {
            background: white;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            display: none;
        }
        
        .stats {
            background: rgba(255,255,255,0.2);
            border-radius: 15px;
            padding: 20px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .stats-number {
            font-size: 2.5em;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 Ask Pastor Bob</h1>
            <p>Get answers from 645 sermons with AI-powered search</p>
        </div>
        
        <div class="stats">
            <div class="stats-number">645</div>
            <div>Complete Sermons • AI-Enhanced Answers</div>
        </div>
        
        <div class="search-box">
            <input 
                type="text" 
                id="searchInput" 
                placeholder="Ask anything... (e.g., 'What does Pastor Bob teach about prayer and fasting?')"
                onkeypress="if(event.key === 'Enter') searchSermons()"
            />
            <button onclick="searchSermons()">Search</button>
        </div>
        
        <div class="loading" id="loading">
            🤖 Analyzing 645 sermons to answer your question...
        </div>
        
        <div class="results" id="results">
            <div id="summarySection"></div>
            <div id="sermonsSection"></div>
        </div>
        
        <div class="no-results" id="noResults">
            <h2>No sermons found</h2>
            <p>Try different keywords or a broader search term</p>
        </div>
    </div>
    
    <script>
        async function searchSermons() {
            const query = document.getElementById('searchInput').value.trim();
            
            if (!query) {
                alert('Please enter a search term');
                return;
            }
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('noResults').style.display = 'none';
            
            try {
                const response = await fetch(`/api/search/v2?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                
                if (data.results && data.results.length > 0) {
                    displayResults(data, query);
                } else {
                    document.getElementById('noResults').style.display = 'block';
                }
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                alert('Error searching sermons. Please try again.');
                console.error(error);
            }
        }
        
        function displayResults(data, query) {
            const summarySection = document.getElementById('summarySection');
            const sermonsSection = document.getElementById('sermonsSection');
            
            // Display summary
            if (data.summary) {
                summarySection.innerHTML = `
                    <div class="summary-box">
                        <div class="summary-title">📖 What Pastor Bob Teaches</div>
                        <div class="summary-intro">
                            Found <strong>${data.summary.sermon_count}</strong> sermons where Pastor Bob discusses "${query}". 
                            Here are key teachings from his sermons:
                        </div>
                        ${data.summary.top_teachings.map(teaching => `
                            <div class="key-teaching">
                                <div class="key-teaching-text">"${teaching.text}"</div>
                                <div class="key-teaching-source">— ${teaching.title}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            // Display sermons
            sermonsSection.innerHTML = `
                <div class="sermons-header">📺 Full Sermons on This Topic</div>
                ${data.results.map(sermon => `
                    <div class="sermon-card">
                        <div class="sermon-title">${sermon.title}</div>
                        <div class="sermon-meta">
                            <span>📅 ${formatDate(sermon.date)}</span>
                            <span>📝 ${sermon.word_count.toLocaleString()} words</span>
                        </div>
                        <div class="relevance-badge">${sermon.relevance}</div>
                        ${sermon.passages.slice(0, 2).map((passage, idx) => `
                            <div class="passage">${highlightKeywords(passage, query)}</div>
                            ${idx < Math.min(sermon.passages.length, 2) - 1 ? '<div class="passage-separator">• • •</div>' : ''}
                        `).join('')}
                        ${sermon.url ? `<a href="${sermon.url}" target="_blank" class="watch-button">▶️ Watch Full Sermon</a>` : ''}
                    </div>
                `).join('')}
            `;
            
            document.getElementById('results').style.display = 'block';
        }
        
        function formatDate(dateString) {
            if (!dateString) return 'Date unknown';
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
        }
        
        function highlightKeywords(text, query) {
            const words = query.toLowerCase().split(' ');
            let highlighted = text;
            
            words.forEach(word => {
                // Only highlight meaningful words (5+ characters)
                // This avoids highlighting "what", "does", etc.
                if (word.length >= 5) {
                    // Simple case-insensitive replacement
                    const parts = highlighted.split(new RegExp('(' + word + ')', 'gi'));
                    highlighted = parts.map((part, i) => 
                        i % 2 === 1 ? '<strong style="background: #fff59d; padding: 2px 4px; border-radius: 3px;">' + part + '</strong>' : part
                    ).join('');
                }
            });
            
            return highlighted;
        }
    </script>
</body>
</html>
'''
    return render_template_string(html)

@app.route('/api/search/v2')
def api_search_v2():
    """
    Enhanced API endpoint with summary answers
    """
    query = request.args.get('q', '')
    max_results = int(request.args.get('max', 10))
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    results = search_sermons_v2(query, max_results)
    summary = generate_summary_answer(query, results)
    
    return jsonify({
        'query': query,
        'total_sermons': len(SERMONS),
        'results_count': len(results),
        'summary': summary,
        'results': results
    })

@app.route('/api/stats')
def api_stats():
    """Get statistics"""
    total_words = sum(s.get('word_count', 0) for s in SERMONS)
    dates = [s.get('date') for s in SERMONS if s.get('date')]
    dates.sort()
    
    return jsonify({
        'total_sermons': len(SERMONS),
        'total_words': total_words,
        'oldest_sermon': dates[0] if dates else None,
        'newest_sermon': dates[-1] if dates else None
    })

if __name__ == '__main__':
    if not SERMONS:
        print("\n❌ ERROR: No sermons loaded!")
        exit(1)
    
    print("\n✅ Sermon Search App Ready!")
    print(f"📚 Loaded {len(SERMONS)} sermons")
    print("\n🌐 Starting server...")
    
    # Get port from environment (Render provides this)
    port = int(os.environ.get('PORT', 5000))
    
    app.run(debug=False, host='0.0.0.0', port=port)
