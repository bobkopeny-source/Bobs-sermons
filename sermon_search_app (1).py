#!/usr/bin/env python3
"""
Pastor Bob Sermon Search App
Searches through 645 sermons and returns relevant excerpts with YouTube links
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import gzip
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for API requests

# Load sermons at startup
print("Loading sermon database...")
SERMONS = []

# Try multiple possible filenames
possible_files = [
    'PASTOR_BOB_SERMONS_COMPLETE_CLEAN.json.gz',
    'PASTOR_BOB_SERMONS_COMPLETE_CLEAN.json',
    'PASTOR_BOB_SERMONS_FINAL.json.gz',
    'PASTOR_BOB_SERMONS_FINAL.json',
    'PASTOR_BOB_SERMONS_CLEAN.json.gz',
    'PASTOR_BOB_SERMONS_CLEAN.json'
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
    print(f"Looking for files in: {os.getcwd()}")
    print(f"Files present: {os.listdir('.')}")
    print("Make sure one of these files is in the same directory:")
    for f in possible_files:
        print(f"  - {f}")

def search_sermons(query, max_results=10):
    """
    Search through sermons and return relevant results with excerpts
    """
    query_lower = query.lower()
    query_words = query_lower.split()
    
    results = []
    
    for sermon in SERMONS:
        title = sermon.get('title', '')
        transcript = sermon.get('transcript', '')
        description = sermon.get('description', '')
        
        # Calculate relevance score
        score = 0
        
        # Title matches are most important
        title_lower = title.lower()
        for word in query_words:
            if word in title_lower:
                score += 10
        
        # Full phrase in transcript
        transcript_lower = transcript.lower()
        if query_lower in transcript_lower:
            score += 5
        
        # Individual word matches in transcript
        for word in query_words:
            if len(word) > 3:  # Skip short words
                count = transcript_lower.count(word)
                score += count * 0.5
        
        # If no matches, skip this sermon
        if score == 0:
            continue
        
        # Find best excerpt (context around the query)
        excerpt = find_best_excerpt(transcript, query_words)
        
        results.append({
            'title': title,
            'date': sermon.get('date', ''),
            'url': sermon.get('url', ''),
            'word_count': sermon.get('word_count', 0),
            'excerpt': excerpt,
            'score': score
        })
    
    # Sort by relevance score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:max_results]

def find_best_excerpt(transcript, query_words, context_chars=300):
    """
    Find the most relevant excerpt from the transcript
    """
    if not transcript:
        return ""
    
    transcript_lower = transcript.lower()
    
    # Find the position of the first query word
    best_position = -1
    for word in query_words:
        if len(word) > 3:
            pos = transcript_lower.find(word)
            if pos != -1:
                best_position = pos
                break
    
    if best_position == -1:
        # No match found, return beginning
        return transcript[:context_chars] + "..."
    
    # Get context around the match
    start = max(0, best_position - context_chars // 2)
    end = min(len(transcript), best_position + context_chars // 2)
    
    # Adjust to word boundaries
    while start > 0 and transcript[start] not in ' \n':
        start -= 1
    while end < len(transcript) and transcript[end] not in ' \n':
        end += 1
    
    excerpt = transcript[start:end].strip()
    
    # Add ellipsis
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(transcript):
        excerpt = excerpt + "..."
    
    return excerpt

@app.route('/')
def home():
    """
    Serve the main search interface
    """
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ask Pastor Bob - Sermon Search</title>
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
                max-width: 900px;
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
            
            .result-count {
                color: white;
                font-size: 1.1em;
                margin-bottom: 20px;
                text-align: center;
            }
            
            .sermon-card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                transition: transform 0.3s, box-shadow 0.3s;
            }
            
            .sermon-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
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
            
            .sermon-meta span {
                display: flex;
                align-items: center;
                gap: 5px;
            }
            
            .excerpt {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
                line-height: 1.6;
                color: #333;
                font-style: italic;
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
            
            .no-results h2 {
                color: #667eea;
                margin-bottom: 10px;
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
                <p>Search through 645 sermons to find what Pastor Bob teaches</p>
            </div>
            
            <div class="stats">
                <div class="stats-number">645</div>
                <div>Complete Sermons Available to Search</div>
            </div>
            
            <div class="search-box">
                <input 
                    type="text" 
                    id="searchInput" 
                    placeholder="What would you like to know? (e.g., 'What does Pastor Bob teach about prayer?')"
                    onkeypress="if(event.key === 'Enter') searchSermons()"
                />
                <button onclick="searchSermons()">Search</button>
            </div>
            
            <div class="loading" id="loading">
                🔍 Searching through 645 sermons...
            </div>
            
            <div class="results" id="results">
                <div class="result-count" id="resultCount"></div>
                <div id="resultsList"></div>
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
                
                // Show loading, hide results
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').style.display = 'none';
                document.getElementById('noResults').style.display = 'none';
                
                try {
                    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                    const data = await response.json();
                    
                    document.getElementById('loading').style.display = 'none';
                    
                    if (data.results && data.results.length > 0) {
                        displayResults(data.results, query);
                    } else {
                        document.getElementById('noResults').style.display = 'block';
                    }
                } catch (error) {
                    document.getElementById('loading').style.display = 'none';
                    alert('Error searching sermons. Please try again.');
                    console.error(error);
                }
            }
            
            function displayResults(results, query) {
                const resultCount = document.getElementById('resultCount');
                const resultsList = document.getElementById('resultsList');
                
                resultCount.textContent = `Found ${results.length} sermon${results.length === 1 ? '' : 's'} about "${query}"`;
                
                resultsList.innerHTML = results.map((sermon, index) => `
                    <div class="sermon-card">
                        <div class="sermon-title">${sermon.title}</div>
                        <div class="sermon-meta">
                            <span>📅 ${formatDate(sermon.date)}</span>
                            <span>📝 ${sermon.word_count.toLocaleString()} words</span>
                        </div>
                        <div class="excerpt">${highlightKeywords(sermon.excerpt, query)}</div>
                        ${sermon.url ? `<a href="${sermon.url}" target="_blank" class="watch-button">▶️ Watch on YouTube</a>` : ''}
                    </div>
                `).join('');
                
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
                    if (word.length > 3) {
                        const regex = new RegExp(`(${word})`, 'gi');
                        highlighted = highlighted.replace(regex, '<strong style="background: #fff59d;">$1</strong>');
                    }
                });
                
                return highlighted;
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/api/search')
def api_search():
    """
    API endpoint for searching sermons
    """
    query = request.args.get('q', '')
    max_results = int(request.args.get('max', 10))
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    results = search_sermons(query, max_results)
    
    return jsonify({
        'query': query,
        'total_sermons': len(SERMONS),
        'results_count': len(results),
        'results': results
    })

@app.route('/api/stats')
def api_stats():
    """
    Get statistics about the sermon database
    """
    total_words = sum(s.get('word_count', 0) for s in SERMONS)
    
    # Get date range
    dates = [s.get('date') for s in SERMONS if s.get('date')]
    dates.sort()
    
    return jsonify({
        'total_sermons': len(SERMONS),
        'total_words': total_words,
        'oldest_sermon': dates[0] if dates else None,
        'newest_sermon': dates[-1] if dates else None,
        'average_words_per_sermon': total_words // len(SERMONS) if SERMONS else 0
    })

if __name__ == '__main__':
    if not SERMONS:
        print("\n❌ ERROR: No sermons loaded!")
        print("Please make sure PASTOR_BOB_SERMONS_COMPLETE_CLEAN.json.gz is in the same directory")
        exit(1)
    
    print("\n✅ Sermon Search App Ready!")
    print(f"📚 Loaded {len(SERMONS)} sermons")
    print("\n🌐 Starting server...")
    print("Visit: http://localhost:5000")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
