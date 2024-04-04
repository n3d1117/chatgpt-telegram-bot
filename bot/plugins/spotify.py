import os
from typing import Dict

import spotipy
from spotipy import SpotifyOAuth

from .plugin import Plugin


class SpotifyPlugin(Plugin):
    """
    A plugin to fetch information from Spotify
    """
    def __init__(self):
        spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
        spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        spotify_redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
        if not spotify_client_id or not spotify_client_secret or not spotify_redirect_uri:
            raise ValueError('SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET and SPOTIFY_REDIRECT_URI environment variables'
                             ' are required to use SpotifyPlugin')
        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=spotify_client_id,
                client_secret=spotify_client_secret,
                redirect_uri=spotify_redirect_uri,
                scope="user-top-read,user-read-currently-playing",
                open_browser=False
            )
        )

    def get_source_name(self) -> str:
        return "Spotify"

    def get_spec(self) -> [Dict]:
        time_range_param = {
            "type": "string",
            "enum": ["short_term", "medium_term", "long_term"],
            "description": "The time range of the data to be returned. Short term is the last 4 weeks, "
                           "medium term is last 6 months, long term is last several years. Default to "
                           "short_term if not specified."
        }
        limit_param = {
            "type": "integer",
            "description": "The number of results to return. Max is 50. Default to 5 if not specified.",
        }
        type_param = {
            "type": "string",
            "enum": ["album", "artist", "track"],
            "description": "Type of content to search",
        }
        return [
            {
                "name": "spotify_get_currently_playing_song",
                "description": "Get the user's currently playing song",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "spotify_get_users_top_artists",
                "description": "Get the user's top listened artists",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_range": time_range_param,
                        "limit": limit_param
                    }
                }
            },
            {
                "name": "spotify_get_users_top_tracks",
                "description": "Get the user's top listened tracks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_range": time_range_param,
                        "limit": limit_param
                    }
                }
            },
            {
                "name": "spotify_search_by_query",
                "description": "Search spotify content by query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                        "type": type_param
                    },
                    "required": ["query", "type"]
                }
            },
            {
                "name": "spotify_lookup_by_id",
                "description": "Lookup spotify content by id",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The exact id to lookup. Can be a track id, an artist id or an album id",
                        },
                        "type": type_param
                    },
                    "required": ["id", "type"]
                }
            }
        ]

    async def execute(self, function_name, helper, **kwargs) -> Dict:
        time_range = kwargs.get('time_range', 'short_term')
        limit = kwargs.get('limit', 5)

        if function_name == 'spotify_get_currently_playing_song':
            return self.fetch_currently_playing()
        elif function_name == 'spotify_get_users_top_artists':
            return self.fetch_top_artists(time_range, limit)
        elif function_name == 'spotify_get_users_top_tracks':
            return self.fetch_top_tracks(time_range, limit)
        elif function_name == 'spotify_search_by_query':
            query = kwargs.get('query', '')
            search_type = kwargs.get('type', 'track')
            return self.search_by_query(query, search_type, limit)
        elif function_name == 'spotify_lookup_by_id':
            content_id = kwargs.get('id')
            search_type = kwargs.get('type', 'track')
            return self.search_by_id(content_id, search_type)

    def fetch_currently_playing(self) -> Dict:
        """
        Fetch user's currently playing song from Spotify
        """
        currently_playing = self.spotify.current_user_playing_track()
        if not currently_playing:
            return {"result": "No song is currently playing"}
        result = {
            'name': currently_playing['item']['name'],
            'artist': currently_playing['item']['artists'][0]['name'],
            'album': currently_playing['item']['album']['name'],
            'url': currently_playing['item']['external_urls']['spotify'],
            '__album_id': currently_playing['item']['album']['id'],
            '__artist_id': currently_playing['item']['artists'][0]['id'],
            '__track_id': currently_playing['item']['id'],
        }
        return {"result": result}

    def fetch_top_tracks(self, time_range='short_term', limit=5) -> Dict:
        """
        Fetch user's top tracks from Spotify
        """
        results = []
        top_tracks = self.spotify.current_user_top_tracks(limit=limit, time_range=time_range)
        if not top_tracks or 'items' not in top_tracks or len(top_tracks['items']) == 0:
            return {"results": "No top tracks found"}
        for item in top_tracks['items']:
            results.append({
                'name': item['name'],
                'artist': item['artists'][0]['name'],
                'album': item['album']['name'],
                'album_release_date': item['album']['release_date'],
                'url': item['external_urls']['spotify'],
                'album_url': item['album']['external_urls']['spotify'],
                'artist_url': item['artists'][0]['external_urls']['spotify'],
                '__track_id': item['id'],
                '__album_id': item['album']['id'],
                '__artist_id': item['artists'][0]['id'],
            })
        return {'results': results}

    def fetch_top_artists(self, time_range='short_term', limit=5) -> Dict:
        """
        Fetch user's top artists from Spotify
        """
        results = []
        top_artists = self.spotify.current_user_top_artists(limit=limit, time_range=time_range)
        if not top_artists or 'items' not in top_artists or len(top_artists['items']) == 0:
            return {"results": "No top artists found"}
        for item in top_artists['items']:
            results.append({
                'name': item['name'],
                'url': item['external_urls']['spotify'],
                '__artist_id': item['id']
            })
        return {'results': results}

    def search_by_query(self, query, search_type, limit=5) -> Dict:
        """
        Search content by query on Spotify
        """
        results = {}
        search_response = self.spotify.search(q=query, limit=limit, type=search_type)
        if not search_response:
            return {"results": "No content found"}

        if 'tracks' in search_response:
            results['tracks'] = []
            for item in search_response['tracks']['items']:
                results['tracks'].append({
                    'name': item['name'],
                    'artist': item['artists'][0]['name'],
                    'album': item['album']['name'],
                    'album_release_date': item['album']['release_date'],
                    'url': item['external_urls']['spotify'],
                    'album_url': item['album']['external_urls']['spotify'],
                    'artist_url': item['artists'][0]['external_urls']['spotify'],
                    '__artist_id': item['artists'][0]['id'],
                    '__album_id': item['album']['id'],
                    '__track_id': item['id'],
                })
        if 'artists' in search_response:
            results['artists'] = []
            for item in search_response['artists']['items']:
                results['artists'].append({
                    'name': item['name'],
                    'url': item['external_urls']['spotify'],
                    '__artist_id': item['id'],
                })
        if 'albums' in search_response:
            results['albums'] = []
            for item in search_response['albums']['items']:
                results['albums'].append({
                    'name': item['name'],
                    'artist': item['artists'][0]['name'],
                    'url': item['external_urls']['spotify'],
                    'artist_url': item['artists'][0]['external_urls']['spotify'],
                    'release_date': item['release_date'],
                    '__artist_id': item['artists'][0]['id'],
                    '__album_id': item['id'],
                })
        return {'results': results}

    def search_by_id(self, content_id, search_type) -> Dict:
        """
        Search content by exact id on Spotify
        """
        if search_type == 'track':
            search_response = self.spotify.track(content_id)
            if not search_response:
                return {"result": "No track found"}
            return {'result': self._get_track(search_response)}

        elif search_type == 'artist':
            search_response = self.spotify.artist(content_id)
            if not search_response:
                return {"result": "No artisti found"}
            albums_response = self.spotify.artist_albums(artist_id=content_id, limit=3)
            if not albums_response:
                albums_response = {"items": []}
            return {'result': self._get_artist(search_response, albums_response)}

        elif search_type == 'album':
            search_response = self.spotify.album(content_id)
            if not search_response:
                return {"result": "No album found"}
            return {'result': self._get_album(search_response)}

        else:
            return {'error': 'Invalid search type. Must be track, artist or album'}

    @staticmethod
    def _get_artist(response, albums):
        return {
            'name': response['name'],
            'url': response['external_urls']['spotify'],
            '__artist_id': response['id'],
            'followers': response['followers']['total'],
            'genres': response['genres'],
            'albums': [
                {
                    'name': album['name'],
                    '__album_id': album['id'],
                    'url': album['external_urls']['spotify'],
                    'release_date': album['release_date'],
                    'total_tracks': album['total_tracks'],
                }
                for album in albums['items']
            ],
        }

    @staticmethod
    def _get_track(response):
        return {
            'name': response['name'],
            'artist': response['artists'][0]['name'],
            '__artist_id': response['artists'][0]['id'],
            'album': response['album']['name'],
            '__album_id': response['album']['id'],
            'url': response['external_urls']['spotify'],
            '__track_id': response['id'],
            'duration_ms': response['duration_ms'],
            'track_number': response['track_number'],
            'explicit': response['explicit'],
        }

    @staticmethod
    def _get_album(response):
        return {
            'name': response['name'],
            'artist': response['artists'][0]['name'],
            '__artist_id': response['artists'][0]['id'],
            'url': response['external_urls']['spotify'],
            'release_date': response['release_date'],
            'total_tracks': response['total_tracks'],
            '__album_id': response['id'],
            'label': response['label'],
            'tracks': [
                {
                    'name': track['name'],
                    'url': track['external_urls']['spotify'],
                    '__track_id': track['id'],
                    'duration_ms': track['duration_ms'],
                    'track_number': track['track_number'],
                    'explicit': track['explicit'],
                }
                for track in response['tracks']['items']
            ]
        }
