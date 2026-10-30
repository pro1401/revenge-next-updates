"""Mirror verified production artifacts from the official Revenge Next main branch."""
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.request
import zipfile

UPSTREAM = 'revenge-mod/revenge-bundle-next'
REPOSITORY = 'https://revenge-mod.github.io/revenge-community-plugins'
GENERATOR_VERSION = 2

def order_plugins(plugins):
    by_id = {p['id']: p for p in plugins}
    ordered, visiting, visited = [], set(), set()
    def visit(plugin_id):
        if plugin_id in visited:
            return
        if plugin_id in visiting:
            raise ValueError('Cyclic bundled plugin dependency: ' + plugin_id)
        visiting.add(plugin_id)
        plugin = by_id[plugin_id]
        for dep_id in plugin.get('dependencies', {}):
            if dep_id in by_id:
                visit(dep_id)
        visiting.remove(plugin_id)
        visited.add(plugin_id)
        ordered.append(plugin)
    for plugin_id in by_id:
        visit(plugin_id)
    return ordered

def get(url, api=False):
    headers = {'User-Agent': 'revenge-next-personal-updater'}
    if api:
        headers['Accept'] = 'application/vnd.github+json'
        token = os.environ.get('GH_TOKEN')
        if token:
            headers['Authorization'] = f'Bearer {token}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return r.read()

def main():
    artifacts = json.loads(get(f'https://api.github.com/repos/{UPSTREAM}/actions/artifacts?per_page=100', True))['artifacts']
    artifact = next(a for a in artifacts if a['name'] == 'revenge-bundle' and not a['expired'] and a['workflow_run']['head_branch'] == 'main' and a['workflow_run']['head_repository_id'] == 952540647)
    sha = artifact['workflow_run']['head_sha']
    status_path = Path('build-info.json')
    previous = json.loads(status_path.read_text()) if status_path.exists() else {}
    if previous.get('artifact_id') == artifact['id'] and previous.get('generator_version') == GENERATOR_VERSION:
        print('Already current')
        return
    archive = get(f'https://nightly.link/{UPSTREAM}/actions/artifacts/{artifact["id"]}.zip')
    digest = 'sha256:' + hashlib.sha256(archive).hexdigest()
    if digest != artifact['digest']:
        raise RuntimeError('Official artifact SHA-256 mismatch')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        bundle = z.read('revenge.bundle')
    if len(bundle) < 100000 or bundle[:8] != bytes.fromhex('c61fbc03c103191f'):
        raise RuntimeError('Expected Hermes production bytecode')
    source = get(f'https://codeload.github.com/{UPSTREAM}/zip/{sha}')
    with zipfile.ZipFile(io.BytesIO(source)) as z:
        root = z.namelist()[0]
        version = json.loads(z.read(root + 'package.json'))['version']
        plugins = []
        for name in sorted(z.namelist()):
            relative = name.removeprefix(root)
            if not relative.startswith('src/plugins/') or not relative.endswith('/manifest.json') or relative.count('/') != 4:
                continue
            m = json.loads(z.read(name))
            if m.get('build', {}).get('devOnly'):
                continue
            p = {'id': m['id']}
            for key in ('essential', 'dependencies'):
                if m.get(key):
                    p[key] = m[key]
            if m.get('enabledByDefault') is True:
                p['enabledByDefault'] = True
            default_source = m.get('defaultSource')
            if default_source:
                for key in ('name', 'description', 'author', 'contributors', 'icon', 'version'):
                    if key in m:
                        p[key] = m[key]
                p['defaultSource'] = {'repo': REPOSITORY} if default_source is True else default_source
            plugins.append(p)
        if not any(p['id'] == 'revenge.settings.plugins' for p in plugins):
            raise RuntimeError('Missing plugin manager manifest')
        license_text = z.read(root + 'LICENSE')
    # All downloads are validated before replacing published files.
    Path('revenge.bundle').write_bytes(bundle)
    Path('manifest.json').write_text(json.dumps({'format': 1, 'version': version, 'plugins': order_plugins(plugins)}, separators=(',', ':')), encoding='utf-8')
    Path('source.zip').write_bytes(source)
    Path('LICENSE.upstream').write_bytes(license_text)
    status_path.write_text(json.dumps({'generator_version': GENERATOR_VERSION, 'upstream': UPSTREAM, 'commit': sha, 'artifact_id': artifact['id'], 'artifact_sha256': digest, 'bundle_sha256': hashlib.sha256(bundle).hexdigest(), 'created_at': artifact['created_at']}, indent=2) + '\n', encoding='utf-8')
    print('Mirrored official build', sha)

if __name__ == '__main__':
    main()

