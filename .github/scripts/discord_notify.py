"""Post Caliper releases and public issue updates to Discord (GitHub Actions, standard library only).

Reads the triggering event from GITHUB_EVENT_PATH; event text is never interpolated into a
shell, and mentions are disabled, so issue titles cannot ping @everyone or run commands.
Secrets: DISCORD_WEBHOOK_RELEASES (releases) and DISCORD_WEBHOOK_ISSUES (issues; falls back
to the releases webhook). A missing webhook is reported and skipped, never a failure.
Local preview: python discord_notify.py --print EVENT_NAME EVENT.json
"""
import json, os, re, sys, urllib.error, urllib.request

SECTIONS = ("What's new", 'Improvements', 'Fixes')
LIMIT = 3900  # Discord embed descriptions allow 4096 characters

def sections(body):
    """The release-note sections worth announcing, plus the installer SHA-256."""
    body = (body or '').replace('\r\n', '\n')
    parts = []
    for name in SECTIONS:
        m = re.search(r'^##[ \t]+' + re.escape(name) + r'[ \t]*\n(.*?)(?=^##[ \t]|^\*\*Caliper-Setup\.exe SHA-256|\Z)', body, re.M | re.S)
        text = m.group(1).strip() if m else ''
        if text and text.lower().rstrip('.') != '- none':
            parts.append(f'**{name}**\n{text}')
    sha = re.search(r'Caliper-Setup\.exe SHA-256:\*\*\s*`([0-9a-f]{64})`', body)
    text = '\n\n'.join(parts)
    if len(text) > LIMIT:
        text = text[:LIMIT].rsplit('\n', 1)[0] + '\n…'
    return text, sha.group(1) if sha else None

def release_message(event):
    r = event['release']
    if r.get('draft') or r.get('prerelease'):
        return None
    text, sha = sections(r.get('body'))
    setup = next((a['browser_download_url'] for a in r.get('assets', []) if a['name'] == 'Caliper-Setup.exe'), None)
    fields = []
    if setup:
        fields.append({'name': 'Download', 'value': f'[Caliper-Setup.exe]({setup})', 'inline': True})
    if sha:
        fields.append({'name': 'SHA-256', 'value': f'`{sha}`', 'inline': False})
    name = r.get('name') or r['tag_name']
    return 'DISCORD_WEBHOOK_RELEASES', {'embeds': [{'title': f'{name} is out', 'url': r['html_url'], 'color': 0xF0A04B,
            'description': (text + '\n\n' if text else '') + f"[Full release notes]({r['html_url']})", 'fields': fields}]}

def issue_message(event):
    action, issue = event['action'], event['issue']
    if action == 'closed':
        heading, color = ('Resolved', 0x3BA55C) if issue.get('state_reason') != 'not_planned' else ('Closed, not planned', 0x747F8D)
    elif action == 'reopened':
        heading, color = 'Reopened', 0xF0B232
    elif action == 'opened':
        heading, color = 'New issue', 0x5865F2
    else:
        return None
    body = re.sub(r'<!--.*?-->', '', issue.get('body') or '', flags=re.S).strip()
    if len(body) > 300:
        body = body[:300].rsplit(' ', 1)[0] + '…'
    labels = ', '.join(l['name'] for l in issue.get('labels', []))
    embed = {'author': {'name': heading}, 'title': f"#{issue['number']} {issue['title']}"[:256], 'url': issue['html_url'],
             'color': color, 'description': body if action == 'opened' else ''}
    if labels:
        embed['footer'] = {'text': labels[:200]}
    return 'DISCORD_WEBHOOK_ISSUES', {'embeds': [embed]}

def message(name, event):
    if name == 'release' and event.get('action') == 'published':
        return release_message(event)
    if name == 'issues':
        return issue_message(event)
    return None

def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--print':
        with open(sys.argv[3], encoding='utf-8') as f:
            print(json.dumps(message(sys.argv[2], json.load(f)), ensure_ascii=False, indent=2))
        return 0
    with open(os.environ['GITHUB_EVENT_PATH'], encoding='utf-8') as f:
        found = message(os.environ['GITHUB_EVENT_NAME'], json.load(f))
    if not found:
        print('Nothing to announce for this event.')
        return 0
    secret, payload = found
    url = os.environ.get(secret) or os.environ.get('DISCORD_WEBHOOK_RELEASES')
    if not url:
        print(f'{secret} is not configured; nothing was posted.')
        return 0
    payload.update({'username': 'Caliper', 'allowed_mentions': {'parse': []}})
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'caliper-discord-notify'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print('Posted to Discord:', response.status)
    except urllib.error.HTTPError as e:
        print('Discord rejected the message:', e.code, e.read()[:300])
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
