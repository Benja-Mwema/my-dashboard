from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, subprocess, time

ROOT = Path(__file__).resolve().parent
MODULE = ROOT.parent
APP = MODULE.parent
REPO = Path(r'D:\render_sites\my-dashboard')
TASK = 'AURUM Dashboard Refresh 15 Minutes'
EXPECTED = {
    'aurum-workspace-v2.js': 'fa3ce016c8cb4e824c1acff93543bfd83d4dfcecc3d7efb3ec22a36487c31ea0',
    'aurum-charts-v3.js': '0a47d0a79d4cd299fb0773e4eb427f581cb1235bfc33065b42b6648c6fe0018b',
    'aurum-views.js': '765a082fc792ee1e3bb8ce401ac57a9d27bff239b02039cc95e4691d1512a148',
    'usdjpy.html': 'c8378903a40871eddf226c45b6a52e63f53f205b0e86a1e9dcb683367dfb5d47',
    'usdjpy.js': '1727cd5f2d82036f0b83c6908dc2fe16af8e4e36169cf71d183067953f8a670c',
    'usdjpy.css': '199df92fac76004bb25fed9dede2ec2abadaac8403f8b5649edab12764b336f5',
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def digest(b):
    return hashlib.sha256(b).hexdigest()

def run(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    if p.returncode:
        raise RuntimeError(str(args[:3]) + ': ' + p.stderr[-2000:] + p.stdout[-1000:])
    return p.stdout.strip()

def ps(command):
    return run(['powershell.exe', '-NoProfile', '-Command', command])

def git(*args):
    return run(['git', '-C', str(REPO), *args])

def main():
    checks = json.loads((ROOT / 'ui_acceptance.json').read_text())
    assert len(checks) == 16 and all(not c['errors'] for c in checks)
    assert all(c['indicator_parity'] and c['snapshot_unchanged'] and c['frozen_replay'] == 55 for c in checks[:2])
    manifest = MODULE / 'freeze_manifest.json'
    assert sha(manifest) == 'b3e7bb3d9101e676f1c67e3802cbd66d0f4357d5cc01c8bfe4462543ba3c6ead'
    frozen = {MODULE / n: h for n, h in json.loads(manifest.read_text())['files'].items()}
    frozen[manifest] = sha(manifest)
    for p, h in frozen.items():
        assert sha(p) == h, 'Frozen file mismatch: ' + p.name
    backup = ROOT / ('backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir()
    modified = {}
    committed = False
    enabled = None
    try:
        enabled = ps("(Get-ScheduledTask -TaskName '" + TASK + "').Settings.Enabled").lower() == 'true'
        if enabled:
            ps("Disable-ScheduledTask -TaskName '" + TASK + "' | Out-Null")
        for attempt in range(90):
            running = ps("$s=New-Object -ComObject Schedule.Service; $s.Connect(); @($s.GetRunningTasks(0) | Where-Object {$_.Name -eq '" + TASK + "'}).Count")
            if running == '0':
                break
            if attempt % 3 == 0:
                print('Waiting for current refresh cycle to complete safely', flush=True)
            time.sleep(10)
        else:
            raise RuntimeError('Refresh still active; presentation files left unchanged')
        assert not (APP / 'publish_transaction.json').exists(), 'Publication transaction active'
        assert not git('status', '--porcelain'), 'Unrelated repository changes present'
        assert git('branch', '--show-current') == 'main'
        git('fetch', 'origin', 'main')
        git('merge', '--ff-only', 'origin/main')
        previous = git('rev-parse', 'HEAD')
        for name, expected in EXPECTED.items():
            assert sha(REPO / name) == expected, 'Concurrent presentation change: ' + name
        preserved = {p: sha(p) for p in REPO.iterdir() if p.is_file() and (p.suffix == '.json' or p.name.endswith('-rules.md'))}
        preserved.update(frozen)
        for name in ['config.json', 'latest_native.json']:
            p = MODULE / name
            if p.exists():
                preserved[p] = sha(p)
        targets = {REPO / name: (ROOT / 'site' / name).read_bytes() for name in EXPECTED}
        # Read staged USDJPY HTML from targets so cache updates never restore the old page.
        for p in REPO.glob('*.html'):
            source = targets.get(p, p.read_bytes()).decode('utf-8')
            changed = source
            for script in ['aurum-workspace-v2.js', 'aurum-charts-v3.js', 'aurum-views.js']:
                changed = re.sub(r'(src="' + re.escape(script) + r')(?:\?[^" ]*)?(\")', r'\1?v=usdjpy-harmonized-20261118\2', changed)
            if changed != source or p in targets:
                targets[p] = changed.encode('utf-8')
        for name in ['usdjpy.html', 'usdjpy.js', 'usdjpy.css']:
            targets[MODULE / 'site' / name] = targets[REPO / name]
            targets[REPO / 'runtime/usdjpy/site' / name] = targets[REPO / name]
        for name in ['deploy_ui.py', 'test_ui.py', 'ui_acceptance.json', 'README.md']:
            targets[REPO / 'runtime/usdjpy/harmonize_20261118' / name] = (ROOT / name).read_bytes()
        for i, (p, content) in enumerate(targets.items()):
            old = p.read_bytes() if p.exists() else None
            saved = backup / str(i)
            if old is not None:
                saved.write_bytes(old)
            modified[str(p)] = {'backup': str(saved) if old is not None else None, 'old': digest(old) if old is not None else None, 'new': digest(content)}
        (backup / 'manifest.json').write_text(json.dumps({'previous_commit': previous, 'files': modified, 'preserved': {str(p): h for p, h in preserved.items()}}, indent=2))
        for p, content in targets.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(p.suffix + '.harmonize-tmp')
            tmp.write_bytes(content)
            try:
                tmp.replace(p)
            except PermissionError:
                assert p.is_file() and sha(p) == modified[str(p)]['old']
                p.write_bytes(content)
                tmp.unlink()
            assert sha(p) == digest(content)
        assert all(sha(p) == h for p, h in preserved.items()), 'Data, rules or formula changed'
        paths = [p.relative_to(REPO).as_posix() for p in targets if p.is_relative_to(REPO)]
        git('-c', 'core.autocrlf=false', 'add', '--', *paths)
        git('-c', 'core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol', 'diff', '--cached', '--check')
        git('commit', '-m', 'Harmonize USDJPY with shared AURUM chart and workspace')
        committed = True
        commit = git('rev-parse', 'HEAD')
        git('push', 'origin', 'main')
        assert git('ls-remote', 'origin', 'refs/heads/main').split()[0] == commit
        assert not git('status', '--porcelain')
        receipt = {'status': 'PUSHED', 'at_utc': datetime.now(timezone.utc).isoformat(), 'commit': commit, 'previous_commit': previous,
                   'url': 'https://my-dashboard-olo8.onrender.com/usdjpy.html', 'frozen_formula_unchanged': True,
                   'preserved_files': len(preserved), 'preview_checks': len(checks), 'scheduler_original_enabled': enabled,
                   'public_files': {p.name: sha(p) for p in targets if p.parent == REPO}}
        (ROOT / 'deployment_receipt.json').write_text(json.dumps(receipt, indent=2))
        print(json.dumps(receipt), flush=True)
    except Exception:
        if not committed:
            paths = [Path(p).relative_to(REPO).as_posix() for p in modified if Path(p).is_relative_to(REPO)]
            staged = [n for n in git('diff', '--cached', '--name-only').splitlines() if n in paths]
            if staged:
                git('restore', '--staged', '--', *staged)
            for name, spec in modified.items():
                p = Path(name)
                if p.exists() and sha(p) == spec['new']:
                    if spec['backup']:
                        shutil.copyfile(spec['backup'], p)
                    else:
                        p.unlink()
        raise
    finally:
        if enabled:
            ps("Enable-ScheduledTask -TaskName '" + TASK + "' | Out-Null")
            assert ps("(Get-ScheduledTask -TaskName '" + TASK + "').Settings.Enabled").lower() == 'true'
            print('Dashboard refresh scheduler enabled', flush=True)

if __name__ == '__main__':
    main()
