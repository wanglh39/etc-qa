import argparse
import json
import os


def compute_cer(reference: str, hypothesis: str) -> float:
    ref_chars = list(reference)
    hyp_chars = list(hypothesis)

    m = len(ref_chars)
    n = len(hyp_chars)

    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_chars[i - 1] == hyp_chars[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    return dp[m][n] / m if m > 0 else 0.0


def evaluate(test_file: str, asr_service=None):
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"测试文件不存在: {test_file}")

    with open(test_file, encoding="utf-8") as f:
        test_data = json.load(f)

    if asr_service is None:
        from asr.service import get_asr_service

        asr_service = get_asr_service()

    results = []
    total_cer = 0.0
    count = 0

    for item in test_data:
        audio_path = item["audio"]
        reference = item["text"]

        try:
            response = asr_service.transcribe(audio_path)
            hypothesis = response.text
            cer = compute_cer(reference, hypothesis)
            total_cer += cer
            count += 1
            results.append(
                {
                    "audio": audio_path,
                    "reference": reference,
                    "hypothesis": hypothesis,
                    "cer": round(cer, 4),
                }
            )
        except Exception as e:
            results.append(
                {
                    "audio": audio_path,
                    "reference": reference,
                    "error": str(e),
                }
            )

    avg_cer = total_cer / count if count > 0 else 0.0
    print(f"评估完成: {count}条, 平均CER: {avg_cer:.4f} ({avg_cer * 100:.2f}%)")
    return {"avg_cer": avg_cer, "count": count, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ASR CER评估")
    parser.add_argument("--test-file", required=True, help="测试数据JSON文件")
    args = parser.parse_args()
    evaluate(args.test_file)
