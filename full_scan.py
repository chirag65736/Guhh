"""Bounded Full Scan: share profile/media data instead of flooding six scrapers.

The standalone scan modes remain independent. Cache and cooldown state are
process-local; changing the authorized Instagram session invalidates both.
"""
import copy
import hashlib
import json
import math
import os
import re
import threading
import time
from collections import OrderedDict
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
from curl_cffi import requests
from post_engagement_scraper import _parse_post_node
from profile_info_scraper import _parse_user_json
from private_posts_scraper import POST_MEDIA_DOC_ID, IG_APP_ID, _clean_url
from full_scan_posts import collect_posts, needs_media_detail, post_key

_LOCK = threading.Lock()
_CACHE = OrderedDict()
_COOLDOWNS = {}


def _empty():
    return dict(image_urls=[], profile_info=None, follower_usernames=[],
                post_engagement=[], all_post_urls=[], video_urls=[], notices=[])


def _objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _html_data(page, username):
    """Read public embedded data and metadata; never infer private followers."""
    soup = BeautifulSoup(page, 'html.parser')
    user, nodes = None, {}
    for script in soup.find_all('script'):
        try:
            data = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue
        for obj in _objects(data):
            if str(obj.get('username', '')).lower() == username:
                if 'edge_owner_to_timeline_media' in obj or 'is_private' in obj:
                    user = obj if user is None or 'edge_owner_to_timeline_media' in obj else user
            owner = obj.get('owner') or obj.get('user') or {}
            if not isinstance(owner, dict):
                continue
            code = obj.get('shortcode') or obj.get('code')
            if code and str(owner.get('username', '')).lower() == username:
                nodes[code] = obj
    def meta(name):
        tag = soup.find('meta', attrs={'property': name})
        return tag.get('content', '') if tag else ''
    info = {}
    desc, title = meta('og:description'), meta('og:title')
    # Login pages' generic images are not profile data.
    if f'(@{username})' in title.lower() or 'Followers' in desc:
        info = {'username': username, 'profile_pic_url': meta('og:image')}
        match = re.match(r'^(.*?)\s*\(@', title)
        if match:
            info['full_name'] = match.group(1)
        for key, label in [('followers', 'Followers'), ('following', 'Following'), ('posts', 'Posts')]:
            match = re.search(r'([\d,.]+\s*[KM]?)\s+' + label, desc, re.I)
            if match:
                text = match.group(1).replace(',', '').strip().upper()
                factor = 1000 if text.endswith('K') else 1000000 if text.endswith('M') else 1
                info[key] = int(float(text.rstrip('KM').strip()) * factor)
        info['bio'] = desc.split(' - ', 1)[-1] if ' - ' in desc else ''
    return user, list(nodes.values()), info or None


def _best(versions):
    return max(versions, key=lambda v: (v.get('width') or 0) * (v.get('height') or 0), default={})


def _media(node, result):
    children = node.get('carousel_media') or [e.get('node', {}) for e in
                node.get('edge_sidecar_to_children', {}).get('edges', [])] or [node]
    for item in children:
        image = _best(item.get('image_versions2', {}).get('candidates', []))
        url = _clean_url(image.get('url') or item.get('display_url') or item.get('display_uri') or item.get('thumbnail_src', ''))
        if url and url not in result['all_post_urls']:
            result['all_post_urls'].append(url)
        video = _best(item.get('video_versions', []))
        vurl = _clean_url(video.get('url') or item.get('video_url', ''))
        if vurl and not any(v['url'] == vurl for v in result['video_urls']):
            result['video_urls'].append({'url': vurl, 'thumbnail': url,
                                        'shortcode': node.get('shortcode') or node.get('code', '')})


