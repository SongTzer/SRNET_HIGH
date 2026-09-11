"""策略回測 CLI。

    python -m finlab_lab.cli list
    python -m finlab_lab.cli run momentum --start 2013-04-01
    python -m finlab_lab.cli run breakout --start 2013-04-01 --end 2026-08-31
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from finlab_lab.session import ensure_login, loader

REPORT_DIR = Path("reports")


def cmd_list(_: argparse.Namespace) -> int:
    from strategies import REGISTRY

    width = max(len(name) for name in REGISTRY)
    for name, strategy in sorted(REGISTRY.items()):
        print(f"{name:<{width}}  {strategy.description}")
    return 0


def _save_html(report: Any, path: Path) -> bool:
    """把互動式報表存成 HTML。

    ``Report.to_html`` 來自編譯模組，不同版本的呼叫方式可能是回傳字串或直接
    寫檔，兩種都試一次，失敗就跳過（metrics JSON 仍然會留下）。
    """
    to_html = getattr(report, "to_html", None)
    if not callable(to_html):
        return False
    try:
        result = to_html()
        if isinstance(result, str):
            path.write_text(result, encoding="utf-8")
            return True
    except TypeError:
        pass
    try:
        to_html(str(path))
        return path.exists()
    except Exception as exc:  # noqa: BLE001 - 報表存檔失敗不該讓回測結果消失
        print(f"HTML 報表儲存失敗（已忽略）：{exc}", file=sys.stderr)
        return False


def cmd_run(args: argparse.Namespace) -> int:
    ensure_login()

    from finlab.backtest import sim

    from strategies import REGISTRY

    strategy = REGISTRY.get(args.strategy)
    if strategy is None:
        print(f"找不到策略：{args.strategy}", file=sys.stderr)
        print(f"可用策略：{', '.join(sorted(REGISTRY))}", file=sys.stderr)
        return 1

    print(f"建立部位：{strategy.name} — {strategy.description}")
    position = strategy.build(loader())

    if args.start or args.end:
        position = position.loc[args.start or None : args.end or None]

    sim_kwargs = dict(strategy.sim_kwargs)
    if args.resample:
        sim_kwargs["resample"] = args.resample
    # 預設不上傳到 FinLab 雲端，要上傳請加 --upload。
    sim_kwargs["upload"] = args.upload

    print(f"回測中：{sim_kwargs}")
    report = sim(position, **sim_kwargs)

    metrics = report.get_metrics()
    print(json.dumps(metrics, ensure_ascii=False, indent=2, default=str))

    REPORT_DIR.mkdir(exist_ok=True)
    metrics_path = REPORT_DIR / f"{strategy.name}.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"指標已存檔：{metrics_path}")

    html_path = REPORT_DIR / f"{strategy.name}.html"
    if _save_html(report, html_path):
        print(f"報表已存檔：{html_path}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="finlab_lab", description="FinLab 台股策略回測")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="列出所有策略").set_defaults(func=cmd_list)

    run = sub.add_parser("run", help="回測單一策略")
    run.add_argument("strategy", help="策略名稱，用 list 查詢")
    run.add_argument("--start", default=None, help="回測起始日 YYYY-MM-DD")
    run.add_argument("--end", default=None, help="回測結束日 YYYY-MM-DD")
    run.add_argument("--resample", default=None, help="覆寫再平衡頻率，如 M / W / Q")
    run.add_argument(
        "--upload", action="store_true", help="把回測結果上傳到 FinLab 雲端（預設不上傳）"
    )
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
