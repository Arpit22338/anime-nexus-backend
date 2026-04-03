import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from anipy_api.provider import list_providers, get_provider, LanguageTypeEnum

app = Flask(__name__)
CORS(app)

DEFAULT_PROVIDER = None

def get_default_provider():
    global DEFAULT_PROVIDER
    if not DEFAULT_PROVIDER:
        providers = list(list_providers())
        DEFAULT_PROVIDER = get_provider(providers[0])()
    return DEFAULT_PROVIDER

@app.route('/')
def home():
    return jsonify({'status': 'online', 'name': 'ANIME//NEXUS API'})

@app.route('/api/search')
def search():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'Missing query'}), 400
    
    try:
        provider = get_default_provider()
        results = provider.get_search(q)
        return jsonify({
            'success': True,
            'results': [{'id': r.identifier, 'name': r.name} for r in results[:15]]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3001)))
