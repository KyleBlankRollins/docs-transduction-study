import csv
import json
import shutil
import subprocess

import pytest

from docs_transduction_study import coding_ai, instrument_authoring, lint_probes
from docs_transduction_study import study_pipeline as pipeline

MDX = {
    "explicit": "---\ntitle: T\n---\nIntro text for the page.\n\n:::tip\nYou can customize the settings to your needs.\n:::\n\n"
    + "Filler sentence number one. " * 70
    + "\n\nSave the settings file after editing it.\n",
    "implicit": "---\ntitle: T\n---\nIntro text for the page.\n\nAs a helpful tip, You can customize the settings to your needs.\n\n"
    + "Filler sentence number one. " * 70
    + "\n\nSave the settings file after editing it.\n",
}
HTML = {
    "explicit": '<aside class="starlight-aside"><p class="starlight-aside__title">Tip</p><p>You can customize the settings to your needs.</p></aside>',
    "implicit": "<p>As a helpful tip, You can customize the settings to your needs.</p>",
}


@pytest.fixture(autouse=True)
def no_real_builds(monkeypatch):
    """Tests must never materialise the real corpus or start a real build."""

    def forbidden(*_args, **_kwargs):
        raise AssertionError("real builder or snapshotter invoked under test")

    monkeypatch.setattr(pipeline, "_default_builder", forbidden)
    monkeypatch.setattr(pipeline, "_default_snapshotter", forbidden)


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    for arm, text in MDX.items():
        (root / "corpus" / arm / "guides").mkdir(parents=True)
        (root / "corpus" / arm / "guides" / "page.mdx").write_text(text)
    write_csv(
        root / "corpus" / "specimens.csv",
        ["specimen_id", "source_path"],
        [{"specimen_id": "S01", "source_path": "guides/page.mdx"}],
    )
    hosts = {
        "explicit": ":::tip\nYou can customize the settings to your needs.",
        "implicit": "As a helpful tip, You can customize the settings to your needs.",
    }
    write_csv(
        root / "instruments" / "instances.csv",
        instrument_authoring.INSTANCE_FIELDS,
        [
            {
                "instance_id": "S01-R3-001",
                "specimen_id": "S01",
                "relation_type": "R3",
                "anchor_explicit": "customize the settings to your needs",
                "anchor_implicit": "customize the settings to your needs",
                "host_passage_explicit": hosts["explicit"],
                "host_passage_implicit": hosts["implicit"],
                "demark_rule": "D3",
                "notes": "",
            },
            {
                "instance_id": "S01-R3-002",
                "specimen_id": "S01",
                "relation_type": "R3",
                "anchor_explicit": "x",
                "anchor_implicit": "x",
                "host_passage_explicit": "",
                "host_passage_implicit": "",
                "demark_rule": "D3",
                "notes": "excluded",
            },
        ],
    )
    write_csv(
        root / "instruments" / "probes.csv",
        lint_probes.PROBES_HEADERS,
        [
            {
                "probe_id": "P-S01-R3-001",
                "instance_id": "S01-R3-001",
                "question": "How is adjusting the configuration presented?",
                "correct_answer": "As optional",
                "foil_1": "As mandatory",
                "foil_2": "",
                "version_change": "false",
                "superseded_answer": "",
                "superseded_source": "",
            }
        ],
    )
    write_csv(
        root / "instruments" / "gate_exclusions.csv",
        lint_probes.EXCLUSIONS_HEADERS,
        [
            {
                "instance_id": "S01-R3-002",
                "reason": "invalid",
                "failed_arm": "both",
                "date": "2026-09-23",
            }
        ],
    )
    (root / "coding").mkdir()
    (root / "coding" / "seed").write_text("ab" * 32 + "\n")
    return root


def fake_builder(nondeterministic=False, drop_page=False):
    calls = []

    def build(arm, workdir):
        calls.append(arm)
        dist = workdir / "dist"
        page = dist / "en" / "guides" / "page" / "index.html"
        page.parent.mkdir(parents=True)
        body = (
            HTML[arm]
            + "<p>"
            + "Filler sentence number one. " * 70
            + "</p><p>Save the settings file after editing it.</p>"
        )
        if nondeterministic and calls.count("explicit") == 2:
            body += "<p>changed</p>"
        page.write_text(
            f'<html><body><div class="sl-markdown-content"><p>Intro text for the page.</p>{body}</div></body></html>'
        )
        (dist / "_astro").mkdir()
        (dist / "_astro" / "style.css").write_text("body{}")
        if not (drop_page and arm == "implicit"):
            other = dist / "en" / "other" / "index.html"
            other.parent.mkdir(parents=True)
            other.write_text(
                '<html><body><div class="sl-markdown-content">Other</div></body></html>'
            )
        return dist

    return build


def fake_snapshotter(site, route, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "snapshot-1.txt").write_text(
        "- paragraph: You can customize the settings to your needs."
    )
    return {"stable": True}


def unlocked(_repo):
    raise pipeline.PipelineError(
        "L2 is not recorded in DESIGN.md; study generation is forbidden"
    )


