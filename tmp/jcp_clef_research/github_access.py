import json
import os
import subprocess
import urllib.error
import urllib.request

GIT = r'C:\Users\100OS\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\mingw64\bin\git.exe'
EXEC = 'C:/Users/100OS/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/mingw64/bin'
REPO = 'boml41195-sys/jcp-clef'


def credentials():
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
    result = subprocess.run([GIT, '--exec-path=' + EXEC, 'credential', 'fill'],
        input='protocol=https\nhost=github.com\n\n', text=True, capture_output=True, env=env, timeout=30)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    return values.get('password')


def request_api(path, token=None, body=None, method=None):
    headers = {'User-Agent': 'JCP-applicability-study', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    data = None if body is None else json.dumps(body).encode('utf-8')
    if data is not None:
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request('https://api.github.com' + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


if __name__ == '__main__':
    token = credentials()
    output = {'credential_available': bool(token)}
    try:
        repo = request_api('/repos/' + REPO, token)
        output.update(repository=repo['full_name'], default_branch=repo['default_branch'], size=repo['size'],
                      permissions=repo.get('permissions'), private=repo['private'])
        if token:
            user = request_api('/user', token)
            output['authenticated_as'] = user['login']
    except urllib.error.HTTPError as exc:
        output['http_status'] = exc.code
    print(json.dumps(output, ensure_ascii=False, indent=2))
