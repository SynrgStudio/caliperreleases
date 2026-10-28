"""Post releases and public issue updates to Discord (GitHub Actions, standard library only).

Shared by Caliper (SynrgStudio/caliperreleases) and Breadslicer (breadslicer-app/breadslicer);
the authoritative copy lives in calipersource/community/caliperreleases. Per repository:
PRODUCT (display name, default: repository name) and SETUP_ASSET (installer shown as the
download link; default: the first .exe, else .msi/.zip/.dmg/.AppImage asset).
Reads the triggering event from GITHUB_EVENT_PATH; event text is never interpolated into a
shell, and mentions are disabled, so issue titles cannot ping @everyone or run commands.
Secrets: DISCORD_WEBHOOK_RELEASES (releases) and DISCORD_WEBHOOK_ISSUES (issues; falls back
to the releases webhook). A missing webhook is reported and skipped, never a failure.
Local preview: python discord_notify.py --print EVENT_NAME EVENT.json
"""
import json, os, re, sys, urllib.error, urllib.request

SECTIONS = ("What's new", 'Improvements', 'Fixes')
LIMIT = 3900  # Discord embed descriptions allow 4096 characters
INSTALLERS = ('.exe', '.msi', '.zip', '.dmg', '.appimage')

def product():
    return os.environ.get('PRODUCT') or os.environ.get('GITHUB_REPOSITORY', '/Caliper').split('/')[-1].capitalize()

def trim(text):
    return text if len(text) <= LIMIT else text[:LIMIT].rsplit('\n', 1)[0] + '\n…'

def sections(body):
    """What's new / Improvements / Fixes when present (Caliper's contract), else the whole body
    without its title; plus the first SHA-256 found."""
    body = (body or '').replace('\r\n', '\n')
    parts = []
    for name in SECTIONS:
        m = re.search(r'^##[ \t]+' + re.escape(name) + r'[ \t]*\n(.*?)(?=^##[ \t]|^\*\*[^\n]*SHA-256|\Z)', body, re.M | re.S)
        text = m.group(1).strip() if m else ''
        if text and text.lower().rstrip('.') != '- none':
            parts.append(f'**{name}**\n{text}')
    sha = re.search(r'SHA-256:?\**\s*`([0-9a-fA-F]{64})`', body)
    if not parts:
        rest = re.sub(r'\A#[ \t][^\n]*\n', '', body.strip()).strip()
        parts = [rest] if rest else []
    return trim('\n\n'.join(parts)), sha.group(1).lower() if sha else None

def setup_asset(assets):
    wanted = os.environ.get('SETUP_ASSET')
    if wanted:
        return next((a for a in assets if a['name'] == wanted), None)
    for suffix in INSTALLERS:
        found = next((a for a in assets if a['name'].lower().endswith(suffix)), None)
        if found:
            return found
    return None

def release_message(event):
    r = event['release']
    if r.get('draft') or r.get('prerelease'):
        return None
    text, sha = sections(r.get('body'))
    setup = setup_asset(r.get('assets', []))
    fields = []
    if setup:
        fields.append({'name': 'Download', 'value': f"[{setup['name']}]({setup['browser_download_url']})", 'inline': True})
    if sha:
        fields.append({'name': 'SHA-256', 'value': f'`{sha}`', 'inline': False})
    name = r.get('name') or f"{product()} {r['tag_name']}"
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

def manual_message(what, latest):
    """Manual run (Actions → Discord → Run workflow): re-announce the latest release, or test the issues channel."""
    if what == 'test-issues':
        repo = os.environ.get('GITHUB_REPOSITORY', 'SynrgStudio/caliperreleases')
        return 'DISCORD_WEBHOOK_ISSUES', {'embeds': [{'author': {'name': 'Connected'}, 'title': f'{product()} issue updates will appear here',
                'url': f'https://github.com/{repo}/issues', 'color': 0x5865F2,
                'description': 'New reports and resolved issues from the public tracker are posted in this channel.'}]}
    return release_message({'release': latest()}) if what == 'latest-release' else None

def latest_release():
    request = urllib.request.Request(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/releases/latest",
                                     headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'discord-notify',
                                              **({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']} if os.environ.get('GITHUB_TOKEN') else {})})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit('No published release yet; nothing to announce.') from None
        raise

def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--print':
        with open(sys.argv[3], encoding='utf-8') as f:
            print(json.dumps(message(sys.argv[2], json.load(f)), ensure_ascii=False, indent=2))
        return 0
    if os.environ['GITHUB_EVENT_NAME'] == 'workflow_dispatch':
        found = manual_message(os.environ.get('WHAT', ''), latest_release)
    else:
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
    payload.update({'username': product(), 'allowed_mentions': {'parse': []}})
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'discord-notify'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print('Posted to Discord:', response.status)
    except urllib.error.HTTPError as e:
        print('Discord rejected the message:', e.code, e.read()[:300])
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
