# NAMED LOCAL EXCEPTION SOLVER-IMAGE: upstream supplies no solver Dockerfile.
# Official Python image, registry-verified Linux arm64/v8 child manifest.
FROM python:3.12-slim@sha256:b224e2fe306f9d303251ada22961635e5b52a69c0414a0050611be31c59f5f5b

# Official Codex 0.166.0 standalone arm64 binary and matching bundled sandbox.
# SHA-256 values are the release API's asset.digest, not locally chosen values.
RUN python3 - <<'PY'
import hashlib, io, pathlib, tarfile, urllib.request
release = 'https://github.com/openai/codex/releases/download/rust-v0.166.0/'
assets = (
    ('codex-aarch64-unknown-linux-musl.tar.gz',
     '94eb707605ec2646b2e05b7edf7c4e7b3ccf02b16237c34ae9beb8cfb7f810a9',
     '/usr/local/bin/codex'),
    ('bwrap-aarch64-unknown-linux-musl.tar.gz',
     'b59c26ee2cc939a1f3df81b639fcc4fb965609bdc704ca85777c168c12cfeb26',
     '/usr/local/bin/codex-resources/bwrap'),
    # Code-mode host, required by 0.166.0 code mode (Feature::CodeModeHost, Stable, default on).
    ('codex-code-mode-host-aarch64-unknown-linux-musl.tar.gz',
     'ac98d1f878e353a16cba711fd47bfef2f6c814109bdd819ee2b6b6d6a19701e7',
     '/usr/local/bin/codex-code-mode-host'),
)
for name, expected, destination in assets:
    payload = urllib.request.urlopen(release + name).read()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise SystemExit('STOP: release asset hash mismatch: ' + name)
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        files = [member for member in archive.getmembers() if member.isfile()]
        if len(files) != 1:
            raise SystemExit('STOP: unexpected standalone archive layout: ' + name)
        target = pathlib.Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.extractfile(files[0]).read())
        target.chmod(0o755)
PY

WORKDIR /work