class _Client:
    def __init__(self, deadline, notices, identity):
        self.deadline, self.notices, self.identity = deadline, notices, identity
        self.last_request = 0
        self.proxy = None
        self.session = requests.Session()
        session_id = os.environ.get('IG_SESSION_ID')
        if session_id:
            self.session.cookies.set('sessionid', session_id, domain='.instagram.com')

    def fetch(self, path, **kwargs):
        # Group all media queries together, but allow public HTML after API 401.
        group = 'graphql' if path.startswith('/graphql') else 'api' if path.startswith('/api') else 'html'
        key = (self.identity, self.proxy, group)
        now = time.monotonic()
        until = _COOLDOWNS.get(key, 0)
        if until > now:
            notice = f'Instagram {group} access paused; retry in {math.ceil(until - now)} seconds.'
            if not any(n.startswith(f'Instagram {group} access paused') for n in self.notices):
                self.notices.append(notice)
            return None
        delay = max(0, 1 - (now - self.last_request))
        if now + delay + 0.5 >= self.deadline:
            return None
        time.sleep(delay)
        self.last_request = time.monotonic()
        try:
            response = self.session.request(
                kwargs.pop('method', 'GET'), 'https://www.instagram.com' + path,
                impersonate='chrome', timeout=min(8, self.deadline - self.last_request),
                proxies={'http': self.proxy, 'https': self.proxy} if self.proxy else None,
                headers={'x-ig-app-id': IG_APP_ID, 'referer': 'https://www.instagram.com/',
                         'X-CSRFToken': self.session.cookies.get('csrftoken', '')},
                **kwargs,
            )
            if response.status_code in (401, 403, 429):
                wait = 60
                if response.status_code == 429:
                    value = response.headers.get('Retry-After', '')
                    try:
                        wait = max(60, int(value))
                    except ValueError:
                        try:
                            wait = max(60, int(parsedate_to_datetime(value).timestamp() - time.time()))
                        except (ValueError, TypeError, OverflowError):
                            pass
                _COOLDOWNS[key] = time.monotonic() + wait
                message = ('Instagram is rate-limiting requests' if response.status_code == 429
                           else 'Instagram requires an authorized session for this data')
                self.notices.append(f'{message}; {group} requests paused for {wait} seconds.')
                return None
            if response.status_code == 200 and '/accounts/login' not in str(response.url):
                return response
        except requests.exceptions.RequestException:
            self.notices.append('An Instagram request timed out or failed; showing available results.')
        return None


