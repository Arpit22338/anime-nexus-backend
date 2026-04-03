import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({'status': 'online', 'name': 'ANIME//NEXUS API', 'version': '2.0'})

@app.route('/api/test')
def test():
    try:
        from anipy_api.provider import list_providers, get_provider, LanguageTypeEnum
        providers = list(list_providers())
        return jsonify({
            'success': True,
            'providers': providers,
            'provider_count': len(providers)
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/search')
def search():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'Missing query'}), 400
    
    try:
        from anipy_api.provider import list_providers, get_provider, LanguageTypeEnum
        
        # Get available providers
        providers = list(list_providers())
        if not providers:
            return jsonify({'error': 'No providers available'}), 500
        
        # Use first provider
        provider_name = providers[0]
        provider_class = get_provider(provider_name)
        provider = provider_class()
        
        # Search
        results = provider.get_search(q, LanguageTypeEnum.SUB)
        
        return jsonify({
            'success': True,
            'provider_used': provider_name,
            'results': [{'id': r.identifier, 'name': r.name} for r in results[:15]]
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/episodes/<anime_id>')
def get_episodes(anime_id):
    lang = request.args.get('lang', 'sub')
    try:
        from anipy_api.provider import list_providers, get_provider, LanguageTypeEnum
        
        providers = list(list_providers())
        provider_name = providers[0]
        provider_class = get_provider(provider_name)
        provider = provider_class()
        
        lang_enum = LanguageTypeEnum.SUB if lang == 'sub' else LanguageTypeEnum.DUB
        episodes = provider.get_episodes(anime_id, lang_enum)
        
        return jsonify({
            'success': True,
            'episodes': [{'number': i+1, 'id': ep.identifier} for i, ep in enumerate(episodes)]
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc(), 'anime_id': anime_id}), 500

@app.route('/api/stream/<anime_id>/<int:episode>')
def get_stream(anime_id, episode):
    lang = request.args.get('lang', 'sub')
    try:
        from anipy_api.provider import list_providers, get_provider, LanguageTypeEnum
        
        providers = list(list_providers())
        provider_name = providers[0]
        provider_class = get_provider(provider_name)
        provider = provider_class()
        
        lang_enum = LanguageTypeEnum.SUB if lang == 'sub' else LanguageTypeEnum.DUB
        episodes = provider.get_episodes(anime_id, lang_enum)
        
        if episode < 1 or episode > len(episodes):
            return jsonify({'error': 'Invalid episode number'}), 400
        
        ep = episodes[episode - 1]
        stream = provider.get_video(ep)
        
        return jsonify({
            'success': True,
            'stream_url': stream.url if hasattr(stream, 'url') else str(stream)
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3001)))
