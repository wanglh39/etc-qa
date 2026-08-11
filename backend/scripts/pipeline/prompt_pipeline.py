import os

os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'test')
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import argparse
import json
from datetime import datetime

from prompt.version_manager import get_version_manager
from scripts.eval.eval_prompt_diff import format_diff, format_report, load_golden, run_evaluation
from utils.logger import get_logger

logger = get_logger("scripts.pipeline.prompt_pipeline")


def cmd_publish(args):
    vm = get_version_manager()
    template_text = args.template_text
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            template_text = f.read()

    result = vm.publish(args.key, template_text, args.description)
    print(f"发布成功: {args.key} v{result['version']}")
    return result


def cmd_rollback(args):
    vm = get_version_manager()
    result = vm.rollback(args.key, args.version)
    if "error" in result:
        print(f"回滚失败: {result['error']}")
        return result
    print(f"回滚成功: {args.key} v{result['version']}")
    return result


def cmd_eval(args):
    golden = load_golden(args.golden)
    pipelines = args.pipeline
    results = run_evaluation(golden, pipelines)
    report = format_report(results, label=f"[{args.label}]" if args.label else "")
    print(report)

    out_dir = args.output or os.path.join(os.path.dirname(__file__), "..", "..", "output")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    label_suffix = f"_{args.label}" if args.label else ""

    report_path = os.path.join(out_dir, f"prompt_eval{label_suffix}_{ts}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    results_path = os.path.join(out_dir, f"prompt_eval{label_suffix}_{ts}.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n报告: {report_path}")
    print(f"数据: {results_path}")
    return results


def cmd_diff(args):
    if not args.before or not args.after:
        print("需要指定 --before 和 --after 两个评估结果JSON文件")
        return

    with open(args.before, encoding="utf-8") as f:
        before = json.load(f)
    with open(args.after, encoding="utf-8") as f:
        after = json.load(f)

    diff_report = format_diff(before, after)
    print(diff_report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(diff_report)
        print(f"\nDIFF报告已保存: {args.output}")


def cmd_iterate(args):
    print(f"{'='*60}")
    print("提示词迭代流水线")
    print(f"{'='*60}")

    vm = get_version_manager()

    if not args.key:
        print("错误: 需要指定 --key 提示词key")
        return

    current = vm.get_version(args.key)
    if current:
        print(f"当前版本: {args.key} v{current['version']}")
    else:
        print(f"当前无活跃版本: {args.key}")

    print("\n--- 步骤1: 评估当前版本（基线）---")
    golden = load_golden(args.golden)
    before_results = run_evaluation(golden, args.pipeline)
    before_report = format_report(before_results, label="[基线]")
    print(before_report)

    template_text = args.template_text
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            template_text = f.read()
    if not template_text:
        print("\n错误: 需要通过 --template-text 或 --file 提供新提示词")
        return

    print("\n--- 步骤2: 发布新版本 ---")
    publish_result = vm.publish(args.key, template_text, args.description or "")
    new_version = publish_result["version"]
    print(f"发布成功: {args.key} v{new_version}")

    print("\n--- 步骤3: 评估新版本 ---")
    after_results = run_evaluation(golden, args.pipeline)
    after_report = format_report(after_results, label=f"[v{new_version}]")
    print(after_report)

    print("\n--- 步骤4: DIFF对比 ---")
    diff_report = format_diff(before_results, after_results)
    print(diff_report)

    before_rate = before_results["passed"] / before_results["total"] * 100 if before_results["total"] > 0 else 0
    after_rate = after_results["passed"] / after_results["total"] * 100 if after_results["total"] > 0 else 0
    delta = after_rate - before_rate

    out_dir = args.output or os.path.join(os.path.dirname(__file__), "..", "..", "output")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    diff_path = os.path.join(out_dir, f"prompt_diff_{args.key}_v{new_version}_{ts}.txt")
    with open(diff_path, "w", encoding="utf-8") as f:
        f.write(diff_report)
    print(f"\nDIFF报告: {diff_path}")

    if delta < -5:
        print(f"\n⚠️  通过率下降 {abs(delta):.1f}%，建议回滚！")
        print(f"  回滚命令: python scripts/pipeline/prompt_pipeline.py rollback --key {args.key}")
    elif delta < 0:
        print(f"\n⚠️  通过率轻微下降 {abs(delta):.1f}%，请人工审核")
    else:
        print(f"\n✅ 通过率提升 {delta:.1f}%，新版本已上线")

    return {"delta": delta, "before": before_results, "after": after_results}


def cmd_shadow_start(args):
    vm = get_version_manager()
    result = vm.start_shadow(args.key, args.version)
    if "error" in result:
        print(f"启动失败: {result['error']}")
        return
    print(f"影子测试已启动: {args.key} v{args.version}")
    print("PromptEngine将在每次render时同时渲染影子版本并记录差异")


def cmd_shadow_stop(args):
    vm = get_version_manager()
    result = vm.stop_shadow(args.key, args.version)
    print(f"影子测试已停止: {args.key} v{args.version}")


def cmd_shadow_stats(args):
    from prompt.shadow_recorder import get_shadow_records, get_shadow_stats
    stats = get_shadow_stats()
    print("影子测试统计:")
    print(f"  总请求数: {stats['total']}")
    print(f"  差异数: {stats['diff_count']}")
    print(f"  差异率: {stats['diff_rate']*100:.1f}%")
    for key, ks in stats["by_key"].items():
        rate = ks["diff"] / ks["total"] * 100 if ks["total"] > 0 else 0
        print(f"  {key}: {ks['diff']}/{ks['total']} ({rate:.1f}%)")

    if args.verbose:
        records = get_shadow_records(diff_only=True, limit=20)
        if records:
            print("\n最近差异记录:")
            for r in records:
                print(f"  [{r['timestamp']}] {r['prompt_key']} query={r['query'][:30]}")


def main():
    parser = argparse.ArgumentParser(description="提示词迭代流水线")
    sub = parser.add_subparsers(dest="command", help="子命令")

    p_publish = sub.add_parser("publish", help="发布新提示词版本")
    p_publish.add_argument("--key", required=True, help="提示词key")
    p_publish.add_argument("--template-text", default="", help="提示词内容")
    p_publish.add_argument("--file", help="从文件读取提示词")
    p_publish.add_argument("--description", default="", help="版本说明")

    p_rollback = sub.add_parser("rollback", help="回滚到上一版本")
    p_rollback.add_argument("--key", required=True, help="提示词key")
    p_rollback.add_argument("--version", type=int, default=None, help="目标版本号（默认上一版本）")

    p_eval = sub.add_parser("eval", help="运行黄金数据集评估")
    p_eval.add_argument("--pipeline", nargs="*", help="只评估指定流水线")
    p_eval.add_argument("--golden", default=None, help="黄金数据集路径")
    p_eval.add_argument("--output", default=None, help="输出目录")
    p_eval.add_argument("--label", default="", help="标签")

    p_diff = sub.add_parser("diff", help="对比两个评估结果")
    p_diff.add_argument("--before", required=True, help="旧版评估JSON")
    p_diff.add_argument("--after", required=True, help="新版评估JSON")
    p_diff.add_argument("--output", default=None, help="输出文件")

    p_iterate = sub.add_parser("iterate", help="一键迭代：评估基线→发布→评估→对比")
    p_iterate.add_argument("--key", required=True, help="提示词key")
    p_iterate.add_argument("--template-text", default="", help="新提示词内容")
    p_iterate.add_argument("--file", help="从文件读取新提示词")
    p_iterate.add_argument("--description", default="", help="版本说明")
    p_iterate.add_argument("--pipeline", nargs="*", help="只评估指定流水线")
    p_iterate.add_argument("--golden", default=None, help="黄金数据集路径")
    p_iterate.add_argument("--output", default=None, help="输出目录")

    p_shadow_start = sub.add_parser("shadow-start", help="启动影子测试")
    p_shadow_start.add_argument("--key", required=True, help="提示词key")
    p_shadow_start.add_argument("--version", type=int, required=True, help="影子版本号")

    p_shadow_stop = sub.add_parser("shadow-stop", help="停止影子测试")
    p_shadow_stop.add_argument("--key", required=True, help="提示词key")
    p_shadow_stop.add_argument("--version", type=int, required=True, help="影子版本号")

    p_shadow_stats = sub.add_parser("shadow-stats", help="查看影子测试统计")
    p_shadow_stats.add_argument("--verbose", "-v", action="store_true", help="显示差异详情")

    args = parser.parse_args()

    if not args.golden:
        args.golden = os.path.join(os.path.dirname(__file__), "..", "..", "data", "golden", "golden_dataset.json")

    commands = {
        "publish": cmd_publish,
        "rollback": cmd_rollback,
        "eval": cmd_eval,
        "diff": cmd_diff,
        "iterate": cmd_iterate,
        "shadow-start": cmd_shadow_start,
        "shadow-stop": cmd_shadow_stop,
        "shadow-stats": cmd_shadow_stats,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
