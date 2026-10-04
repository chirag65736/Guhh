"""Verified engagement extraction for Full Scan; never guess user relationships."""
import time

from post_engagement_scraper import _parse_post_node


def media_pk(node):
    value = str(node.get('pk') or node.get('id') or '').split('_', 1)[0]
    if value.isdigit():
        return value
    code = node.get('shortcode') or node.get('code') or ''
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    value = 0
    for char in code:
        if char not in alphabet:
            return ''
        value = value * 64 + alphabet.index(char)
    return str(value) if code else ''


def parse_engagement(node):
    code = node.get('shortcode') or node.get('code')
    if not code:
        return None
    normalized = dict(node, shortcode=code)
    for field, edge in [('like_count', 'edge_media_preview_like'),
                        ('comment_count', 'edge_media_to_comment')]:
        if field in node:
            normalized[edge] = {'count': node[field] or 0}
    if 'edge_media_preview_like' not in normalized:
        normalized['edge_media_preview_like'] = node.get('edge_liked_by') or {}
    if 'edge_media_to_comment' not in normalized:
        normalized['edge_media_to_comment'] = node.get('edge_media_to_parent_comment') or {}
    caption = node.get('caption')
    if isinstance(caption, dict):
        normalized['edge_media_to_caption'] = {'edges': [{'node': caption}]}
    elif isinstance(caption, str):
        normalized['edge_media_to_caption'] = {'edges': [{'node': {'text': caption}}]}
    normalized['is_video'] = node.get('is_video', node.get('media_type') == 2)
    normalized['taken_at_timestamp'] = node.get('taken_at_timestamp') or node.get('taken_at') or 0
    candidates = (node.get('image_versions2') or {}).get('candidates') or []
    image = max(candidates, key=lambda v: (v.get('width') or 0) * (v.get('height') or 0), default={})
    normalized['display_url'] = node.get('display_url') or node.get('display_uri') or image.get('url', '')
    entry = _parse_post_node(normalized)
    comments = list(node.get('preview_comments') or [])
    likers = list(node.get('likers') or [])
    for field in ('edge_media_to_comment', 'edge_media_to_parent_comment'):
        comments.extend(edge.get('node') or {} for edge in (node.get(field) or {}).get('edges', []))
    for field in ('edge_liked_by', 'edge_media_preview_like'):
        likers.extend(edge.get('node') or {} for edge in (node.get(field) or {}).get('edges', []))
    entry['comments'] = clean_comments(comments)
    entry['likers'] = list(dict.fromkeys(u['username'] for u in likers if isinstance(u, dict) and u.get('username')))
    return entry


def clean_comments(items):
    result, seen = [], set()
    for item in items:
        owner = item.get('user') or item.get('owner') or {}
        name, text = owner.get('username'), item.get('text', '')
        key = (name, text)
        if name and key not in seen:
            seen.add(key)
            result.append({'username': name, 'text': text})
    return result


def fetch_followers(client, user_id):
    names, seen = [], set()
    cursor = None
    while time.monotonic() + 0.5 < client.deadline:
        params = {'count': 200}
        if cursor:
            params['max_id'] = cursor
        response = client.fetch(f'/api/v1/friendships/{user_id}/followers/', params=params)
        if response is None:
            break
        try:
            data = response.json()
            names.extend(u['username'] for u in data.get('users', []) if u.get('username'))
            next_cursor = data.get('next_max_id')
        except (ValueError, AttributeError, TypeError):
            break
        if not next_cursor or next_cursor in seen:
            return list(dict.fromkeys(names))
        seen.add(next_cursor)
        cursor = next_cursor
    client.notices.append('Follower list is partial or unavailable: Instagram denied access or the scan budget ended.')
    return list(dict.fromkeys(names))


def enrich_entries(client, entries, nodes):
    """Round-robin pages so one popular post cannot starve all other posts."""
    by_code = {n.get('shortcode') or n.get('code'): n for n in nodes}
    jobs = []
    comment_cursors = set()
    for entry in entries:
        pk = media_pk(by_code.get(entry['shortcode'], {}))
        if pk:
            node = by_code.get(entry['shortcode'], {})
            fields = {'comments': ('comment_count', 'edge_media_to_comment', 'edge_media_to_parent_comment'),
                      'likers': ('like_count', 'edge_liked_by', 'edge_media_preview_like')}
            jobs.extend((entry, pk, kind, None) for kind in ('comments', 'likers')
                        if not any(field in node for field in fields[kind])
                        or entry.get('comment_count' if kind == 'comments' else 'like_count', 0) > len(entry[kind]))
    while jobs and time.monotonic() + 0.5 < client.deadline:
        entry, pk, kind, cursor = jobs.pop(0)
        params = {'min_id': cursor} if cursor else {}
        response = client.fetch(f'/api/v1/media/{pk}/{kind}/', params=params)
        if response is None:
            continue
        try:
            data = response.json()
            if kind == 'likers':
                entry['likers'] = list(dict.fromkeys(entry['likers'] + [u['username'] for u in data.get('users', []) if u.get('username')]))
            else:
                comments = clean_comments(data.get('comments') or [])
                seen = {(c['username'], c['text']) for c in entry['comments']}
                entry['comments'].extend(c for c in comments if (c['username'], c['text']) not in seen)
                next_cursor = data.get('next_min_id')
                if data.get('has_more_comments') and next_cursor and next_cursor != cursor:
                    job_key = (entry['shortcode'], next_cursor)
                    if job_key not in comment_cursors:
                        comment_cursors.add(job_key)
                        jobs.append((entry, pk, kind, next_cursor))
        except (ValueError, AttributeError, TypeError):
            continue
    client.notices.append('Liker and comment usernames show only returned data; Instagram restrictions or the time budget can leave these lists incomplete.')
