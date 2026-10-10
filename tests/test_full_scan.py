"""Full Scan regressions; fixtures do not claim real Instagram access."""
import json
import time
import unittest
from unittest.mock import patch

from full_scan import _html_data, run_full_scan, _CACHE
from full_scan_posts import collect_posts, merge_post
from full_scan_engagement import parse_engagement, enrich_entries, fetch_followers, media_pk


class Response:
    def __init__(self, data):
        self.data = data
    def json(self):
        return self.data


class Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.deadline = time.monotonic() + 30
        self.notices = []
        self.calls = []
    def fetch(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return next(self.responses, None)


class FullScanTests(unittest.TestCase):
    def test_sparse_merge_keeps_carousel_and_counts(self):
        rich = {'carousel_media': [{'id': 1}, {'id': 2}], 'edge_liked_by': {'count': 7, 'edges': [{'node': {'username': 'liker'}}]}}
        merged = merge_post(rich, {'carousel_media': [], 'edge_liked_by': {'edges': []}})
        self.assertEqual(len(merged['carousel_media']), 2)
        self.assertEqual(merged['edge_liked_by']['count'], 7)
        self.assertEqual(len(merged['edge_liked_by']['edges']), 1)

    def test_authorized_feed_pages_over_twenty_posts(self):
        nodes = [{'code': f'post{i}'} for i in range(60)]
        client = Client([Response({'items': nodes[:40], 'more_available': True, 'next_max_id': 'next'}), Response({'items': nodes[40:], 'more_available': False})])
        user = {'pk': 123, 'media_count': 60, 'edge_owner_to_timeline_media': {'page_info': {'has_next_page': True, 'end_cursor': 'old'}}}
        self.assertEqual(len(collect_posts(client, user, [], True)), 60)
        self.assertTrue(all('/feed/user/' in path for path, _ in client.calls))
        self.assertEqual(client.calls[1][1]['params']['max_id'], 'next')

    def test_private_without_permission_does_not_paginate(self):
        client = Client([])
        self.assertEqual(collect_posts(client, {'id': 1, 'is_private': True}, [{'code': 'preview'}], False), [{'code': 'preview'}])
        self.assertEqual(client.calls, [])

    def test_embedded_engagement_is_preserved(self):
        entry = parse_engagement({'shortcode': 'ABC', 'edge_liked_by': {'count': 3, 'edges': [{'node': {'username': 'actual_liker'}}]}, 'edge_media_to_parent_comment': {'count': 1, 'edges': [{'node': {'owner': {'username': 'actual_commenter'}, 'text': 'hello'}}]}})
        self.assertEqual(entry['like_count'], 3)
        self.assertEqual(entry['comment_count'], 1)
        self.assertEqual(entry['likers'], ['actual_liker'])
        self.assertEqual(entry['comments'], [{'username': 'actual_commenter', 'text': 'hello'}])

    def test_comment_and_liker_requests_and_pagination(self):
        client = Client([Response({'comments': [{'user': {'username': 'c1'}, 'text': 'one'}], 'has_more_comments': True, 'next_min_id': 'two'}), Response({'users': [{'username': 'l1'}]}), Response({'comments': [{'user': {'username': 'c2'}, 'text': 'two'}]})])
        entry = parse_engagement({'code': 'ABC', 'like_count': 1, 'comment_count': 2})
        enrich_entries(client, [entry], [{'code': 'ABC', 'id': '123_456'}])
        self.assertEqual(entry['likers'], ['l1'])
        self.assertEqual([c['username'] for c in entry['comments']], ['c1', 'c2'])
        self.assertEqual(client.calls[2][1]['params'], {'min_id': 'two'})
        self.assertEqual(media_pk({'code': 'B'}), '1')

    def test_followers_only_from_friendships(self):
        client = Client([Response({'users': [{'username': 'f1'}], 'next_max_id': 'next'}), Response({'users': [{'username': 'f2'}]})])
        self.assertEqual(fetch_followers(client, 123), ['f1', 'f2'])
        self.assertEqual(client.calls[1][1]['params']['max_id'], 'next')

    def test_relay_owner_id_and_unrelated_users(self):
        data = {'user': {'username': 'target', 'id': '12', 'is_private': False}, 'posts': [{'code': 'ABC', 'owner': {'id': '12'}, 'display_uri': 'image'}, {'code': 'WRONG', 'owner': {'id': '99'}}]}
        _, nodes, _ = _html_data('<script type="application/json">' + json.dumps(data) + '</script>', 'target')
        self.assertEqual([n['code'] for n in nodes], ['ABC'])
        self.assertEqual(parse_engagement(nodes[0])['likers'], [])

    def test_denied_post_response_does_not_crash(self):
        client = Client([Response({'items': []})])
        client.session = type('Session', (), {'close': lambda self: None})()
        _CACHE.clear()
        html = '<script type="application/json">' + json.dumps({'username': 'target', 'is_private': False, 'id': '12', 'edge_owner_to_timeline_media': {'count': 1, 'edges': [{'node': {'shortcode': 'ABC'}}]}}) + '</script>'
        response = type('HTML', (), {'text': html})()
        client.responses = iter([response, None, None])
        with patch('full_scan._Client', return_value=client), patch.dict('os.environ', {'IG_SESSION_ID': ''}):
            result = run_full_scan('target')
        self.assertEqual(len(result['post_engagement']), 1)
        self.assertEqual(result['follower_usernames'], [])
        self.assertFalse(any('returned incomplete data' in n for n in result['notices']))


if __name__ == '__main__':
    unittest.main()
