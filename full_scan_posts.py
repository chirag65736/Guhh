"""Timeline pagination for Full Scan, using its shared request budget/session."""
import json
import time

USER_QUERY_HASH = '003056d32c2554def87228bc3fd9668a'


def post_key(node):
    return str(node.get('shortcode') or node.get('code') or node.get('pk') or node.get('id') or '')


def merge_post(existing, incoming):
    """Sparse API records must not erase richer embedded carousel/engagement data."""
    merged = dict(existing)
    for field, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(field), dict):
            merged[field] = merge_post(merged[field], value)
        elif value is not None and value != '' and value != []:
            if isinstance(value, list) and isinstance(merged.get(field), list) and len(merged[field]) > len(value):
                continue
            merged[field] = value
    return merged


def collect_posts(client, user, initial_nodes, authorized):
    """Merge pages without a post cap; stop on access denial/deadline/bad cursors.

    Private profiles are paginated only with a user-supplied Instagram session;
    Instagram still decides whether that session has permission to view them.
    """
    nodes = {}
    for node in initial_nodes:
        key = post_key(node)
        if key:
            nodes[key] = merge_post(nodes.get(key, {}), node)
    if not user:
        return list(nodes.values())
    timeline = user.get('edge_owner_to_timeline_media') or user.get('timeline_media') or {}
    for edge in timeline.get('edges', []):
        node = edge.get('node') or {}
        key = post_key(node)
        if key:
            nodes[key] = merge_post(nodes.get(key, {}), node)
    if user.get('is_private') and not authorized:
        client.notices.append('This profile is private. All posts require an Instagram session from the owner or an approved follower; public previews are not the full account.')
        return list(nodes.values())
    user_id = user.get('id') or user.get('pk')
    if not user_id:
        return list(nodes.values())
    page_info = timeline.get('page_info') or {}
    cursor = page_info.get('end_cursor')
    more = bool(page_info.get('has_next_page'))
    total = timeline.get('count', user.get('media_count'))
    # A session feed can supply full carousel/video nodes, including when the
    # profile response exposes a count but no timeline cursor.
    use_feed = authorized and (not nodes or more or (isinstance(total, int) and total > len(nodes)))
    if not more and not use_feed:
        return list(nodes.values())
    if use_feed:
        cursor = None
    seen_cursors = set()
    while time.monotonic() + 0.5 < client.deadline:
        if use_feed:
            params = {'count': 50}
            if cursor:
                params['max_id'] = cursor
            response = client.fetch(f'/api/v1/feed/user/{user_id}/', params=params)
        else:
            if not cursor or cursor in seen_cursors:
                break
            seen_cursors.add(cursor)
            response = client.fetch('/graphql/query/', params={
                'query_hash': USER_QUERY_HASH,
                'variables': json.dumps({'id': str(user_id), 'first': 50, 'after': cursor}),
            })
        if response is None:
            break
        try:
            data = response.json()
            if use_feed:
                batch = data.get('items') or []
                next_cursor = data.get('next_max_id') or data.get('next_max_id_str')
                more = bool(data.get('more_available', next_cursor))
            else:
                media = (data.get('data') or {}).get('user') or {}
                media = media.get('edge_owner_to_timeline_media') or {}
                batch = [edge.get('node') or {} for edge in media.get('edges', [])]
                page_info = media.get('page_info') or {}
                more, next_cursor = bool(page_info.get('has_next_page')), page_info.get('end_cursor')
        except (ValueError, AttributeError, TypeError):
            break
        if not batch:
            break
        for node in batch:
            key = post_key(node)
            if key:
                nodes[key] = merge_post(nodes.get(key, {}), node)
        if not more:
            return list(nodes.values())
        if not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
            break
        if use_feed and cursor:
            seen_cursors.add(cursor)
        cursor = next_cursor
    client.notices.append('Timeline collection is incomplete: Instagram stopped pagination or the scan time limit was reached. These are partial results, not all posts.')
    return list(nodes.values())


def needs_media_detail(node):
    """Avoid an individual request when the timeline already has full media."""
    children = node.get('carousel_media') or [edge.get('node') or {} for edge in
                (node.get('edge_sidecar_to_children') or {}).get('edges', [])]
    if node.get('media_type') == 8 or node.get('__typename') == 'GraphSidecar':
        if not children or (node.get('carousel_media_count') or 0) > len(children):
            return True
    for item in children or [node]:
        image = (item.get('image_versions2') or {}).get('candidates') or item.get('display_url') or item.get('display_uri') or item.get('thumbnail_src')
        video = item.get('video_versions') or item.get('video_url')
        if not image or ((item.get('is_video') or item.get('media_type') == 2) and not video):
            return True
    return False