def run_full_scan(username, budget=55):
    username = username.strip().lstrip('@').lower()
    result = _empty()
    if not re.fullmatch(r'[a-z0-9._]{1,30}', username):
        result['notices'].append('Enter a valid Instagram username (not a profile URL).')
        return result
    session_id = os.environ.get('IG_SESSION_ID', '')
    identity = hashlib.sha256((session_id + '\0' + os.environ.get('INSTAGRAM_PROXY', '')).encode()).hexdigest()
    key = (identity, username)
    # One active scan prevents repeated clicks/users multiplying upstream traffic.
    if not _LOCK.acquire(timeout=1):
        result['notices'].append('Another Full Scan is running. Please wait and try again.')
        return result
    try:
        now = time.monotonic()
        cached = _CACHE.get(key)
        if cached and cached[0] > now:
            result = copy.deepcopy(cached[1])
            result['notices'].append('Showing recent cached results; no duplicate Instagram requests sent.')
            return result
        deadline = now + budget
        client = _Client(deadline, result['notices'], identity)
        try:
            user, nodes = None, []
            response = client.fetch(f'/{username}/')
            if response is None and os.environ.get('INSTAGRAM_PROXY'):
                # Use only the existing configured connection; never rotate exits.
                # Each connection retains its own endpoint cooldown.
                client.proxy = os.environ['INSTAGRAM_PROXY']
                response = client.fetch(f'/{username}/')
            if response is not None:
                user, nodes, result['profile_info'] = _html_data(response.text, username)
            if user is None or 'edge_owner_to_timeline_media' not in user:
                response = client.fetch(f'/api/v1/users/web_profile_info/?username={username}')
                if response is not None:
                    try:
                        data = response.json()
                        api_user = data.get('data', {}).get('user') or data.get('user')
                        if api_user:
                            user = dict(user or {}, **api_user)
                    except ValueError:
                        pass
            if user:
                info = _parse_user_json(user)
                metadata = result['profile_info'] or {}
                # Sparse Relay user objects must not replace real counts with
                # parser defaults (zero is not the same as unknown).
                for field, source, alternate in [('posts', 'edge_owner_to_timeline_media', 'media_count'),
                                                  ('followers', 'edge_followed_by', 'follower_count'),
                                                  ('following', 'edge_follow', 'following_count')]:
                    if source not in user:
                        info[field] = user.get(alternate, metadata.get(field, '?'))
                info['username'] = user.get('username') or username
                result['profile_info'] = dict(metadata, **info)
                # collect_posts merges the API timeline with HTML Relay nodes
                # instead of dropping richer carousel/video data from either.
            nodes = collect_posts(client, user, nodes, bool(session_id))
            available_posts = set()
            # Preserve every discovered post even when later detail requests
            # use up the time budget; images and posts are separate counts.
            for node in nodes:
                before = (len(result['all_post_urls']), len(result['video_urls']))
                _media(node, result)
                if before != (len(result['all_post_urls']), len(result['video_urls'])):
                    available_posts.add(post_key(node))
            for node in nodes:
                code = node.get('shortcode') or node.get('code')
                if not code:
                    continue
                if any(field in node for field in (
                    'like_count', 'comment_count', 'edge_media_preview_like', 'edge_media_to_comment',
                )):
                    normalized = dict(node, shortcode=code)
                    if 'like_count' in node:
                        normalized['edge_media_preview_like'] = {'count': node['like_count']}
                    if 'comment_count' in node:
                        normalized['edge_media_to_comment'] = {'count': node['comment_count']}
                    if isinstance(node.get('caption'), dict):
                        normalized['edge_media_to_caption'] = {'edges': [{'node': node['caption']}]}
                    normalized['is_video'] = node.get('is_video', node.get('media_type') == 2)
                    normalized['taken_at_timestamp'] = node.get('taken_at_timestamp', node.get('taken_at', 0))
                    normalized['display_url'] = node.get('display_url') or node.get('display_uri') or _best(node.get('image_versions2', {}).get('candidates', [])).get('url', '')
                    result['post_engagement'].append(_parse_post_node(normalized))
                if not needs_media_detail(node):
                    continue
                media_before = (len(result['all_post_urls']), len(result['video_urls']))
                # Fetch only missing carousel/video detail, once for both tabs.
                response = client.fetch('/graphql/query', method='POST', data={
                    'doc_id': POST_MEDIA_DOC_ID, 'variables': json.dumps({'shortcode': code}),
                    'server_timestamps': 'true',
                })
                if response is not None:
                    try:
                        items = response.json().get('data', {}).get('xdt_api__v1__media__shortcode__web_info', {}).get('items', [])
                        for item in items:
                            _media(dict(item, shortcode=code), result)
                    except (ValueError, AttributeError):
                        pass
                if media_before == (len(result['all_post_urls']), len(result['video_urls'])):
                    # A code-only Relay node may still have public post metadata.
                    # Do not repeat the blocked GraphQL/API call for each post.
                    response = client.fetch(f'/p/{code}/')
                    if response is not None:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        title = soup.find('meta', attrs={'property': 'og:title'})
                        title_text = title.get('content', '') if title else ''
                        if title_text and not re.search(r'log\s*in|sign\s*up', title_text, re.I):
                            media_node = {'shortcode': code}
                            for prop, field in [('og:image', 'display_url'), ('og:video', 'video_url')]:
                                tag = soup.find('meta', attrs={'property': prop})
                                if tag:
                                    media_node[field] = tag.get('content', '')
                            _media(media_node, result)
                if media_before != (len(result['all_post_urls']), len(result['video_urls'])):
                    available_posts.add(post_key(node))
                if time.monotonic() + 0.5 >= deadline:
                    result['notices'].append('Scan time limit reached; showing partial results.')
                    break
            expected = (result['profile_info'] or {}).get('posts')
            if isinstance(expected, int):
                result['notices'].append(f'Available media from {len(available_posts)} of {expected} profile posts ({len(result["all_post_urls"])} images, {len(result["video_urls"])} videos).')
                if len(available_posts) < expected:
                    result['notices'].append('Not all posts are accessible. A profile post count does not grant access to private or restricted media.')
            else:
                result['notices'].append(f'Available media from {len(available_posts)} posts; the full profile total could not be verified.')
            if any(needs_media_detail(node) for node in nodes):
                result['notices'].append('Some carousel or video details may be incomplete if Instagram denied the media request.')
            result['image_urls'] = list(result['all_post_urls'])
            if session_id and user and user.get('id') and time.monotonic() + 1 < deadline:
                response = client.fetch(f'/api/v1/friendships/{user["id"]}/followers/?count=200')
                if response is not None:
                    try:
                        result['follower_usernames'] = [u['username'] for u in response.json().get('users', []) if u.get('username')]
                    except ValueError:
                        pass
            if not result['follower_usernames']:
                result['notices'].append('Follower list unavailable: requires an authorized Instagram session. Commenters are not counted as followers.')
            if not nodes:
                result['notices'].append('No accessible posts returned. Private content requires permission from the account; rate limits cannot be bypassed.')
        except (ValueError, TypeError, AttributeError, KeyError):
            result['notices'].append('Instagram returned incomplete data; showing available results.')
            result['image_urls'] = list(result['all_post_urls'])
        finally:
            client.session.close()
        has_data = bool(result['profile_info'] or result['all_post_urls'] or result['video_urls'])
        # Bound memory and suppress negative-result retry storms as well.
        _CACHE[key] = (time.monotonic() + (300 if has_data else 60), copy.deepcopy(result))
        _CACHE.move_to_end(key)
        while len(_CACHE) > 128:
            _CACHE.popitem(last=False)
        return result
    finally:
        _LOCK.release()
