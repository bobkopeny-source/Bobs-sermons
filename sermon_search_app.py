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

def extract_excerpt(transcript, term, context=200):
    pos = transcript.lower().find(term.lower())
    if pos == -1: return ""
    start = max(0, pos - context)
    end = min(len(transcript), pos + context)
    excerpt = transcript[start:end].strip()
    if start > 0: excerpt = "..." + excerpt
    if end < len(transcript): excerpt = excerpt + "..."
    return excerpt

def synthesize_answer(results, query):
    if not results: return ""
    all_excerpts = []
    for r in results[:5]:
        for excerpt in r['excerpts'][:2]:
            if len(excerpt) > 50:
                all_excerpts.append(excerpt.replace('...', '').strip())
    if not all_excerpts: return ""
    intro = f'Pastor Bob teaches that {query.lower().replace("what does pastor bob teach about", "").replace("?", "").strip()}'
    paragraphs = []
    for i, excerpt in enumerate(all_excerpts[:4]):
        if i == 0: paragraphs.append(f"{intro}: {excerpt}")
        elif i == 1: paragraphs.append(f"He emphasizes that {excerpt}")
        elif i == 2: paragraphs.append(f"Additionally, {excerpt}")
        else: paragraphs.append(f"As Pastor Bob explains, {excerpt}")
    return " ".join(paragraphs)

def search_sermons(query, max_results=10):
    words = [w for w in re.sub(r'[^\w\s]', ' ', query.lower()).split() if len(w) >= 4]
    results = []
    for s in SERMONS:
        transcript = s.get('transcript', '')
        score = sum(min(transcript.lower().count(w) * 3, 25) for w in words)
        if score > 0:
            excerpts = [extract_excerpt(transcript, w, 250) for w in words if extract_excerpt(transcript, w, 250)]
            if excerpts:
                results.append({'title': s.get('title', 'Sermon'), 'excerpts': excerpts[:3], 'score': score})
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:max_results]

@app.route('/')
def home():
    return render_template_string('''<!DOCTYPE html>
<html><head><title>Ask Pastor Bob</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;padding:20px}
.container{max-width:900px;margin:0 auto}
.header{text-align:center;color:white;margin-bottom:40px;padding-top:40px}
.header h1{font-size:3em}
.stats{background:rgba(255,255,255,0.2);border-radius:15px;padding:20px;color:white;text-align:center;margin-bottom:30px}
.stats-number{font-size:2.5em;font-weight:bold}
.search-box{background:white;border-radius:50px;padding:10px 30px;display:flex;margin-bottom:40px}
.search-box input{flex:1;border:none;font-size:1.1em;padding:15px}
.search-box button{background:#667eea;color:white;border:none;padding:15px 40px;border-radius:30px;cursor:pointer}
.results{display:none}
.answer-box{background:white;border-radius:15px;padding:30px;margin-bottom:30px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}
.answer-title{font-size:1.4em;color:#667eea;margin-bottom:20px;font-weight:600}
.answer-text{line-height:1.9;font-size:1.1em;color:#333}
.sources{margin-top:30px;padding-top:20px;border-top:2px solid #eee}
.sources-title{font-size:1.1em;color:#667eea;margin-bottom:15px;font-weight:600}
.source-item{background:#f8f9fa;padding:15px;border-radius:10px;margin:10px 0;border-left:4px solid #667eea}
.source-title{font-weight:600;color:#667eea;margin-bottom:8px;font-size:0.95em}
.source-excerpt{color:#555;line-height:1.6;font-size:0.9em}
</style></head><body>
<div class="container">
<div class="header"><h1>🎤 Ask Pastor Bob</h1><p>Search 40 years of teaching</p></div>
<div class="stats"><div class="stats-number">1,302</div><div>Audio Sermons</div></div>
<div class="search-box"><input id="q" placeholder="What does Pastor Bob teach about grace?" onkeypress="if(event.key==='Enter')search()"/><button onclick="search()">Search</button></div>
<div class="results" id="results"></div></div>
<script>
async function search(){
const q=document.getElementById('q').value.trim();
if(!q)return;
const r=await fetch('/api/search?q='+encodeURIComponent(q));
const d=await r.json();
const div=document.getElementById('results');
if(d.answer){
let html='<div class="answer-box"><div class="answer-title">📖 '+q+'</div><div class="answer-text">'+d.answer+'</div>';
if(d.results&&d.results.length>0){
html+='<div class="sources"><div class="sources-title">Sources from '+d.results.length+' sermons:</div>';
d.results.slice(0,5).forEach(s=>{
html+='<div class="source-item"><div class="source-title">'+s.title+'</div>';
s.excerpts.slice(0,2).forEach(e=>{html+='<div class="source-excerpt">'+e+'</div>';});
html+='</div>';
});
html+='</div>';
}
html+='</div>';
div.innerHTML=html;
}else{div.innerHTML='<p style="color:white;text-align:center">No results found</p>';}
div.style.display='block';
}
</script></body></html>''')

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    if not q: return jsonify({'error': 'No query'}), 400
    results = search_sermons(q)
    answer = synthesize_answer(results, q)
    return jsonify({'query': q, 'answer': answer, 'results': results})

if __name__ == '__main__':
    if not SERMONS: exit(1)
    print("✅ Ready!")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