def locked(_repo):
    return {"commit": "f" * 40, "date": "2026-10-01"}


@pytest.fixture
def passphrase(tmp_path):
    path = tmp_path / "outside" / "pass"
    path.parent.mkdir()
    path.write_text("correct horse battery staple")
    return path


def run(repo, out, passphrase, **kwargs):
    options = {
        "builder": fake_builder(),
        "snapshotter": fake_snapshotter,
        "lock_verifier": locked,
        "mdx_checker": lambda _repo: [],
    }
    options.update(kwargs)
    return pipeline.run_study(out, passphrase_file=passphrase, repo=repo, **options)


def test_generation_refuses_without_l2(repo, tmp_path, passphrase):
    with pytest.raises(pipeline.PipelineError, match="forbidden"):
        run(repo, tmp_path / "out", passphrase, lock_verifier=unlocked)
    assert not (tmp_path / "out").exists()


def test_end_to_end_eight_assignments_with_sealed_keys(repo, tmp_path, passphrase):
    out = tmp_path / "out"
    manifest = run(repo, out, passphrase)
    assert (
        manifest["a1"]["pages"] == 2
        and (out / "a1" / "explicit" / "_astro" / "style.css").exists()
    )
    packets = [
        json.loads(line)
        for line in (out / "assignments" / "packets.jsonl").read_text().splitlines()
    ]
    assert len(packets) == 8 and manifest["assignments"]["per_stage"] == dict.fromkeys(
        pipeline.STAGES, 2
    )
    assert all(
        "correct_id" not in packet and "S01-R3-001" not in json.dumps(packet)
        for packet in packets
    )
    assert not list((out / "private").glob("*.jsonl"))
    keys = [
        json.loads(line)
        for line in pipeline.unseal(
            out / "private" / "keys.jsonl.enc", passphrase
        ).splitlines()
    ]
    by_id = {packet["opaque_id"]: packet for packet in packets}
    resolved = json.loads((out / "anchor-assignments.json").read_text())[0]
    for key in keys:
        artifact = by_id[key["opaque_id"]]["artifact"]
        if key["stage"] == "A4":
            chunk = (out / resolved[key["arm"]]["chunk_path"]).read_text()
            assert artifact == chunk and len(chunk) <= pipeline.CHUNK_SIZE
        if key["stage"] == "A1":
            assert artifact.startswith("<html>")
    assert (
        "explicit" in resolved["explicit"]["chunk_path"]
        and "implicit" in resolved["implicit"]["chunk_path"]
    )
    repeats = (out / "assignments" / "repeat_packets.jsonl").read_text().splitlines()
    assert len(repeats) == 2  # ceil(0.2 * 8)
    plan = pipeline.assignment_plan(pipeline.load_instrument(repo))
    assert [p["opaque_id"] for p in packets] == [
        plan["opaque"][i] for i in plan["order"]
    ]
    assert plan["repeat_sample"] == coding_ai.repeat_sample(
        [p["opaque_id"] for p in packets], "ab" * 32
    )


@pytest.mark.parametrize(
    ("builder", "message"),
    [
        (fake_builder(nondeterministic=True), "nondeterminism"),
        (fake_builder(drop_page=True), "different page sets"),
    ],
)
def test_build_checks_fail_closed(repo, tmp_path, passphrase, builder, message):
    with pytest.raises(pipeline.PipelineError, match=message):
        run(repo, tmp_path / "out", passphrase, builder=builder)
    assert not (tmp_path / "out" / "assignments").exists()


def test_unresolvable_anchor_stops_before_packaging(repo, tmp_path, passphrase):
    def hidden_builder(arm, workdir):
        dist = fake_builder()(arm, workdir)
        page = dist / "en" / "guides" / "page" / "index.html"
        page.write_text(
            page.read_text().replace("customize the settings", "adjust the options")
        )
        return dist

    with pytest.raises(pipeline.PipelineError, match="amendment"):
        run(repo, tmp_path / "out", passphrase, builder=hidden_builder)
    assert not (tmp_path / "out" / "assignments").exists()


def test_keys_require_passphrase_outside_repository(repo, tmp_path):
    inside = repo / "pass"
    inside.write_text("secret")
    with pytest.raises(pipeline.PipelineError, match="outside the repository"):
        run(repo, tmp_path / "out", inside)


