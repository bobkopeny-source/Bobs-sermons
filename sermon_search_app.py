from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json, gzip, os, re

app = Flask(__name__)
CORS(app)

SERMONS = []
if os.path.exists('PASTOR_BOB_AUDIO_ONLY.json.gz'):
    with gzip.open('PASTOR_BOB_AUDIO_ONLY.json.gz', 'rt') as f:
        SERMONS = json.load(f)
    print(f"✅ Loaded {len(SERMONS)} audio sermons")

def extract_excerpt(transcript, term):
    pos = transcript.lower().find(term.lower())
    if pos == -1: return ""
    start = max(0, pos - 150)
    end = min(len(transcript), pos + 150)
    return ("..." + transcript[start:end] + "...")[:300]

def search_sermons(query, max_results=10):
    words = [w for w in re.sub(r'[^\w\s]', ' ', query.lower()).split() if len(w) >= 4]
    results = []
    for s in SERMONS:
        transcript = s.get('transcript', '')
        score = sum(min(transcript.lower().count(w) * 3, 25) for w in words)
        if score > 0:
            excerpts = [extract_excerpt(transcript, w) for w in words if extract_excerpt(transcript, w)]
            if excerpts:
                results.append({'title': s.get('title', 'Sermon'), 'url': s.get('url', ''), 'excerpts': excerpts[:3], 'score': score})
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:max_results]

@app.route('/')
def home():
    return render_template_string('''<!DOCTYPE html>
<html><head><title>Ask Pastor Bob</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;padding:20px}
.container{max-width:1000px;margin:0 auto}
.header{text-align:center;color:white;margin-bottom:40px;padding-top:40px}
.header h1{font-size:3em}
.stats{background:rgba(255,255,255,0.2);border-radius:15px;padding:20px;color:white;text-align:center;margin-bottom:30px}
.stats-number{font-size:2.5em;font-weight:bold}
.search-box{background:white;border-radius:50px;padding:10px 30px;display:flex;margin-bottom:40px}
.search-box input{flex:1;border:none;font-size:1.1em;padding:15px}
.search-box button{background:#667eea;color:white;border:none;padding:15px 40px;border-radius:30px;cursor:pointer}
.results{display:none}
.sermon-card{background:white;border-radius:15px;padding:25px;margin-bottom:20px}
.sermon-title{font-size:1.3em;color:#667eea;margin-bottom:15px;font-weight:600}
.excerpt{background:#f8f9fa;padding:15px;border-radius:10px;margin:10px 0;line-height:1.7;border-left:4px solid #667eea}
.watch-link{display:inline-block;background:#667eea;color:white;padding:10px 25px;border-radius:20px;text-decoration:none;margin-top:10px}
</style></head><body>
<div class="container">
<div class="header"><h1>🎤 Ask Pastor Bob</h1><p>Search 1,302 audio sermons</p></div>
<div class="stats"><div class="stats-number">1,302</div><div>Audio Sermons with Full Context</div></div>
<div class="search-box"><input id="q" placeholder="Ask anything..." onkeypress="if(event.key==='Enter')search()"/><button onclick="search()">Search</button></div>
<div class="results" id="results"></div></div>
<script>
async function search(){
const q=document.getElementById('q').value.trim();
if(!q)return;
const r=await fetch('/api/search?q='+encodeURIComponent(q));
const d=await r.json();
const div=document.getElementById('results');
if(d.results&&d.results.length>0){
div.innerHTML='<h2 style="color:white;margin-bottom:20px;">Found '+d.results.length+' sermons</h2>'+
d.results.map(s=>'<div class="sermon-card"><div class="sermon-title">'+(s.title||'Sermon')+'</div>'+s.excerpts.map(e=>'<div class="excerpt">'+e+'</div>').join('')+'<a href="'+s.url+'" target="_blank" class="watch-link">▶️ Listen</a></div>').join('');
div.style.display='block';
}else{div.innerHTML='<p style="color:white;">No results</p>';div.style.display='block';}
}
</script></body></html>''')

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    if not q: return jsonify({'error': 'No query'}), 400
    return jsonify({'query': q, 'results': search_sermons(q)})

if __name__ == '__main__':
    if not SERMONS: exit(1)
    print("✅ Ready!")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
