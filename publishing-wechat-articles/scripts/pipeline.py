#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

from wechat_pipeline.config import load_repository_config
from wechat_pipeline.feishu import FeishuClient
from wechat_pipeline.models import Stage
from wechat_pipeline.orchestrator import Pipeline
from wechat_pipeline.oss import OssClient
from wechat_pipeline.preflight import run_preflight
from wechat_pipeline.publish import Publisher


SKILL_ROOT = Path(__file__).resolve().parents[1]


def _base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Self-contained WeChat article pipeline")
    parser.add_argument("--workspace", type=Path, help="override repository-local workspace directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="run read-only dependency and configuration checks")
    preflight.add_argument("--mode", choices=("collect-only", "prepare-only", "publish"), default="prepare-only")
    preflight.add_argument("--account", choices=("auto", "tech", "parenting"), default="auto")
    preflight.add_argument("--title", default="")
    preflight.add_argument("--tags", default="")
    preflight.add_argument("--author-voice", action="store_true", help="check optional author voice configuration")
    preflight.add_argument("--json", action="store_true", dest="as_json")

    plan = subparsers.add_parser("plan", help="create a durable local run")
    plan.add_argument("--title", required=True)
    plan.add_argument("--summary", default="")
    plan.add_argument("--tags", default="")
    plan.add_argument("--account", choices=("auto", "tech", "parenting"), default="auto")
    plan.add_argument("--mode", choices=("collect-only", "prepare-only", "publish"), default="prepare-only")
    plan.add_argument("--run-id")
    plan.add_argument("--author-voice", action="store_true", help="enable the optional evidence-backed author voice workflow")
    plan.add_argument("--json", action="store_true", dest="as_json")

    capture = subparsers.add_parser("capture", help="capture a public URL into a run")
    capture.add_argument("run_id")
    capture.add_argument("url")
    capture.add_argument("--json", action="store_true", dest="as_json")

    brief = subparsers.add_parser("brief", help="validate and attach an author brief to an enabled run")
    brief.add_argument("run_id")
    brief.add_argument("--input", type=Path, required=True)
    brief.add_argument("--json", action="store_true", dest="as_json")

    voice_review = subparsers.add_parser("voice-review", help="validate and attach an author voice review")
    voice_review.add_argument("run_id")
    voice_review.add_argument("--input", type=Path, required=True)
    voice_review.add_argument("--json", action="store_true", dest="as_json")

    research = subparsers.add_parser("research-check", help="validate a local reader-value and evidence dossier (no fact verification)")
    research.add_argument("--input", type=Path, required=True)
    research.add_argument("--json", action="store_true", dest="as_json")

    retitle = subparsers.add_parser("retitle", help="revise a run title before external publishing")
    retitle.add_argument("run_id")
    retitle.add_argument("--title", required=True)
    retitle.add_argument("--summary")
    retitle.add_argument("--json", action="store_true", dest="as_json")

    prepare = subparsers.add_parser("prepare", help="quality-check and render local article artifacts")
    prepare.add_argument("run_id")
    prepare.add_argument("--no-png", action="store_true", help="create cover HTML without Playwright PNG")
    prepare.add_argument("--json", action="store_true", dest="as_json")

    status = subparsers.add_parser("status", help="show persisted run state")
    status.add_argument("run_id")
    status.add_argument("--json", action="store_true", dest="as_json")

    publish = subparsers.add_parser("publish", help="perform authorized OSS and Feishu writes")
    publish.add_argument("run_id")
    publish.add_argument("--commit", action="store_true")
    publish.add_argument("--json", action="store_true", dest="as_json")

    reconcile = subparsers.add_parser("reconcile-empty-upload", help="verify all expected OSS objects are absent after a failed upload")
    reconcile.add_argument("run_id")
    reconcile.add_argument("--json", action="store_true", dest="as_json")

    reconcile_handoff = subparsers.add_parser("reconcile-handoff", help="search exact Feishu chat history before any handoff retry")
    reconcile_handoff.add_argument("run_id")
    reconcile_handoff.add_argument("--json", action="store_true", dest="as_json")

    confirm = subparsers.add_parser("confirm-downstream", help="record verified publishing-assistant draft receipt")
    confirm.add_argument("run_id")
    confirm.add_argument("--draft-id", required=True)
    confirm.add_argument("--assistant-message-id", required=True)
    confirm.add_argument("--json", action="store_true", dest="as_json")

    inspect_target = subparsers.add_parser("inspect-feishu-target", help="read-only Feishu credential and chat check")
    inspect_target.add_argument("--account", choices=("tech", "parenting"), required=True)
    inspect_target.add_argument("--json", action="store_true", dest="as_json")

    inspect_handoff = subparsers.add_parser("inspect-handoff", help="read-only search for an uncertain Feishu handoff")
    inspect_handoff.add_argument("run_id")
    inspect_handoff.add_argument("--json", action="store_true", dest="as_json")

    resume = subparsers.add_parser("resume", help="resume the next safe stage from a manifest")
    resume.add_argument("run_id")
    resume.add_argument("--commit", action="store_true")
    resume.add_argument("--no-png", action="store_true")
    resume.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _emit(payload: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key in ("run_id", "mode", "account", "state", "ready"):
        if key in payload:
            print(f"{key}={str(payload[key]).lower() if isinstance(payload[key], bool) else payload[key]}")
    if payload.get("failures"):
        print("failures=" + ", ".join(payload["failures"]))


def _manifest_payload(manifest) -> dict[str, object]:
    return manifest.to_dict()


def _publisher(config) -> Publisher:
    return Publisher(OssClient.from_repository_config(config), _feishu(config), prefix=config.oss.prefix)


def _feishu(config):
    if config.runtime.feishu_mode == "lark-cli":
        from wechat_pipeline.lark_cli import LarkCliFeishuClient
        return LarkCliFeishuClient(config)
    return FeishuClient(config)


def execute(args: argparse.Namespace) -> tuple[dict[str, object], int]:
    config = load_repository_config(SKILL_ROOT)
    pipeline = Pipeline(config, args.workspace)
    if args.command == "research-check":
        from wechat_pipeline.research import check_research
        report = check_research(json.loads(args.input.read_text(encoding="utf-8")))
        report["ready"] = report["passed"]
        report["failures"] = report["findings"]
        return report, 0 if report["passed"] else 1
    if args.command == "preflight":
        account = config.route_account(args.account, args.title, args.tags)
        report = run_preflight(config, args.mode, account, author_voice=args.author_voice)
        return report.to_dict(), 0 if report.ready else 1
    if args.command == "plan":
        manifest = pipeline.plan(
            args.title,
            args.summary,
            args.account,
            tags=args.tags,
            mode=args.mode,
            run_id=args.run_id,
            author_voice=args.author_voice,
        )
        return _manifest_payload(manifest), 0
    if args.command == "capture":
        return _manifest_payload(pipeline.capture(args.run_id, args.url)), 0
    if args.command == "brief":
        return _manifest_payload(pipeline.ingest_brief(args.run_id, args.input)), 0
    if args.command == "voice-review":
        return _manifest_payload(pipeline.ingest_voice_review(args.run_id, args.input)), 0
    if args.command == "retitle":
        return _manifest_payload(pipeline.retitle(args.run_id, args.title, args.summary)), 0
    if args.command == "prepare":
        return _manifest_payload(pipeline.prepare(args.run_id, render_png=not args.no_png)), 0
    if args.command == "status":
        return _manifest_payload(pipeline.status(args.run_id)), 0
    if args.command == "publish":
        if not args.commit:
            raise ValueError("--commit is required for external writes")
        path = pipeline._manifest_path(args.run_id)
        return _manifest_payload(_publisher(config).publish(path)), 0
    if args.command == "reconcile-empty-upload":
        return _manifest_payload(_publisher(config).reconcile_empty_upload(pipeline._manifest_path(args.run_id))), 0
    if args.command == "reconcile-handoff":
        return _manifest_payload(_publisher(config).reconcile_handoff(pipeline._manifest_path(args.run_id))), 0
    if args.command == "confirm-downstream":
        manifest = pipeline.status(args.run_id)
        client = _feishu(config)
        if not callable(getattr(client, "verify_draft_receipt", None)):
            raise ValueError("this Feishu mode cannot verify assistant draft receipts")
        receipt = client.verify_draft_receipt(manifest.account, args.assistant_message_id,
                                              manifest.external.get("message_id"), manifest.title, args.draft_id)
        confirmation = {"kind": "wechat-draft", "title": manifest.title,
                        "message_id": manifest.external.get("message_id"),
                        "confirmed_by": "publishing-assistant",
                        "evidence": f"Feishu assistant message {args.assistant_message_id}; {receipt['method']}",
                        "draft_id": args.draft_id}
        return _manifest_payload(_publisher(config).confirm_downstream(pipeline._manifest_path(args.run_id), confirmation)), 0
    if args.command == "inspect-feishu-target":
        return _feishu(config).inspect_target(args.account), 0
    if args.command == "inspect-handoff":
        manifest = pipeline.status(args.run_id)
        client = _feishu(config)
        expected = client.handoff_text(manifest.title, manifest.summary,
                                       manifest.external["cover_url"], manifest.external["html_url"])
        since_ms = int(datetime.fromisoformat(manifest.created_at).timestamp() * 1000)
        return client.inspect_handoff_history(manifest.account, expected, since_ms=since_ms), 0
    if args.command == "resume":
        manifest = pipeline.status(args.run_id)
        if manifest.state in {Stage.PLANNED, Stage.CAPTURED, Stage.WRITTEN, Stage.NEEDS_REVIEW}:
            return _manifest_payload(pipeline.prepare(args.run_id, render_png=not args.no_png)), 0
        if manifest.state in {Stage.RENDERED, Stage.UPLOADED, Stage.HANDED_OFF}:
            if manifest.authorization_mode != "publish" or not args.commit:
                raise ValueError("--commit is required to resume external writes")
            return _manifest_payload(_publisher(config).publish(pipeline._manifest_path(args.run_id))), 0
        return _manifest_payload(manifest), 0
    raise ValueError(f"unsupported command: {args.command}")


def _redact(message: str) -> str:
    try:
        runtime = load_repository_config(SKILL_ROOT).runtime
        secrets = (
            runtime.oss_access_key_id,
            runtime.oss_access_key_secret,
            runtime.tech_app_secret,
            runtime.parenting_app_secret,
        )
        for secret in secrets:
            if secret:
                message = message.replace(secret, "[REDACTED]")
    except Exception:
        pass
    return message


def main(argv: list[str] | None = None) -> int:
    parser = _base_parser()
    args = parser.parse_args(argv)
    try:
        payload, exit_code = execute(args)
        _emit(payload, getattr(args, "as_json", False))
        return exit_code
    except Exception as exc:
        message = _redact(str(exc))
        if getattr(args, "as_json", False):
            print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"error: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
