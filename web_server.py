"""
Cipher Web Server — full-featured app with auth, payments, gift cards,
invoices, admin panel, and Instagram scraping (unchanged).
"""

import http.server
import socketserver
import urllib.parse
import json
import os

import database as db
import email_sender
import upi_payment
import ai_verifier
from templates import (
    landing_page, login_page, signup_page, dashboard_page,
    payment_page, invoice_page, admin_page, analytics_page,
    scrape_loading_page, terms_page, welcome_page,
)
from igscrapper import (
    fetch_instagram_profile,
    extract_timeline_data,
    extract_highest_resolution_urls,
    generate_gallery_html,
    generate_unsuccessful_html,
)


def _generate_profile_info_html(info, username):
    """Generate HTML page showing Instagram profile info (followers, following, etc.)."""
    followers = info.get('followers', '?')
    following = info.get('following', '?')
    posts = info.get('posts', '?')
    full_name = info.get('full_name', '')
    bio = info.get('bio', '')
    profile_pic = info.get('profile_pic_url', '')
    is_private = info.get('is_private', False)
    is_verified = info.get('is_verified', False)
    external_url = info.get('external_url', '')
    category = info.get('category', '')

    private_badge = '🔒 Private' if is_private else '🌐 Public'
    verified_badge = ' ✓ Verified' if is_verified else ''

    ext_html = f'<div class="info-row"><span class="info-label">🔗 External URL</span><span class="info-value"><a href="{external_url}" target="_blank" style="color:#00e5ff;">{external_url}</a></span></div>' if external_url else ''
    cat_html = f'<div class="info-row"><span class="info-label">🏷️ Category</span><span class="info-value">{category}</span></div>' if category else ''
    pic_html = f'<img src="{profile_pic}" alt="Profile" style="width:120px;height:120px;border-radius:50%;border:3px solid #00e5ff;box-shadow:0 0 20px rgba(0,229,255,.3);object-fit:cover;" />' if profile_pic else ''
    bio_html = f'<div class="info-row"><span class="info-label">📝 Bio</span><span class="info-value" style="white-space:pre-wrap;">{bio}</span></div>' if bio else ''

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cɪᴘʜᴇʀ · Profile Info — @{username}</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        :root {{
            --bg-0:#05060a; --bg-1:#0a0d14; --bg-2:#111624;
            --line:rgba(0,255,255,.15); --cyan:#00e5ff; --magenta:#ff2bd6;
            --green:#00ff9c; --text:#e6f1ff; --dim:#7a8aa3;
        }}
        body {{
            font-family:'Inter',sans-serif; background:var(--bg-0); color:var(--text);
            min-height:100vh; padding:24px 18px;
            background-image:radial-gradient(circle at 15% 10%,rgba(0,229,255,.10),transparent 45%),radial-gradient(circle at 85% 90%,rgba(255,43,214,.10),transparent 45%),linear-gradient(180deg,#05060a 0%,#0a0d14 100%);
            background-attachment:fixed;
        }}
        body::before {{
            content:''; position:fixed; inset:0;
            background-image:linear-gradient(rgba(0,229,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,255,.035) 1px,transparent 1px);
            background-size:40px 40px; pointer-events:none; z-index:0;
        }}
        .container {{
            position:relative; z-index:1; max-width:700px; margin:0 auto;
            background:rgba(10,13,20,.75); border:1px solid var(--line); border-radius:20px;
            padding:36px 30px; backdrop-filter:blur(14px);
            box-shadow:0 0 0 1px rgba(0,229,255,.05),0 30px 80px rgba(0,0,0,.7);
        }}
        .header {{ text-align:center; margin-bottom:30px; }}
        .brand {{
            font-family:'JetBrains Mono',monospace; font-size:2.2rem; font-weight:800;
            letter-spacing:4px; background:linear-gradient(90deg,var(--cyan),var(--magenta));
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
            text-shadow:0 0 40px rgba(0,229,255,.35); margin-bottom:6px;
        }}
        .brand-sub {{
            font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--dim);
            letter-spacing:6px; text-transform:uppercase; margin-bottom:20px;
        }}
        .profile-section {{
            display:flex; flex-direction:column; align-items:center; gap:16px;
            padding:30px 20px; border-radius:16px; margin-bottom:24px;
            background:linear-gradient(135deg,rgba(0,229,255,.06),rgba(255,43,214,.06));
            border:1px solid var(--line);
        }}
        .full-name {{
            font-family:'JetBrains Mono',monospace; font-size:1.4rem; font-weight:700;
            color:var(--text);
        }}
        .username-tag {{
            font-family:'JetBrains Mono',monospace; font-size:.95rem; color:var(--cyan);
        }}
        .badges {{ display:flex; gap:10px; flex-wrap:wrap; justify-content:center; }}
        .badge {{
            font-family:'JetBrains Mono',monospace; font-size:.72rem; letter-spacing:1px;
            padding:6px 14px; border-radius:30px; text-transform:uppercase; font-weight:600;
        }}
        .badge.private {{ color:var(--magenta); border:1px solid rgba(255,43,214,.5); background:rgba(255,43,214,.08); }}
        .badge.public {{ color:var(--green); border:1px solid rgba(0,255,156,.5); background:rgba(0,255,156,.08); }}
        .badge.verified {{ color:#00e5ff; border:1px solid rgba(0,229,255,.5); background:rgba(0,229,255,.08); }}
        .stats-grid {{
            display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:24px;
        }}
        .stat-card {{
            background:rgba(5,6,10,.7); border:1px solid var(--line); border-radius:14px;
            padding:22px 14px; text-align:center;
        }}
        .stat-card .num {{
            font-family:'JetBrains Mono',monospace; font-size:2rem; font-weight:800;
            color:var(--cyan); text-shadow:0 0 20px rgba(0,229,255,.4);
        }}
        .stat-card .lbl {{
            font-size:.72rem; letter-spacing:2px; color:var(--dim);
            text-transform:uppercase; margin-top:6px;
        }}
        .info-section {{
            background:rgba(5,6,10,.5); border:1px solid var(--line); border-radius:14px;
            padding:20px; margin-bottom:16px;
        }}
        .info-row {{
            display:flex; justify-content:space-between; align-items:flex-start;
            padding:12px 0; border-bottom:1px solid rgba(0,229,255,.08); gap:12px;
        }}
        .info-row:last-child {{ border-bottom:none; }}
        .info-label {{
            font-family:'JetBrains Mono',monospace; font-size:.78rem; color:var(--dim);
            letter-spacing:1px; white-space:nowrap;
        }}
        .info-value {{
            font-size:.88rem; color:var(--text); text-align:right; word-break:break-word;
            font-style:italic; font-weight:600;
        }}
        .footer {{
            text-align:center; margin-top:30px; padding-top:20px;
            border-top:1px solid var(--line); color:var(--dim); font-size:.82rem;
        }}
        .footer .brand-mini {{
            font-family:'JetBrains Mono',monospace; color:var(--cyan);
            letter-spacing:3px; font-weight:700; margin-bottom:6px;
        }}
        .footer .made {{
            font-family:'JetBrains Mono',monospace; font-size:.72rem;
            color:var(--magenta); margin-top:4px; letter-spacing:1px;
        }}
        @media(max-width:600px) {{
            .container {{ padding:20px 16px; }}
            .stats-grid {{ grid-template-columns:1fr; }}
            .brand {{ font-size:1.8rem; letter-spacing:2px; }}
            .stat-card .num {{ font-size:1.6rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">Cɪᴘʜᴇʀ</div>
            <div class="brand-sub">Profile Intelligence Engine</div>
        </div>

        <div class="profile-section">
            {pic_html}
            <div class="full-name">{full_name}{verified_badge}</div>
            <div class="username-tag">@{username}</div>
            <div class="badges">
                <span class="badge {'private' if is_private else 'public'}">{private_badge}</span>
                {'<span class="badge verified">✓ Verified</span>' if is_verified else ''}
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="num">{followers:,}</div>
                <div class="lbl">Followers</div>
            </div>
            <div class="stat-card">
                <div class="num">{following:,}</div>
                <div class="lbl">Following</div>
            </div>
            <div class="stat-card">
                <div class="num">{posts:,}</div>
                <div class="lbl">Posts</div>
            </div>
        </div>

        <div class="info-section">
            {bio_html}
            {cat_html}
            {ext_html}
        </div>

        <div class="footer">
            <div class="brand-mini">Cɪᴘʜᴇʀ</div>
            <div>Instagram Profile Intelligence — POC</div>
            <div class="made">◈ Made by Ryon · CipherXPortal ◈</div>
        </div>
    </div>
</body>
</html>
    """
from private_scraper import scrape_private_profile
from stealth_scraper import scrape_stealth_profile
from profile_info_scraper import scrape_profile_info
from followers_scraper import scrape_followers
from post_engagement_scraper import scrape_post_engagement
from private_posts_scraper import scrape_private_posts


def _generate_combined_html(username, image_urls, profile_info, follower_usernames, post_engagement=None, all_post_urls=None):
    """Generate a single page showing ALL scan results: stealth gallery,
    profile info, followers list, post engagement (likes/comments), and
    all private post images — combined into one page."""
    # ── Profile Info section ──
    info_html = ''
    if profile_info:
        followers = profile_info.get('followers', '?')
        following = profile_info.get('following', '?')
        posts = profile_info.get('posts', '?')
        full_name = profile_info.get('full_name', '')
        bio = profile_info.get('bio', '')
        profile_pic = profile_info.get('profile_pic_url', '')
        is_private = profile_info.get('is_private', False)
        is_verified = profile_info.get('is_verified', False)
        private_badge = '🔒 Private' if is_private else '🌐 Public'
        verified_badge = ' ✓' if is_verified else ''
        pic_html = f'<img src="{profile_pic}" alt="Profile" style="width:80px;height:80px;border-radius:50%;border:2px solid #00e5ff;object-fit:cover;" />' if profile_pic else ''
        bio_html = f'<div style="font-size:.82rem;color:var(--dim);margin-top:8px;font-style:italic;">{bio}</div>' if bio else ''
        info_html = f"""
        <div class="result-section" id="section-info">
            <div class="section-header" style="color:#00ff9c;">🔍 Profile Info</div>
            <div class="info-card">
                <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;justify-content:center;">
                    {pic_html}
                    <div>
                        <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;color:var(--text);">{full_name}{verified_badge}</div>
                        <div style="font-family:'JetBrains Mono',monospace;font-size:.85rem;color:var(--cyan);">@{username}</div>
                        <div style="font-size:.72rem;color:{'#ff2bd6' if is_private else '#00ff9c'};margin-top:4px;">{private_badge}</div>
                    </div>
                </div>
                {bio_html}
                <div class="mini-stats">
                    <div class="mini-stat"><span class="mini-num">{followers:,}</span><span class="mini-lbl">Followers</span></div>
                    <div class="mini-stat"><span class="mini-num">{following:,}</span><span class="mini-lbl">Following</span></div>
                    <div class="mini-stat"><span class="mini-num">{posts:,}</span><span class="mini-lbl">Posts</span></div>
                </div>
            </div>
        </div>"""
    else:
        info_html = """
        <div class="result-section" id="section-info">
            <div class="section-header" style="color:#00ff9c;">🔍 Profile Info</div>
            <div class="result-empty">⚠ Could not extract profile info.</div>
        </div>"""

    # ── Stealth gallery section ──
    if image_urls:
        gallery_items = ''
        for url in image_urls:
            gallery_items += f'<div class="gallery-item"><img src="{url}" loading="lazy" alt="post" /><a href="{url}" download class="gallery-dl">⬇</a></div>'
        gallery_html = f"""
        <div class="result-section" id="section-stealth">
            <div class="section-header" style="color:var(--gold);">🛡 Stealth Scan — {len(image_urls)} Posts</div>
            <div class="gallery-grid">{gallery_items}</div>
        </div>"""
    else:
        gallery_html = """
        <div class="result-section" id="section-stealth">
            <div class="section-header" style="color:var(--gold);">🛡 Stealth Scan</div>
            <div class="result-empty">⚠ No posts found via stealth scan.</div>
        </div>"""

    # ── Followers list section ──
    if follower_usernames:
        follower_items = ''
        for i, uname in enumerate(follower_usernames, 1):
            follower_items += f'<a href="https://www.instagram.com/{uname}/" target="_blank" class="follower-item"><span class="follower-num">{i}</span><span class="follower-avatar">{uname[0].upper() if uname else "?"}</span><span class="follower-username">@{uname}</span><span class="follower-arrow">→</span></a>'
        followers_html = f"""
        <div class="result-section" id="section-followers">
            <div class="section-header" style="color:#7c3aed;">👥 Followers List — {len(follower_usernames)} Found</div>
            <div class="followers-list">{follower_items}</div>
        </div>"""
    else:
        followers_html = """
        <div class="result-section" id="section-followers">
            <div class="section-header" style="color:#7c3aed;">👥 Followers List</div>
            <div class="result-empty">⚠ Could not extract followers list.</div>
        </div>"""

    # ── Post engagement section ──
    if post_engagement:
        post_cards = ''
        total_likes = 0
        total_comments = 0
        for p in post_engagement:
            total_likes += p.get('like_count', 0)
            total_comments += p.get('comment_count', 0)
            caption_short = (p.get('caption', '') or '')[:120]
            if len(p.get('caption', '') or '') > 120:
                caption_short += '…'
            ts = p.get('timestamp', '')
            like_n = p.get('like_count', 0)
            cmt_n = p.get('comment_count', 0)
            img_url = p.get('display_url', '')
            sc = p.get('shortcode', '')
            post_link = f'https://www.instagram.com/p/{sc}/' if sc else '#'

            thumb = f'<img src="{img_url}" loading="lazy" alt="post" style="width:100%;border-radius:10px;aspect-ratio:1;object-fit:cover;border:1px solid var(--line);" />' if img_url else ''
            video_badge = '<span style="font-size:.68rem;padding:3px 8px;border-radius:6px;background:rgba(255,43,214,.15);color:#ff2bd6;">▶ Reel</span>' if p.get('is_video') else ''

            # Comment text list
            comments_html = ''
            for c in p.get('comments', [])[:5]:
                ctext = (c.get('text', '') or '')[:80]
                if len(c.get('text', '') or '') > 80:
                    ctext += '…'
                comments_html += f'<div style="display:flex;gap:8px;padding:8px 0;border-bottom:1px solid rgba(0,229,255,.06);"><span style="font-family:JetBrains Mono,monospace;font-size:.78rem;color:var(--cyan);font-weight:700;white-space:nowrap;">@{c.get("username","?")}</span><span style="font-size:.82rem;color:var(--text);font-style:italic;">{ctext}</span></div>'
            if p.get('comments'):
                comments_html = f'<div style="margin-top:12px;padding:8px 12px;background:rgba(5,6,10,.5);border-radius:10px;border:1px solid rgba(0,229,255,.08);">{comments_html}</div>'
            elif cmt_n > 0:
                comments_html = f'<div style="margin-top:10px;font-size:.78rem;color:var(--dim);font-style:italic;">💬 {cmt_n} comments (load post page to view text)</div>'

            # Likers list
            likers_html = ''
            likers = p.get('likers', [])
            if likers:
                liker_chips = ''
                for l in likers[:12]:
                    liker_chips += f'<a href="https://www.instagram.com/{l}/" target="_blank" style="display:inline-block;padding:4px 10px;margin:3px;border-radius:20px;font-family:JetBrains Mono,monospace;font-size:.72rem;color:var(--cyan);text-decoration:none;border:1px solid rgba(0,229,255,.2);background:rgba(0,229,255,.05);">@{l}</a>'
                more = f'<span style="font-size:.72rem;color:var(--dim);">+{len(likers)-12} more</span>' if len(likers) > 12 else ''
                likers_html = f'<div style="margin-top:10px;"><div style="font-size:.72rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">❤ LIKERS</div>{liker_chips}{more}</div>'

            post_cards += f"""
            <div class="post-card">
                <div class="post-card-thumb">{thumb}</div>
                <div class="post-card-body">
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
                        <span style="font-family:JetBrains Mono,monospace;font-size:.72rem;color:var(--dim);">{ts}</span>
                        {video_badge}
                    </div>
                    <div class="post-engagement-row">
                        <span class="eng-badge likes">❤ {like_n:,}</span>
                        <span class="eng-badge comments">💬 {cmt_n:,}</span>
                        <a href="{post_link}" target="_blank" class="eng-badge view">↗ View</a>
                    </div>
                    {f'<div style="font-size:.82rem;color:var(--text);margin-top:10px;font-style:italic;line-height:1.5;">{caption_short}</div>' if caption_short else ''}
                    {comments_html}
                    {likers_html}
                </div>
            </div>"""

        engagement_html = f"""
        <div class="result-section" id="section-engagement">
            <div class="section-header" style="color:#ff6b35;">📊 Post Engagement — {len(post_engagement)} Posts</div>
            <div class="eng-summary">
                <div class="eng-summary-stat"><span class="eng-summary-num">{total_likes:,}</span><span class="eng-summary-lbl">Total Likes</span></div>
                <div class="eng-summary-stat"><span class="eng-summary-num">{total_comments:,}</span><span class="eng-summary-lbl">Total Comments</span></div>
                <div class="eng-summary-stat"><span class="eng-summary-num">{len(post_engagement)}</span><span class="eng-summary-lbl">Posts Analyzed</span></div>
            </div>
            <div class="posts-list">{post_cards}</div>
        </div>"""
    else:
        engagement_html = """
        <div class="result-section" id="section-engagement">
            <div class="section-header" style="color:#ff6b35;">📊 Post Engagement</div>
            <div class="result-empty">⚠ Could not extract post engagement data.</div>
        </div>"""

    # ── All Posts (private posts via GraphQL) section ──
    if all_post_urls:
        all_posts_items = ''
        for url in all_post_urls:
            is_vid = '.mp4' in url.lower() or '/video' in url.lower()
            if is_vid:
                all_posts_items += f'<div class="gallery-item"><video src="{url}" controls style="width:100%;height:100%;object-fit:cover;"></video><a href="{url}" download class="gallery-dl">⬇</a></div>'
            else:
                all_posts_items += f'<div class="gallery-item"><img src="{url}" loading="lazy" alt="post" /><a href="{url}" download class="gallery-dl">⬇</a></div>'
        all_posts_html = f"""
        <div class="result-section" id="section-allposts">
            <div class="section-header" style="color:#00e5ff;">📸 All Posts — {len(all_post_urls)} Images (GraphQL)</div>
            <div style="font-size:.78rem;color:var(--dim);margin-bottom:16px;font-style:italic;">Extracted via GraphQL post query — includes all carousel images at highest resolution.</div>
            <div class="gallery-grid">{all_posts_items}</div>
        </div>"""
    else:
        all_posts_html = """
        <div class="result-section" id="section-allposts">
            <div class="section-header" style="color:#00e5ff;">📸 All Posts</div>
            <div class="result-empty">⚠ Could not extract post images (API may be rate limited).</div>
        </div>"""

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cɪᴘʜᴇʀ · Full Scan — @{username}</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        :root {{
            --bg-0:#05060a; --bg-1:#0a0d14; --bg-2:#111624;
            --line:rgba(0,255,255,.15); --cyan:#00e5ff; --magenta:#ff2bd6;
            --green:#00ff9c; --gold:#ffd700; --text:#e6f1ff; --dim:#7a8aa3;
        }}
        body {{
            font-family:'Inter',sans-serif; background:var(--bg-0); color:var(--text);
            min-height:100vh; padding:24px 18px; font-weight:bold; font-style:italic;
            background-image:radial-gradient(circle at 15% 10%,rgba(0,229,255,.10),transparent 45%),radial-gradient(circle at 85% 90%,rgba(255,43,214,.10),transparent 45%),linear-gradient(180deg,#05060a 0%,#0a0d14 100%);
            background-attachment:fixed;
        }}
        body::before {{
            content:''; position:fixed; inset:0;
            background-image:linear-gradient(rgba(0,229,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,255,.035) 1px,transparent 1px);
            background-size:40px 40px; pointer-events:none; z-index:0;
        }}
        .container {{
            position:relative; z-index:1; max-width:900px; margin:0 auto;
        }}
        .header {{ text-align:center; margin-bottom:28px; }}
        .brand {{
            font-family:'JetBrains Mono',monospace; font-size:2.2rem; font-weight:800;
            letter-spacing:4px; background:linear-gradient(90deg,var(--cyan),var(--magenta));
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
            text-shadow:0 0 40px rgba(0,229,255,.35); margin-bottom:6px;
        }}
        .brand-sub {{
            font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--dim);
            letter-spacing:6px; text-transform:uppercase; margin-bottom:12px;
        }}
        .target-box {{
            display:inline-flex; align-items:center; gap:10px;
            padding:10px 24px; border-radius:30px;
            background:linear-gradient(135deg,rgba(0,229,255,.06),rgba(255,43,214,.06));
            border:1px solid var(--line);
        }}
        .target-box .label {{ font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--dim); letter-spacing:1px; }}
        .target-box .name {{ font-family:'JetBrains Mono',monospace; font-size:.95rem; color:var(--cyan); font-weight:700; }}
        /* Tab navigation */
        .tabs {{
            display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-bottom:24px;
            position:sticky; top:0; z-index:10; padding:12px 0;
            background:rgba(5,6,10,.85); backdrop-filter:blur(10px); border-radius:12px;
            border:1px solid var(--line);
        }}
        .tab {{
            font-family:'JetBrains Mono',monospace; font-size:.78rem; font-weight:700;
            padding:10px 20px; border-radius:10px; cursor:pointer;
            border:1px solid var(--line); background:rgba(10,13,20,.6);
            color:var(--dim); transition:all .25s; letter-spacing:1px;
        }}
        .tab:hover {{ color:var(--text); border-color:var(--cyan); }}
        .tab.active {{ color:#05060a; font-weight:800; }}
        .tab.active[data-tab="info"] {{ background:#00ff9c; border-color:#00ff9c; }}
        .tab.active[data-tab="stealth"] {{ background:var(--gold); border-color:var(--gold); }}
        .tab.active[data-tab="followers"] {{ background:#7c3aed; border-color:#7c3aed; color:#fff; }}
        .tab.active[data-tab="engagement"] {{ background:#ff6b35; border-color:#ff6b35; color:#05060a; }}
        .tab.active[data-tab="allposts"] {{ background:var(--cyan); border-color:var(--cyan); color:#05060a; }}
        /* Result sections */
        .result-section {{
            background:rgba(10,13,20,.75); border:1px solid var(--line); border-radius:18px;
            padding:28px 24px; margin-bottom:24px; backdrop-filter:blur(14px);
            box-shadow:0 0 0 1px rgba(0,229,255,.05),0 20px 60px rgba(0,0,0,.5);
        }}
        .result-section.hidden {{ display:none; }}
        .section-header {{
            font-family:'JetBrains Mono',monospace; font-size:1.1rem; font-weight:800;
            letter-spacing:2px; margin-bottom:20px; padding-bottom:12px;
            border-bottom:1px solid var(--line);
        }}
        .result-empty {{
            text-align:center; padding:30px; color:var(--dim); font-size:.88rem;
            background:rgba(5,6,10,.5); border-radius:12px;
        }}
        /* Profile info card */
        .info-card {{
            text-align:center; padding:24px 16px;
            background:linear-gradient(135deg,rgba(0,229,255,.04),rgba(255,43,214,.04));
            border:1px solid var(--line); border-radius:14px;
        }}
        .mini-stats {{
            display:flex; justify-content:center; gap:30px; margin-top:20px; flex-wrap:wrap;
        }}
        .mini-stat {{ display:flex; flex-direction:column; align-items:center; gap:4px; }}
        .mini-num {{ font-family:'JetBrains Mono',monospace; font-size:1.6rem; font-weight:800; color:var(--cyan); }}
        .mini-lbl {{ font-family:'JetBrains Mono',monospace; font-size:.68rem; color:var(--dim); letter-spacing:2px; text-transform:uppercase; }}
        /* Gallery grid */
        .gallery-grid {{
            display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:14px;
        }}
        .gallery-item {{
            position:relative; border-radius:12px; overflow:hidden;
            border:1px solid var(--line); aspect-ratio:1; background:var(--bg-1);
        }}
        .gallery-item img {{ width:100%; height:100%; object-fit:cover; display:block; transition:transform .3s; }}
        .gallery-item:hover img {{ transform:scale(1.05); }}
        .gallery-dl {{
            position:absolute; bottom:8px; right:8px; width:32px; height:32px;
            border-radius:50%; background:rgba(0,229,255,.9); color:#05060a;
            display:flex; align-items:center; justify-content:center;
            text-decoration:none; font-size:1rem; font-weight:800;
            opacity:0; transition:opacity .25s;
        }}
        .gallery-item:hover .gallery-dl {{ opacity:1; }}
        /* Followers list */
        .followers-list {{
            display:flex; flex-direction:column; gap:8px; max-height:500px; overflow-y:auto; padding-right:4px;
        }}
        .followers-list::-webkit-scrollbar {{ width:6px; }}
        .followers-list::-webkit-scrollbar-track {{ background:rgba(0,229,255,.05); border-radius:3px; }}
        .followers-list::-webkit-scrollbar-thumb {{ background:rgba(0,229,255,.3); border-radius:3px; }}
        .follower-item {{
            display:flex; align-items:center; gap:12px; padding:12px 16px;
            border-radius:12px; text-decoration:none; color:var(--text);
            background:rgba(5,6,10,.5); border:1px solid rgba(0,229,255,.08);
            transition:all .25s;
        }}
        .follower-item:hover {{ border-color:var(--cyan); background:rgba(0,229,255,.06); transform:translateX(4px); }}
        .follower-num {{ font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--dim); min-width:28px; text-align:right; }}
        .follower-avatar {{
            width:36px; height:36px; border-radius:50%; flex-shrink:0;
            display:flex; align-items:center; justify-content:center;
            font-family:'JetBrains Mono',monospace; font-size:.85rem; font-weight:800;
            color:#05060a; background:linear-gradient(135deg,var(--cyan),var(--magenta));
        }}
        .follower-username {{ font-family:'JetBrains Mono',monospace; font-size:.9rem; color:var(--text); font-weight:600; flex:1; }}
        .follower-arrow {{ color:var(--dim); font-size:1.1rem; transition:color .25s; }}
        .follower-item:hover .follower-arrow {{ color:var(--cyan); }}
        /* Footer */
        .footer {{
            text-align:center; margin-top:30px; padding-top:20px;
            border-top:1px solid var(--line); color:var(--dim); font-size:.82rem;
        }}
        .footer .brand-mini {{ font-family:'JetBrains Mono',monospace; color:var(--cyan); letter-spacing:3px; font-weight:700; margin-bottom:6px; }}
        .footer .made {{ font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--magenta); margin-top:4px; letter-spacing:1px; }}
        /* Post engagement */
        .eng-summary {{
            display:flex; justify-content:center; gap:30px; margin-bottom:24px; flex-wrap:wrap;
            padding:20px; border-radius:14px;
            background:linear-gradient(135deg,rgba(255,107,53,.06),rgba(255,43,214,.04));
            border:1px solid rgba(255,107,53,.2);
        }}
        .eng-summary-stat {{ display:flex; flex-direction:column; align-items:center; gap:4px; }}
        .eng-summary-num {{ font-family:'JetBrains Mono',monospace; font-size:1.6rem; font-weight:800; color:#ff6b35; text-shadow:0 0 15px rgba(255,107,53,.4); }}
        .eng-summary-lbl {{ font-family:'JetBrains Mono',monospace; font-size:.68rem; color:var(--dim); letter-spacing:2px; text-transform:uppercase; }}
        .posts-list {{ display:flex; flex-direction:column; gap:16px; }}
        .post-card {{
            display:flex; gap:16px; padding:16px; border-radius:14px;
            background:rgba(5,6,10,.5); border:1px solid rgba(0,229,255,.08);
            transition:border-color .25s;
        }}
        .post-card:hover {{ border-color:rgba(255,107,53,.3); }}
        .post-card-thumb {{ flex-shrink:0; width:120px; }}
        .post-card-body {{ flex:1; min-width:0; }}
        .post-engagement-row {{ display:flex; gap:8px; flex-wrap:wrap; }}
        .eng-badge {{
            font-family:'JetBrains Mono',monospace; font-size:.75rem; font-weight:700;
            padding:5px 12px; border-radius:8px; text-decoration:none; letter-spacing:1px;
        }}
        .eng-badge.likes {{ color:#ff6b35; background:rgba(255,107,53,.1); border:1px solid rgba(255,107,53,.3); }}
        .eng-badge.comments {{ color:var(--cyan); background:rgba(0,229,255,.08); border:1px solid rgba(0,229,255,.2); }}
        .eng-badge.view {{ color:var(--green); background:rgba(0,255,156,.08); border:1px solid rgba(0,255,156,.2); }}
        .eng-badge.view:hover {{ background:rgba(0,255,156,.15); }}
        @media(max-width:600px) {{
            .container {{ padding:0; }}
            .gallery-grid {{ grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:10px; }}
            .mini-stats {{ gap:20px; }}
            .mini-num {{ font-size:1.3rem; }}
            .tab {{ font-size:.72rem; padding:8px 14px; }}
            .follower-item {{ padding:10px 12px; gap:8px; }}
            .follower-avatar {{ width:32px; height:32px; font-size:.78rem; }}
            .post-card {{ flex-direction:column; gap:12px; }}
            .post-card-thumb {{ width:100%; }}
            .eng-summary {{ gap:16px; }}
            .eng-summary-num {{ font-size:1.3rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">Cɪᴘʜᴇʀ</div>
            <div class="brand-sub">Full Scan — All Results</div>
            <div style="margin-top:16px;">
                <div class="target-box">
                    <span class="label">Target:</span>
                    <span class="name">@{username}</span>
                </div>
            </div>
        </div>

        <!-- Tab navigation -->
        <div class="tabs">
            <div class="tab active" data-tab="info" onclick="showTab('info')">🔍 Profile Info</div>
            <div class="tab" data-tab="stealth" onclick="showTab('stealth')">🛡 Stealth ({len(image_urls) if image_urls else 0})</div>
            <div class="tab" data-tab="followers" onclick="showTab('followers')">👥 Followers ({len(follower_usernames) if follower_usernames else 0})</div>
            <div class="tab" data-tab="engagement" onclick="showTab('engagement')">📊 Engagement ({len(post_engagement) if post_engagement else 0})</div>
            <div class="tab" data-tab="allposts" onclick="showTab('allposts')">📸 All Posts ({len(all_post_urls) if all_post_urls else 0})</div>
        </div>

        {info_html}
        {gallery_html}
        {followers_html}
        {engagement_html}
        {all_posts_html}

        <div class="footer">
            <div class="brand-mini">Cɪᴘʜᴇʀ</div>
            <div>Full Scan — All-in-One Intelligence</div>
            <div class="made">◈ Made by Ryon · CipherXPortal ◈</div>
        </div>
    </div>
    <script>
    function showTab(tab) {{
        document.querySelectorAll('.tab').forEach(function(t) {{ t.classList.remove('active'); }});
        document.querySelector('.tab[data-tab="' + tab + '"]').classList.add('active');
        document.querySelectorAll('.result-section').forEach(function(s) {{ s.classList.add('hidden'); }});
        document.getElementById('section-' + tab).classList.remove('hidden');
        window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}
    // Show only the active section initially
    document.addEventListener('DOMContentLoaded', function() {{
        document.querySelectorAll('.result-section').forEach(function(s) {{ s.classList.add('hidden'); }});
        document.getElementById('section-info').classList.remove('hidden');
    }});
    </script>
</body>
</html>
    """


def _generate_followers_html(usernames, target_username):
    """Generate HTML page showing a list of follower usernames."""
    count = len(usernames)
    # Build follower list items
    items_html = ''
    for i, uname in enumerate(usernames, 1):
        items_html += f"""
            <a href="https://www.instagram.com/{uname}/" target="_blank" class="follower-item">
                <span class="follower-num">{i}</span>
                <span class="follower-avatar">{uname[0].upper() if uname else '?'}</span>
                <span class="follower-username">@{uname}</span>
                <span class="follower-arrow">→</span>
            </a>"""

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cɪᴘʜᴇʀ · Followers — @{target_username}</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        :root {{
            --bg-0:#05060a; --bg-1:#0a0d14; --bg-2:#111624;
            --line:rgba(0,255,255,.15); --cyan:#00e5ff; --magenta:#ff2bd6;
            --green:#00ff9c; --text:#e6f1ff; --dim:#7a8aa3;
        }}
        body {{
            font-family:'Inter',sans-serif; background:var(--bg-0); color:var(--text);
            min-height:100vh; padding:24px 18px;
            background-image:radial-gradient(circle at 15% 10%,rgba(0,229,255,.10),transparent 45%),radial-gradient(circle at 85% 90%,rgba(255,43,214,.10),transparent 45%),linear-gradient(180deg,#05060a 0%,#0a0d14 100%);
            background-attachment:fixed;
        }}
        body::before {{
            content:''; position:fixed; inset:0;
            background-image:linear-gradient(rgba(0,229,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,255,.035) 1px,transparent 1px);
            background-size:40px 40px; pointer-events:none; z-index:0;
        }}
        .container {{
            position:relative; z-index:1; max-width:700px; margin:0 auto;
            background:rgba(10,13,20,.75); border:1px solid var(--line); border-radius:20px;
            padding:36px 30px; backdrop-filter:blur(14px);
            box-shadow:0 0 0 1px rgba(0,229,255,.05),0 30px 80px rgba(0,0,0,.7);
        }}
        .header {{ text-align:center; margin-bottom:28px; }}
        .brand {{
            font-family:'JetBrains Mono',monospace; font-size:2.2rem; font-weight:800;
            letter-spacing:4px; background:linear-gradient(90deg,var(--cyan),var(--magenta));
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
            text-shadow:0 0 40px rgba(0,229,255,.35); margin-bottom:6px;
        }}
        .brand-sub {{
            font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--dim);
            letter-spacing:6px; text-transform:uppercase; margin-bottom:20px;
        }}
        .target-box {{
            display:flex; align-items:center; justify-content:center; gap:10px;
            padding:14px 20px; border-radius:12px; margin-bottom:20px;
            background:linear-gradient(135deg,rgba(0,229,255,.06),rgba(255,43,214,.06));
            border:1px solid var(--line);
        }}
        .target-box .label {{
            font-family:'JetBrains Mono',monospace; font-size:.78rem; color:var(--dim);
            letter-spacing:1px;
        }}
        .target-box .name {{
            font-family:'JetBrains Mono',monospace; font-size:1rem; color:var(--cyan);
            font-weight:700;
        }}
        .count-badge {{
            display:inline-flex; align-items:center; gap:8px;
            padding:10px 24px; border-radius:30px; margin-bottom:24px;
            background:rgba(0,255,156,.08); border:1px solid rgba(0,255,156,.3);
        }}
        .count-badge .num {{
            font-family:'JetBrains Mono',monospace; font-size:1.4rem; font-weight:800;
            color:var(--green); text-shadow:0 0 15px rgba(0,255,156,.4);
        }}
        .count-badge .lbl {{
            font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--dim);
            letter-spacing:2px; text-transform:uppercase;
        }}
        .followers-list {{
            display:flex; flex-direction:column; gap:8px;
            max-height:600px; overflow-y:auto; padding-right:4px;
        }}
        .followers-list::-webkit-scrollbar {{ width:6px; }}
        .followers-list::-webkit-scrollbar-track {{ background:rgba(0,229,255,.05); border-radius:3px; }}
        .followers-list::-webkit-scrollbar-thumb {{ background:rgba(0,229,255,.3); border-radius:3px; }}
        .follower-item {{
            display:flex; align-items:center; gap:12px; padding:12px 16px;
            border-radius:12px; text-decoration:none; color:var(--text);
            background:rgba(5,6,10,.5); border:1px solid rgba(0,229,255,.08);
            transition:all .25s;
        }}
        .follower-item:hover {{
            border-color:var(--cyan); background:rgba(0,229,255,.06);
            transform:translateX(4px);
        }}
        .follower-num {{
            font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--dim);
            min-width:28px; text-align:right;
        }}
        .follower-avatar {{
            width:36px; height:36px; border-radius:50%; flex-shrink:0;
            display:flex; align-items:center; justify-content:center;
            font-family:'JetBrains Mono',monospace; font-size:.85rem; font-weight:800;
            color:#05060a; background:linear-gradient(135deg,var(--cyan),var(--magenta));
        }}
        .follower-username {{
            font-family:'JetBrains Mono',monospace; font-size:.9rem; color:var(--text);
            font-weight:600; flex:1;
        }}
        .follower-arrow {{
            color:var(--dim); font-size:1.1rem; transition:color .25s;
        }}
        .follower-item:hover .follower-arrow {{ color:var(--cyan); }}
        .footer {{
            text-align:center; margin-top:30px; padding-top:20px;
            border-top:1px solid var(--line); color:var(--dim); font-size:.82rem;
        }}
        .footer .brand-mini {{
            font-family:'JetBrains Mono',monospace; color:var(--cyan);
            letter-spacing:3px; font-weight:700; margin-bottom:6px;
        }}
        .footer .made {{
            font-family:'JetBrains Mono',monospace; font-size:.72rem;
            color:var(--magenta); margin-top:4px; letter-spacing:1px;
        }}
        @media(max-width:600px) {{
            .container {{ padding:20px 16px; }}
            .brand {{ font-size:1.8rem; letter-spacing:2px; }}
            .follower-item {{ padding:10px 12px; gap:8px; }}
            .follower-avatar {{ width:32px; height:32px; font-size:.78rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">Cɪᴘʜᴇʀ</div>
            <div class="brand-sub">Followers Intelligence</div>
        </div>

        <div class="target-box">
            <span class="label">Target:</span>
            <span class="name">@{target_username}</span>
        </div>

        <div style="text-align:center;">
            <div class="count-badge">
                <span class="num">{count}</span>
                <span class="lbl">Followers Found</span>
            </div>
        </div>

        <div class="followers-list">
            {items_html}
        </div>

        <div class="footer">
            <div class="brand-mini">Cɪᴘʜᴇʀ</div>
            <div>Instagram Followers Intelligence — POC</div>
            <div class="made">◈ Made by Ryon · CipherXPortal ◈</div>
        </div>
    </div>
</body>
</html>
    """

PORT = 8080

BACK_BUTTON = """
<div style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:9999;">
  <a href="/dashboard" style="display:inline-flex;align-items:center;gap:8px;padding:14px 30px;background:linear-gradient(135deg,#00e5ff,#ff2bd6);color:#05060a;font-family:'JetBrains Mono',monospace;font-size:.85rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;text-decoration:none;border-radius:12px;box-shadow:0 6px 24px rgba(0,229,255,.35);transition:all .3s;">⟵ Back to Dashboard</a>
</div>
"""

# JS injected into scrape-result pages to count downloads without
# changing the scraper. Uses fetch keepalive so the beacon survives
# the browser's download navigation.
DOWNLOAD_TRACKER = """
<script>
document.addEventListener('click', function(e) {
    var btn = e.target.closest('.download-btn');
    if (btn) {
        var url = btn.getAttribute('href') || '';
        fetch('/track-download', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'url=' + encodeURIComponent(url),
            keepalive: true
        }).catch(function(){});
    }
}, true);
</script>
"""


def inject_back_button(html):
    """Inject a floating back button + download tracker before </body>."""
    extra = BACK_BUTTON + DOWNLOAD_TRACKER
    if '</body>' in html:
        return html.replace('</body>', extra + '</body>', 1)
    return html + extra


# ── Scraping pipeline (unchanged) ─────────────────────────────

def run_scrape(username):
    response = fetch_instagram_profile(username)
    if not response:
        return generate_unsuccessful_html(username)
    timeline_data = extract_timeline_data(response.text)
    if not timeline_data:
        return generate_unsuccessful_html(username)
    image_urls = extract_highest_resolution_urls(timeline_data)
    if not image_urls:
        return generate_unsuccessful_html(username)
    return generate_gallery_html(image_urls, username)


# ── Handler ───────────────────────────────────────────────────

class CipherHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        user = self._current_user()

        # ── Public routes ──
        if path == '/':
            self._serve_html(landing_page(user, db.get_reviews()))
            return

        if path == '/login':
            if user:
                self._redirect('/dashboard')
                return
            self._serve_html(login_page())
            return

        if path == '/signup':
            if user:
                self._redirect('/dashboard')
                return
            self._serve_html(signup_page())
            return

        if path == '/welcome':
            if not user:
                self._redirect('/login')
                return
            self._serve_html(welcome_page(user))
            return

        if path == '/terms':
            self._serve_html(terms_page(user))
            return

        if path == '/logout':
            token = self._cookie_token()
            if token:
                db.delete_session(token)
            self.send_response(302)
            self.send_header('Set-Cookie', 'session=; Path=/; Max-Age=0')
            self.send_header('Location', '/')
            self.end_headers()
            return

        # ── Auth required ──
        if path == '/dashboard':
            if not user:
                self._redirect('/login')
                return
            flash = params.get('flash', [None])[0]
            self._serve_html(dashboard_page(user, flash, db.get_reviews()))
            return

        if path == '/scrape':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            if not db.deduct_credit(user['id']):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('No credits! Buy credits first.'))
                return
            print(f"[*] Quick scan requested for @{username} by {user['email']}", flush=True)
            db.log_activity(user['id'], 'search', username)
            # Return animated loading page; JS fetches /scrape-result
            self._serve_html(scrape_loading_page(user, username, mode='quick'))
            return

        if path == '/scrape-result':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            print(f"[*] Quick scan executing for @{username}", flush=True)
            html = run_scrape(username)
            html = inject_back_button(html)
            self._serve_html(html)
            return

        if path == '/scrape-private':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            if not db.deduct_credits(user['id'], 2):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Need 2 credits for Deep Scan! Buy credits first.'))
                return
            print(f"[*] Private deep scan requested for @{username} by {user['email']}", flush=True)
            db.log_activity(user['id'], 'search', f'{username} (deep)')
            # Return animated loading page; JS fetches /scrape-private-result
            self._serve_html(scrape_loading_page(user, username, mode='private'))
            return

        if path == '/scrape-private-result':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            print(f"[*] Private deep scan executing for @{username}", flush=True)
            image_urls = scrape_private_profile(username, max_posts=60)
            if not image_urls:
                html = generate_unsuccessful_html(username)
            else:
                html = generate_gallery_html(image_urls, username)
            html = inject_back_button(html)
            self._serve_html(html)
            return

        if path == '/scrape-stealth':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            if not db.deduct_credits(user['id'], 3):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Need 3 credits for Stealth Scan! Buy credits first.'))
                return
            print(f"[*] Stealth scan requested for @{username} by {user['email']}", flush=True)
            db.log_activity(user['id'], 'search', f'{username} (stealth)')
            # Return animated loading page; JS fetches /scrape-stealth-result
            self._serve_html(scrape_loading_page(user, username, mode='stealth'))
            return

        if path == '/scrape-stealth-result':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            print(f"[*] Stealth scan executing for @{username}", flush=True)
            image_urls = scrape_stealth_profile(username, max_posts=80)
            if not image_urls:
                html = generate_unsuccessful_html(username)
            else:
                html = generate_gallery_html(image_urls, username)
            html = inject_back_button(html)
            self._serve_html(html)
            return

        if path == '/scrape-all':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            if not db.deduct_credits(user['id'], 6):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Need 6 credits for Full Scan! Buy credits first.'))
                return
            print(f"[*] Full scan (all-in-one) requested for @{username} by {user['email']}", flush=True)
            db.log_activity(user['id'], 'search', f'{username} (full-all)')
            self._serve_html(scrape_loading_page(user, username, mode='all'))
            return

        if path == '/scrape-all-result':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            print(f"[*] Full scan (all-in-one) executing for @{username}", flush=True)
            # Run all four scrapers
            print(f"[*]   → Stealth scan for @{username}", flush=True)
            image_urls = scrape_stealth_profile(username, max_posts=80)
            print(f"[*]   → Profile info scan for @{username}", flush=True)
            profile_info = scrape_profile_info(username)
            print(f"[*]   → Followers list scan for @{username}", flush=True)
            follower_usernames = scrape_followers(username, max_followers=200)
            print(f"[*]   → Post engagement scan for @{username}", flush=True)
            post_engagement = scrape_post_engagement(username, max_posts=12, enrich_comments=True)
            print(f"[*]   → All posts (GraphQL) scan for @{username}", flush=True)
            # Reuse shortcodes from post_engagement to avoid duplicate API call
            engagement_shortcodes = [p.get('shortcode') for p in post_engagement if p.get('shortcode')]
            all_post_urls = scrape_private_posts(username, max_posts=20, shortcodes=engagement_shortcodes)
            html = _generate_combined_html(username, image_urls, profile_info, follower_usernames, post_engagement, all_post_urls)
            html = inject_back_button(html)
            self._serve_html(html)
            return

        if path == '/scrape-profile-info':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            if not db.deduct_credits(user['id'], 1):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Need 1 credit for Profile Info Scan! Buy credits first.'))
                return
            print(f"[*] Profile info scan requested for @{username} by {user['email']}", flush=True)
            db.log_activity(user['id'], 'search', f'{username} (info)')
            self._serve_html(scrape_loading_page(user, username, mode='info'))
            return

        if path == '/scrape-followers':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            if not db.deduct_credits(user['id'], 2):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Need 2 credits for Followers List! Buy credits first.'))
                return
            print(f"[*] Followers list scan requested for @{username} by {user['email']}", flush=True)
            db.log_activity(user['id'], 'search', f'{username} (followers)')
            self._serve_html(scrape_loading_page(user, username, mode='followers'))
            return

        if path == '/scrape-followers-result':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            print(f"[*] Followers list scan executing for @{username}", flush=True)
            usernames = scrape_followers(username, max_followers=200)
            if not usernames:
                html = generate_unsuccessful_html(username)
            else:
                html = _generate_followers_html(usernames, username)
            html = inject_back_button(html)
            self._serve_html(html)
            return

        if path == '/scrape-profile-info-result':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            print(f"[*] Profile info scan executing for @{username}", flush=True)
            info = scrape_profile_info(username)
            if not info:
                html = generate_unsuccessful_html(username)
            else:
                html = _generate_profile_info_html(info, username)
            html = inject_back_button(html)
            self._serve_html(html)
            return

        if path == '/payment':
            if not user:
                self._redirect('/login')
                return
            ptype = params.get('type', [''])[0]
            plan_key = params.get('plan', [None])[0]
            self._serve_html(payment_page(user, ptype, plan_key, db.get_payment_methods()))
            return

        if path == '/invoice':
            if not user:
                self._redirect('/login')
                return
            inv_id = params.get('id', [''])[0]
            try:
                inv_id = int(inv_id)
            except ValueError:
                inv_id = 0
            invoice = db.get_invoice(inv_id)
            if invoice and invoice['user_id'] != user['id'] and not user['is_admin']:
                invoice = None
            self._serve_html(invoice_page(user, invoice))
            return

        # ── Admin ──
        if path == '/admin':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            flash = params.get('flash', [None])[0]
            self._serve_html(admin_page(
                user, db.get_stats(), db.get_all_users(),
                db.get_all_payments(), db.get_all_gift_cards(),
                db.get_all_invoices(), db.get_all_payment_methods(),
                db.get_all_upi_payments(), flash
            ))
            return

        if path == '/analytics':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            self._serve_html(analytics_page(
                user, db.get_analytics_summary(), db.get_analytics()
            ))
            return

        if path == '/screenshot':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            name = params.get('name', [''])[0]
            filepath = upi_payment.get_screenshot_path(name)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filepath)[1].lower()
                mime = 'image/png' if ext == '.png' else 'image/jpeg'
                with open(filepath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._serve_html('<div class="card">Screenshot not found.</div>')
            return

        # ── 404 ──
        self._serve_html(landing_page(user))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._parse_post_body()
        user = self._current_user()

        if path == '/login':
            email = body.get('email', [''])[0].strip()
            password = body.get('password', [''])[0]
            u = db.get_user_by_email(email)
            if u and db.verify_password(password, u['password_hash']):
                token = db.create_session(u['id'])
                self._redirect('/dashboard', cookie=f'session={token}; Path=/; HttpOnly')
            else:
                self._serve_html(login_page('Invalid email or password.'))
            return

        if path == '/signup':
            name = body.get('name', [''])[0].strip()
            email = body.get('email', [''])[0].strip()
            password = body.get('password', [''])[0]
            if not name or not email or not password:
                self._serve_html(signup_page('All fields are required.'))
                return
            if db.create_user(email, password, name):
                u = db.get_user_by_email(email)
                token = db.create_session(u['id'])
                self._redirect('/welcome', cookie=f'session={token}; Path=/; HttpOnly')
            else:
                self._serve_html(signup_page('Email already registered.'))
            return

        if path == '/redeem':
            if not user:
                self._redirect('/login')
                return
            code = body.get('code', [''])[0].strip().upper()
            value = db.redeem_gift_card(code, user['id'])
            if value:
                self._redirect(f'/dashboard?flash=ok:' + urllib.parse.quote(f'Gift card redeemed! +{value} credits.'))
            else:
                self._redirect(f'/dashboard?flash=error:' + urllib.parse.quote('Invalid or already redeemed gift card.'))
            return

        if path == '/process-payment':
            if not user:
                self._redirect('/login')
                return
            ptype = body.get('payment_type', [''])[0]
            plan_key = body.get('plan_key', [''])[0] or None
            try:
                amount = float(body.get('amount', ['0'])[0])
                credits = int(body.get('credits', ['0'])[0])
            except ValueError:
                self._redirect('/dashboard')
                return

            # Record payment
            payment_id = db.create_payment(user['id'], amount, ptype, plan_key, credits)
            # Add credits
            db.add_credits(user['id'], credits)

            # Build invoice description
            if ptype == 'per_post':
                desc = f'1 Post Credit'
            elif ptype == 'plan' and plan_key in db.PLANS:
                plan = db.PLANS[plan_key]
                credits_label = 'Unlimited' if plan['credits'] >= 999 else f"{plan['credits']} Credits"
                desc = f'{plan["name"]} Plan — {credits_label} ({plan["duration"]})'
            else:
                desc = f'Credits Purchase'

            inv_id, inv_num = db.create_invoice(user['id'], payment_id, amount, desc)

            # Send invoice email automatically
            email_sender.send_invoice_email(
                user['email'], inv_num, amount, desc, user['name']
            )

            self._redirect(f'/invoice?id={inv_id}')
            return

        if path == '/track-download':
            if not user:
                self.send_response(204)
                self.end_headers()
                return
            url = body.get('url', [''])[0]
            db.log_activity(user['id'], 'download', url)
            self.send_response(204)
            self.end_headers()
            return

        if path == '/submit-review':
            name = body.get('name', [''])[0].strip()
            text = body.get('text', [''])[0].strip()
            try:
                rating = int(body.get('rating', ['5'])[0])
            except ValueError:
                rating = 5
            if not name or not text:
                self._redirect('/?flash=error:' + urllib.parse.quote('Name and review text are required.'))
                return
            rating = max(1, min(5, rating))
            db.add_review(name, rating, text)
            # Redirect back to where the user came from
            referer = self.headers.get('Referer', '/')
            self._redirect(referer)
            return

        if path == '/verify-upi':
            if not user:
                self._redirect('/login')
                return
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Invalid form submission.'))
                return
            # Extract boundary
            boundary = None
            for part in content_type.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part[len('boundary='):]
            if not boundary:
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Missing form boundary.'))
                return
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            fields, files = upi_payment.parse_multipart(body, boundary)

            try:
                amount = float(fields.get('amount', '0'))
                credits = int(fields.get('credits', '0'))
            except ValueError:
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Invalid payment data.'))
                return
            ptype = fields.get('payment_type', '')
            plan_key = fields.get('plan_key', '') or None
            utr = fields.get('utr', '').strip()
            sender_name = fields.get('sender_name', '').strip()
            screenshot = files.get('screenshot')

            # Validate
            if not sender_name:
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Please enter your name.'))
                return
            valid, err = upi_payment.validate_utr(utr)
            if not valid:
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote(err))
                return
            if not screenshot or not screenshot.get('data'):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Please upload a payment screenshot.'))
                return
            if len(screenshot['data']) > upi_payment.MAX_FILE_SIZE:
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('Screenshot too large (max 10MB).'))
                return
            if db.check_utr_exists(utr):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('This UTR has already been submitted.'))
                return

            # Save screenshot privately
            filename = upi_payment.save_screenshot(
                screenshot['data'], screenshot.get('filename', 'ss.png'), user['id']
            )
            screenshot_path = upi_payment.get_screenshot_path(filename)

            # Create UPI payment record
            payment_id = db.create_upi_payment(
                user['id'], amount, credits, ptype, plan_key, utr, sender_name, filename
            )

            # Run AI verification
            ai_result = ai_verifier.verify_screenshot(screenshot_path, amount, utr)
            db.update_upi_ai_result(
                payment_id,
                ai_result['recommendation'],
                ai_result['reason'],
                ai_result['confidence']
            )

            print(f"[*] UPI payment submitted by {user['email']}: UTR={utr}, AI={ai_result['recommendation']}", flush=True)

            if ai_result['recommendation'] == 'verified':
                # Auto-approve: add credits + create invoice instantly
                result = db.verify_upi_payment(payment_id)
                if result:
                    email_sender.send_invoice_email(
                        result['user_email'], result['invoice_number'],
                        result['amount'], result['details'], result['user_name']
                    )
                    print(f"[*] UPI payment AUTO-APPROVED for {user['email']}, credits added instantly (UTR={utr})", flush=True)
                    self._redirect(f"/invoice?id={result['invoice_id']}")
                    return
                flash_msg = 'AI verified your payment! Credits added to your account.'
            elif ai_result['recommendation'] == 'suspicious':
                flash_msg = 'AI flagged your payment for review. Admin will verify manually.'
            elif ai_result['recommendation'] == 'rejected':
                flash_msg = 'AI could not verify your payment. Admin will review manually.'
            else:
                flash_msg = 'Payment proof submitted! Admin will verify and add your credits shortly.'

            self._redirect('/dashboard?flash=ok:' + urllib.parse.quote(flash_msg))
            return

        if path == '/admin/verify-upi':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            try:
                payment_id = int(body.get('payment_id', ['0'])[0])
            except ValueError:
                payment_id = 0
            if payment_id > 0:
                result = db.verify_upi_payment(payment_id)
                if result:
                    email_sender.send_invoice_email(
                        result['user_email'], result['invoice_number'],
                        result['amount'], result['details'], result['user_name']
                    )
                    self._redirect('/admin?flash=ok:' + urllib.parse.quote('UPI payment verified. Credits added & invoice emailed.'))
                else:
                    self._redirect('/admin?flash=error:' + urllib.parse.quote('Payment not found or already processed.'))
            else:
                self._redirect('/admin?flash=error:Invalid payment.')
            return

        if path == '/admin/reject-upi':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            try:
                payment_id = int(body.get('payment_id', ['0'])[0])
            except ValueError:
                payment_id = 0
            if payment_id > 0:
                db.reject_upi_payment(payment_id)
                self._redirect('/admin?flash=ok:' + urllib.parse.quote('UPI payment rejected.'))
            else:
                self._redirect('/admin?flash=error:Invalid payment.')
            return

        if path == '/admin/create-giftcard':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            try:
                value = int(body.get('value', ['0'])[0])
            except ValueError:
                value = 0
            if value > 0:
                code = db.create_gift_card(value)
                self._redirect(f'/admin?flash=ok:' + urllib.parse.quote(f'Gift card created: {code}'))
            else:
                self._redirect('/admin?flash=error:Invalid value.')
            return

        if path == '/admin/add-credits':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            try:
                target_id = int(body.get('user_id', ['0'])[0])
                amount = int(body.get('amount', ['0'])[0])
            except ValueError:
                self._redirect('/admin?flash=error:Invalid input.')
                return
            if amount > 0 and target_id > 0:
                db.add_credits(target_id, amount)
                target = db.get_user_by_id(target_id)
                name = target['name'] if target else 'User'
                self._redirect(f'/admin?flash=ok:' + urllib.parse.quote(f'Added {amount} credits to {name}.'))
            else:
                self._redirect('/admin?flash=error:Invalid amount.')
            return

        if path == '/admin/add-payment-method':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            name = body.get('name', [''])[0].strip()
            details = body.get('details', [''])[0].strip()
            icon = body.get('icon', ['💰'])[0].strip() or '💰'
            if name and details:
                db.add_payment_method(name, details, icon)
                self._redirect(f'/admin?flash=ok:' + urllib.parse.quote(f'Payment method "{name}" added.'))
            else:
                self._redirect('/admin?flash=error:Name and details required.')
            return

        if path == '/admin/delete-payment-method':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            try:
                method_id = int(body.get('method_id', ['0'])[0])
            except ValueError:
                method_id = 0
            if method_id > 0:
                db.delete_payment_method(method_id)
                self._redirect('/admin?flash=ok:' + urllib.parse.quote('Payment method removed.'))
            else:
                self._redirect('/admin?flash=error:Invalid method.')
            return

        self._redirect('/')

    # ── Helpers ──────────────────────────────────────────────

    def _serve_html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _redirect(self, location, cookie=None):
        self.send_response(302)
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.send_header('Location', location)
        self.end_headers()

    def _parse_post_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        return urllib.parse.parse_qs(body)

    def _cookie_token(self):
        cookie_header = self.headers.get('Cookie', '')
        for cookie in cookie_header.split(';'):
            parts = cookie.strip().split('=', 1)
            if len(parts) == 2 and parts[0] == 'session':
                return parts[1]
        return None

    def _current_user(self):
        token = self._cookie_token()
        return db.get_session_user(token) if token else None

    def log_message(self, *args, **kwargs):
        pass


class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    db.init_db()
    with ReusableTCPServer(('0.0.0.0', PORT), CipherHandler) as httpd:
        print(f"Cipher web server listening on 0.0.0.0:{PORT}")
        httpd.serve_forever()
