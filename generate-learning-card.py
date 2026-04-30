#!/usr/bin/env python3
"""
generate-learning-card.py
硬编码走 gpt-image-2 via Sub2API /v1/responses，不允许任何其他生成方式。

用法: python3 generate-learning-card.py <readme_path> <output_path> [--model gpt-5.4]

守门规则:
  1. 必须从 /v1/responses 拿到 image_generation_call 类型的输出
  2. 最终 PNG 必须 >= 1MB，否则判定为异常
  3. 退出码 0=成功，1=失败
"""

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

MIN_SIZE_BYTES = 1024 * 1024  # 1MB 守门
SUB2API_URL = "http://127.0.0.1:8080/v1/responses"
IMAGE_SIZE = "1536x1024"
IMAGE_QUALITY = "medium"


def read_api_key() -> str:
    auth_path = Path.home() / ".codex" / "auth.json"
    if not auth_path.exists():
        print("ERROR: ~/.codex/auth.json 不存在", file=sys.stderr)
        sys.exit(1)
    data = json.loads(auth_path.read_text())
    key = data.get("OPENAI_API_KEY", "")
    if not key:
        print("ERROR: OPENAI_API_KEY 为空", file=sys.stderr)
        sys.exit(1)
    return key


def extract_metadata(readme: str) -> tuple:
    """从 README frontmatter 提取 day 和 topic"""
    day_num = "?"
    topic = "Unknown"
    fm_match = re.search(r"^---\s*\n(.*?)\n---", readme, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        m = re.search(r"^day:\s*(.+)$", fm, re.MULTILINE)
        if m:
            day_num = m.group(1).strip()
        m = re.search(r"^topic:\s*(.+)$", fm, re.MULTILINE)
        if m:
            topic = m.group(1).strip()
    return day_num, topic


def build_image_prompt(readme: str, day_num: str, topic: str) -> str:
    """构造图片生成的 prompt"""
    # 提取正文（跳过 frontmatter）
    parts = readme.split("---", 2)
    body = parts[2].strip() if len(parts) >= 3 else readme
    # 截取前 3000 字符
    body = body[:3000]

    prompt = f"""Generate a dark-tech style Chinese learning poster (dark background #0D1117, bright accent colors #38BDF8 #F97316 #A78BFA).

Title: Day {day_num} · {topic}

Instructions:
- 全部使用中文
- 暗色科技风，高信息密度，原理理解型
- 不要手机社交卡片风格，要大尺寸学习海报
- 卡片式布局，每个知识点一个独立模块
- 包含以下内容板块：
{body}

Layout:
- 顶部大标题区域（Day 编号 + 中文主题 + 英文副标题）
- 主体用卡片网格布局（2-3列），每个知识点一个圆角卡片
- 每个卡片有编号、中文标题、英文标签、要点列表
- 右下角或底部放「系统视角」总结模块
- 底部留一行小字：build your own learning card · Day {day_num}

Style:
- 背景 #0D1117 深色渐变
- 卡片 #161b22 + 半透明描边
- 三色体系：天蓝 #38BDF8、橙 #F97316、紫 #A78BFA
- 中文用 Noto Sans SC / 黑体
- 关键词用胶囊标签样式
- 信息密度要高，不要留大量空白"""
    return prompt


def call_gpt_image(api_key: str, prompt: str, model: str) -> dict:
    """调用 Sub2API /v1/responses 获取图片"""
    payload = {
        "model": model,
        "store": False,
        "instructions": (
            "You are an assistant that generates images. "
            "When the user describes a poster or card, you MUST use the "
            "image_generation tool to create it. Do not describe the image "
            "or write code to draw it."
        ),
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        "tools": [
            {
                "type": "image_generation",
                "model": "gpt-image-2",
                "size": IMAGE_SIZE,
                "quality": IMAGE_QUALITY,
                "output_format": "png",
                "partial_images": 1,
            }
        ],
        "tool_choice": {
            "type": "allowed_tools",
            "mode": "required",
            "tools": [{"type": "image_generation"}],
        },
    }

    req = urllib.request.Request(
        SUB2API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        print(body[:500], file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def extract_and_save(response: dict, output_path: Path) -> int:
    """从响应中提取 base64 图片并保存，返回字节数"""
    img_b64 = None
    output_types = []
    for item in response.get("output", []):
        output_types.append(item.get("type"))
        if item.get("type") == "image_generation_call" and item.get("result"):
            img_b64 = item["result"]
            break

    if not img_b64:
        print(f"ERROR: 响应中没有 image_generation_call 类型的输出", file=sys.stderr)
        print(f"output types: {output_types}", file=sys.stderr)
        sys.exit(1)

    img_bytes = base64.b64decode(img_b64)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(img_bytes)
    return len(img_bytes)


def main():
    parser = argparse.ArgumentParser(description="Generate learning card via gpt-image-2")
    parser.add_argument("readme_path", help="Path to the day's README.md")
    parser.add_argument("output_path", help="Output PNG path")
    parser.add_argument("--model", default="gpt-5.4", help="Primary text model (default: gpt-5.4)")
    parser.add_argument("--fallback-model", default="gpt-5.5", help="Fallback model if primary fails")
    args = parser.parse_args()

    readme_path = Path(args.readme_path)
    output_path = Path(args.output_path)

    # 检查 README
    if not readme_path.exists():
        print(f"ERROR: README 不存在: {readme_path}", file=sys.stderr)
        sys.exit(1)

    readme = readme_path.read_text()
    if len(readme) < 200:
        print(f"ERROR: README 内容太短 ({len(readme)} chars)，可能不完整", file=sys.stderr)
        sys.exit(1)

    day_num, topic = extract_metadata(readme)
    api_key = read_api_key()

    print("--- generate-learning-card.py ---")
    print(f"README:    {readme_path}")
    print(f"Output:    {output_path}")
    print(f"Day/Topic: Day {day_num} · {topic}")
    print(f"Model:     primary={args.model}, fallback={args.fallback_model}, image=gpt-image-2")
    print(f"Endpoint:  {SUB2API_URL}")
    print(f"Min size:  {MIN_SIZE_BYTES} bytes")
    print("--------------------------------")

    prompt = build_image_prompt(readme, day_num, topic)

    # 尝试主模型，失败则回退
    for model in [args.model, args.fallback_model]:
        print(f"\n正在调用 {model} + gpt-image-2 ...")
        try:
            response = call_gpt_image(api_key, prompt, model)
            size = extract_and_save(response, output_path)
            print(f"OK: {size} bytes -> {output_path}")
            break
        except SystemExit:
            if model == args.fallback_model:
                print("ERROR: 主模型和回退模型都失败了", file=sys.stderr)
                raise
            print(f"主模型 {model} 失败，尝试回退模型 {args.fallback_model} ...")
            continue

    # 文件大小守门
    actual_size = output_path.stat().st_size
    print(f"文件大小: {actual_size} bytes")

    if actual_size < MIN_SIZE_BYTES:
        print(
            f"ERROR: 文件大小 ({actual_size}) 低于守门阈值 ({MIN_SIZE_BYTES})，"
            f"疑似非 gpt-image-2 产出",
            file=sys.stderr,
        )
        sys.exit(1)

    # 验证 PNG magic bytes
    header = output_path.read_bytes()[:8]
    if header[:4] == b"\x89PNG":
        print(f"验证通过: 有效 PNG")
    else:
        print(f"ERROR: 不是有效 PNG (header: {header[:4].hex()})", file=sys.stderr)
        sys.exit(1)

    print(f"\n✅ 学习卡片生成成功: {output_path} ({actual_size} bytes)")


if __name__ == "__main__":
    main()
