#!/usr/bin/env python3
"""Rebuild the source ZIP from an explicit allowlist; no dependencies."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent
files = [root / name for name in ('README.md', 'AUDIT.md', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md') if (root / name).is_file()]
for directory in ('.claude-plugin', 'agents', 'skills', 'scripts'):
    files.extend(p for p in (root / directory).rglob('*')
                 if p.is_file() and not p.is_symlink() and p.suffix in {'.md', '.py', '.json'}
                 and '__pycache__' not in p.parts)
evals = root / 'evals'
if evals.is_dir():  # cases, graders and scaffolds; never results/ (run output) or mocks recordings
    files.extend(p for p in evals.rglob('*') if p.is_file() and not p.is_symlink()
                 and p.suffix in {'.md', '.yaml', '.sh', '.json'} and 'results' not in p.parts)
for name in ('.github/workflows/validate.yml', '.gitignore'):
    if (root / name).is_file(): files.append(root / name)
assets = root / 'skills/tui-design/assets'
files.extend(p for p in assets.rglob('*') if p.is_file() and not p.is_symlink()
             and p.suffix in {'.png', '.txt', '.ansi'})
if (root / 'LICENSE').is_file(): files.append(root / 'LICENSE')
output = root / 'termcraft-plugin.zip'
temporary = output.with_suffix('.zip.tmp')
try:
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.external_attr = (0o100755 if path.suffix == '.sh' else 0o100644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {p.relative_to(root).as_posix() for p in files}
        for path in files: assert archive.read(path.relative_to(root).as_posix()) == path.read_bytes()
    temporary.replace(output)
finally:
    temporary.unlink(missing_ok=True)
print(f'{output}: {len(files)} files; contents verified against source')
