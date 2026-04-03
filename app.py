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
            'results': [{'id': r.identifier, 'name': r.name, 'languages': r.languages} for r in results[:15]]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/anime/<anime_id>')
def get_anime(anime_id):
    try:
        provider = get_default_provider()
        anime = provider.get_anime(anime_id)
        return jsonify({
            'success': True,
            'anime': {
                'id': anime.identifier,
                'name': anime.name,
                'languages': anime.languages
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/episodes/<anime_id>')
def get_episodes(anime_id):
    lang = request.args.get('lang', 'sub')
    try:
        provider = get_default_provider()
        
        # Get anime info first
        anime = provider.get_anime(anime_id)
        
        # Get episodes for the specified language
        lang_enum = LanguageTypeEnum.SUB if lang == 'sub' else LanguageTypeEnum.DUB
        episodes = provider.get_episodes(anime_id, lang_enum)
        
        return jsonify({
            'success': True,
            'episodes': [{'number': i+1, 'id': ep.identifier} for i, ep in enumerate(episodes)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream/<anime_id>/<int:episode>')
def get_stream(anime_id, episode):
    lang = request.args.get('lang', 'sub')
    try:
        provider = get_default_provider()
        
        # Get episodes
        lang_enum = LanguageTypeEnum.SUB if lang == 'sub' else LanguageTypeEnum.DUB
        episodes = provider.get_episodes(anime_id, lang_enum)
        
        if episode < 1 or episode > len(episodes):
            return jsonify({'error': 'Invalid episode number'}), 400
        
        # Get stream URL for the episode
        ep = episodes[episode - 1]
        stream = provider.get_video(ep)
        
        return jsonify({
            'success': True,
            'stream_url': stream.url if hasattr(stream, 'url') else str(stream)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3001)))