def test_unstable_snapshot_stops(repo, tmp_path, passphrase):
    def unstable(site, route, out):
        fake_snapshotter(site, route, out)
        return {"stable": False}

    with pytest.raises(pipeline.PipelineError, match="A2"):
        run(repo, tmp_path / "out", passphrase, snapshotter=unstable)


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_verify_lock_checks_real_commit_and_contents(repo):
    for name in pipeline.FROZEN_CODE:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("# frozen\n")
    (repo / "pipeline" / "demark").mkdir(parents=True)
    (repo / "pipeline" / "demark" / "templates.json").write_text("{}")
    (repo / "DESIGN.md").write_text(
        '---\ninstrument_locked: ""\ninstrument_lock_commit: ""\n---\n'
    )
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    git(repo, "init", "-q")
    git(
        repo,
        *ident,
        "add",
        "-A",
        "--",
        ".",
        ":!coding/seed",
        ":!instruments/probes.csv",
    )
    git(repo, *ident, "commit", "-q", "-m", "readiness")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    git(repo, *ident, "add", "coding/seed", "instruments/probes.csv")
    git(repo, *ident, "commit", "-q", "-m", "L2")
    with pytest.raises(pipeline.PipelineError, match="not recorded"):
        pipeline.verify_lock(repo)
    (repo / "DESIGN.md").write_text(
        f'---\ninstrument_locked: "2026-10-01"\ninstrument_lock_commit: "{base}"\n---\n'
    )
    with pytest.raises(
        pipeline.PipelineError, match="lacks lock-set files|only lock-set files"
    ):
        pipeline.verify_lock(repo)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    (repo / "DESIGN.md").write_text(
        f'---\ninstrument_locked: "2026-10-01"\ninstrument_lock_commit: "{sha}"\n---\n'
    )
    assert pipeline.verify_lock(repo)["commit"] == sha
    (repo / "instruments" / "probes.csv").write_text("changed\n")
    with pytest.raises(pipeline.PipelineError, match="differs"):
        pipeline.verify_lock(repo)

    def head():
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def design(amendments):
        (repo / "DESIGN.md").write_text(
            f'---\ninstrument_locked: "2026-10-01"\ninstrument_lock_commit: "{sha}"\n'
            f'instrument_amendment_commits: "{amendments}"\n---\n'
        )

    git(repo, *ident, "commit", "-q", "-am", "undocumented change")
    design(head())
    with pytest.raises(pipeline.PipelineError, match="AMENDMENTS.md"):
        pipeline.verify_lock(repo)
    (repo / "AMENDMENTS.md").write_text("A5\n")
    (repo / "instruments" / "probes.csv").write_text("amended\n")
    git(repo, *ident, "add", "AMENDMENTS.md", "instruments/probes.csv")
    git(repo, *ident, "commit", "-q", "-m", "A5")
    amendment = head()
    design("")
    with pytest.raises(pipeline.PipelineError, match="differs"):
        pipeline.verify_lock(repo)
    design(amendment)
    assert pipeline.verify_lock(repo)["reference"] == amendment
    (repo / "corpus" / "explicit" / "guides" / "page.mdx").write_text("edited")
    with pytest.raises(pipeline.PipelineError, match="Uncommitted"):
        pipeline.verify_lock(repo)
    (repo / "DESIGN.md").write_text(
        '---\ninstrument_locked: "2026-10-01"\ninstrument_lock_commit: "deadbeef"\n---\n'
    )
    with pytest.raises(pipeline.PipelineError, match="does not exist"):
        pipeline.verify_lock(repo)


def test_tilde_passphrase_paths_are_expanded(repo, tmp_path, passphrase, monkeypatch):
    monkeypatch.setenv("HOME", str(passphrase.parent.parent))
    tilde = pipeline.Path("~") / passphrase.parent.name / passphrase.name
    assert run(repo, tmp_path / "out", tilde)["assignments"]["first_pass"] == 8
    with pytest.raises(pipeline.PipelineError, match="missing or empty"):
        run(repo, tmp_path / "out2", pipeline.Path("~") / "absent")


def test_mdx_parse_failure_stops_before_any_build(repo, tmp_path, passphrase):
    with pytest.raises(pipeline.PipelineError, match="do not parse as MDX"):
        run(
            repo,
            tmp_path / "out",
            passphrase,
            mdx_checker=lambda _repo: ["page.mdx: bad"],
        )
    assert not (tmp_path / "out").exists()


def test_resume_repackages_archive_without_building(
    repo, tmp_path, passphrase, monkeypatch
):
    out = tmp_path / "out"
    run(repo, out, passphrase)
    generated = json.loads((out / "study-manifest.json").read_text())
    shutil.rmtree(out / "assignments")
    shutil.rmtree(out / "private")
    options = {"lock_verifier": locked, "mdx_checker": lambda _repo: []}
    resumed = pipeline.resume_study(
        out, passphrase_file=passphrase, repo=repo, **options
    )
    assert resumed["resumed_from_archive"] and resumed["generation_manifest_verified"]
    assert (
        resumed["assignments"]["packets_sha256"]
        == generated["assignments"]["packets_sha256"]
    )
    with pytest.raises(pipeline.PipelineError, match="already packaged"):
        pipeline.resume_study(out, passphrase_file=passphrase, repo=repo, **options)
    shutil.rmtree(out / "assignments")
    shutil.rmtree(out / "private")
    chunk = next((out / "a4").rglob("chunk-0000.txt"))
    chunk.write_text("tampered")
    with pytest.raises(pipeline.PipelineError, match="does not match its index"):
        pipeline.resume_study(out, passphrase_file=passphrase, repo=repo, **options)
