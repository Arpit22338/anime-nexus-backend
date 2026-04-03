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
        if not providers:
            raise Exception("No providers available")
        provider_name = providers[0]
        provider_class = get_provider(provider_name)
        DEFAULT_PROVIDER = provider_class()  # Instantiate the class
    return DEFAULT_PROVIDER

@app.route('/')
def home():
    return jsonify({'status': 'online', 'name': 'ANIME//NEXUS API'})

@app.route('/api/debug')
def debug():
    try:
        providers = list(list_providers())
        provider_info = []
        for p in providers:
            provider_class = get_provider(p)
            try:
                instance = provider_class()
                provider_info.append({
                    'name': p,
                    'class_name': provider_class.__name__ if hasattr(provider_class, '__name__') else str(provider_class),
                    'instance_created': True,
                    'instance_type': str(type(instance))
                })
            except Exception as e:
                provider_info.append({
                    'name': p,
                    'class_name': str(provider_class),
                    'instance_created': False,
                    'error': str(e)
                })
        return jsonify({
            'providers_found': providers,
            'provider_details': provider_info,
            'count': len(providers)
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'type': str(type(e)), 'traceback': traceback.format_exc()}), 500

@app.route('/api/search')
def search():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'Missing query'}), 400
    
    try:
        provider = get_default_provider()
        results = provider.get_search(q, LanguageTypeEnum.SUB)
        return jsonify({
            'success': True,
            'results': [{'id': r.identifier, 'name': r.name, 'languages': [str(lang) for lang in r.languages]} for r in results[:15]]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/anime/<anime_id>')
def get_anime(anime_id):
    try:
        provider = get_default_provider()
        # Note: anipy-api doesn't have a direct get_anime method
        # We'll search for it instead
        results = provider.get_search(anime_id, LanguageTypeEnum.SUB)
        if results:
            anime = results[0]
            return jsonify({
                'success': True,
                'anime': {
                    'id': anime.identifier,
                    'name': anime.name,
                    'languages': [str(lang) for lang in anime.languages]
                }
            })
        return jsonify({'error': 'Anime not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/episodes/<anime_id>')
def get_episodes(anime_id):
    lang = request.args.get('lang', 'sub')
    try:
        provider = get_default_provider()
        
        # Get episodes for the specified language
        lang_enum = LanguageTypeEnum.SUB if lang == 'sub' else LanguageTypeEnum.DUB
        episodes = provider.get_episodes(anime_id, lang_enum)
        
        return jsonify({
            'success': True,
            'episodes': [{'number': i+1, 'id': ep.identifier} for i, ep in enumerate(episodes)]
        })
    except Exception as e:
        return jsonify({'error': str(e), 'anime_id': anime_id}), 500

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
