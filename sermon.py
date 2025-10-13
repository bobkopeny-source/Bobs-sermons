from flask import Flask, request, jsonify
import pyttsx3
engine = pyttsx3.init()
app = Flask(__name__)
@app.route('/ask')
def ask():
    question = request.args.get('q', '')
    if 'rapture' in question:
        engine.say("Pastor Bob says the rapture's pre-trib - dead rise first, then us - twinkling of an eye.")
    elif 'becky' in question:
        engine.say("Pastor Bob never mentions Becky in any sermon.")
    engine.runAndWait()
    return jsonify(answer="spoken")
if __name__ == '__main__':
    app.run(port=5000)