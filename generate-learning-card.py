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


def _clean_markdown_inline(text: str) -> str:
    """Remove Markdown syntax that makes image prompts noisy."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" >-*_|")


def _append_unique(items: list[str], value: str) -> None:
    value = _clean_markdown_inline(value)
    if not value or len(value) < 2:
        return
    if value.endswith(("？", "?")):
        return
    if re.fullmatch(r"[-:|\s]+", value):
        return
    if value not in items:
        items.append(value)


def _brief_score(item: str) -> int:
    score = 0
    lower = item.lower()
    if re.search(r"day\s*\d+|：|build system|构建系统", item, re.IGNORECASE):
        score += 5
    if re.search(r"Source|Rule|Target|Artifact|source|rule|target|artifact", item):
        score += 10
    if "DAG" in item or "有向无环图" in item or "依赖图" in item:
        score += 9
    if "增量" in item:
        score += 8
    if "内容哈希" in item or "哈希" in item or "hash" in lower or "cache" in lower or "缓存" in item:
        score += 8
    if "时间戳" in item:
        score += 6
    if "调度" in item or "拓扑" in item or "并行" in item or "scheduler" in lower:
        score += 7
    if "依赖" in item:
        score += 5
    if "工具链" in item or "可复现" in item:
        score += 5
    if item.endswith("：") or re.match(r"^\d+(?:\.\d+)*[.)、]?\s*", item):
        score -= 2
    if len(item) > 90:
        score -= 1
    return score


def distill_learning_brief(
    body: str,
    max_source_chars: int = 3000,
    max_brief_chars: int = 380,
) -> str:
    """Distill the first part of a README into a compact image brief.

    The image model is sensitive to raw long Markdown.  We still honor the
    first-3000-character source window, but convert it into headings, table
    rows, and short concept statements before building the final prompt.
    """
    source = body[:max_source_chars]
    source = re.sub(r"```.*?```", "", source, flags=re.DOTALL)

    domain_lines: list[str] = []
    if "构建系统" in source or all(term in source for term in ("Source", "Rule", "Target", "Artifact")):
        _append_unique(domain_lines, "构建系统的核心模型：source → graph → schedule → cache → artifact")
        if all(term in source for term in ("Source", "Rule", "Target", "Artifact")):
            _append_unique(domain_lines, "Source / Rule / Target / Artifact：输入、规则、目标、产物")
        if "增量" in source or "时间戳" in source or "内容哈希" in source:
            _append_unique(domain_lines, "增量构建：时间戳快但粗糙；内容哈希更适合缓存与可复现")
        if "DAG" in source or "有向无环图" in source or "调度" in source:
            _append_unique(domain_lines, "调度执行：DAG 拓扑排序，互不依赖的节点并行执行")
        if "缓存" in source or "cache" in source.lower():
            _append_unique(domain_lines, "缓存策略：输入、命令、环境、工具链共同决定 cache key")
        if "可复现" in source or "工具链" in source:
            _append_unique(domain_lines, "系统视角：依赖图 + 变更检测 + 调度器 + 缓存策略")
        if domain_lines:
            return "\n".join(f"- {line}" for line in domain_lines)

    items: list[str] = []
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            _append_unique(items, heading.group(2))
            continue

        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                _append_unique(items, " / ".join(cells))
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        if bullet:
            _append_unique(items, bullet.group(1))
            continue

        numbered = re.match(r"^\d+(?:\.\d+)*[.)、]\s*(.+)$", line)
        if numbered:
            _append_unique(items, numbered.group(1))
            continue

        # Keep short explanatory statements, but avoid dumping paragraphs.
        cleaned = _clean_markdown_inline(line)
        if cleaned.endswith(("？", "?")):
            continue
        has_signal = re.search(
            r"DAG|cache|hash|Source|Rule|Target|Artifact|scheduler|build|构建|缓存|依赖|调度|产物|增量|时间戳|哈希|工具链|可复现|拓扑|并行|输入|输出|规则|目标",
            cleaned,
            re.IGNORECASE,
        )
        if has_signal and len(cleaned) <= 120:
            _append_unique(items, cleaned)

    if all(term in source for term in ("Source", "Rule", "Target", "Artifact")):
        _append_unique(items, "Source / Rule / Target / Artifact：输入、规则、目标、产物")
    if "内容哈希" in source or "hash" in source.lower():
        _append_unique(items, "内容哈希：输入、命令、环境、工具链共同决定 cache key")

    ranked_items = sorted(enumerate(items), key=lambda pair: (-_brief_score(pair[1]), pair[0]))
    brief_lines: list[str] = []
    total = 0
    for _, item in ranked_items:
        line = f"- {item}"
        if total + len(line) + 1 > max_brief_chars:
            continue
        brief_lines.append(line)
        total += len(line) + 1

    if not brief_lines:
        fallback = _clean_markdown_inline(source[:max_brief_chars])
        return f"- {fallback}" if fallback else "- 主题要点不足，请围绕标题生成原理型学习海报"
    return "\n".join(brief_lines)


def build_image_prompt(readme: str, day_num: str, topic: str) -> str:
    """构造图片生成的 prompt：先取 README 前 3000 字，再提炼为视觉 brief。"""
    parts = readme.split("---", 2)
    body = parts[2].strip() if len(parts) >= 3 else readme
    brief = distill_learning_brief(body)

    topic_guard = ""
    if "build" in topic.lower() or "构建" in topic:
        topic_guard = "；必须是软件构建系统，不要画成 ML/数据 pipeline"

    prompt = f"""生成暗色科技风中文学习海报，横版大图。
标题：Day {day_num} · {topic}
风格：#0D1117 深色背景，#161b22 卡片，霓虹蓝 #38BDF8、橙 #F97316、紫 #A78BFA；高信息密度但文字清晰；不要人物/卡通/手机社交卡片{topic_guard}。

提炼后的内容 brief:
{brief}

版式：顶部大标题；中央发光 DAG/流程图；周围 2-3 列知识卡片；每卡含编号、中文标题、英文标签、2-3 个短要点；右下角放「系统视角」总结；底部小字 build your own learning card · Day {day_num}。"""
    return prompt


def build_stable_image_prompt(readme: str, day_num: str, topic: str) -> str:
    """Ultra-compact fallback prompt distilled from the same first-3000-char source window."""
    parts = readme.split("---", 2)
    body = parts[2].strip() if len(parts) >= 3 else readme
    source = body[:3000]
    if "构建系统" in source or "build" in topic.lower():
        return (
            f"Day {day_num} 构建系统 Build System。暗色科技风中文学习海报。"
            "内容：source→graph→schedule→cache→artifact；"
            "Source/Rule/Target/Artifact；增量构建；内容哈希；DAG调度；缓存策略。"
        )
    brief = distill_learning_brief(body, max_brief_chars=180).replace("\n- ", "；").lstrip("- ")
    return f"Day {day_num} {topic}。暗色科技风中文学习海报。内容：{brief}"


def build_image_payload(
    prompt: str,
    model: str,
    size: str = IMAGE_SIZE,
    quality: str = IMAGE_QUALITY,
    partial_images: int | None = 1,
) -> dict:
    tool = {
        "type": "image_generation",
        "model": "gpt-image-2",
        "size": size,
        "quality": quality,
        "output_format": "png",
    }
    if partial_images is not None:
        tool["partial_images"] = partial_images

    return {
        "model": model,
        "store": False,
        "stream": True,
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
        "tools": [tool],
        "tool_choice": {
            "type": "allowed_tools",
            "mode": "required",
            "tools": [{"type": "image_generation"}],
        },
    }


def _extract_image_b64(response: dict) -> tuple[str | None, list[str]]:
    """Return the first final image_generation result from a Responses object."""
    img_b64 = None
    output_types = []
    for item in response.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        output_types.append(item.get("type"))
        if item.get("type") == "image_generation_call" and item.get("result"):
            img_b64 = item["result"]
            break
    return img_b64, output_types


def _iter_sse_events(response):
    """Yield ``(event_name, data)`` pairs from a text/event-stream response."""
    event_name = None
    data_lines = []

    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            if data_lines:
                yield event_name, "\n".join(data_lines)
                event_name = None
                data_lines = []
            continue

        if line.startswith(":"):
            continue

        field, sep, value = line.partition(":")
        if not sep:
            continue
        if value.startswith(" "):
            value = value[1:]

        if field == "event":
            event_name = value
        elif field == "data":
            data_lines.append(value)

    if data_lines:
        yield event_name, "\n".join(data_lines)


def _stream_error_message(payload: dict) -> str | None:
    error = payload.get("error")
    if isinstance(error, dict):
        return error.get("message") or json.dumps(error, ensure_ascii=False)
    if isinstance(error, str):
        return error

    response = payload.get("response")
    if isinstance(response, dict):
        response_error = response.get("error")
        if isinstance(response_error, dict):
            return response_error.get("message") or json.dumps(response_error, ensure_ascii=False)
        if isinstance(response_error, str):
            return response_error

    return None


def _read_streaming_response(response) -> dict:
    """Read Responses SSE and return a normal image_generation output object."""
    final_b64 = None
    last_partial_b64 = None
    output_types = []
    last_error = None

    for event_name, data in _iter_sse_events(response):
        if data == "[DONE]":
            continue

        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue

        event_type = payload.get("type") or event_name or ""

        item = payload.get("item")
        if isinstance(item, dict):
            output_types.append(item.get("type"))
            if item.get("type") == "image_generation_call" and item.get("result"):
                final_b64 = item["result"]

        response_payload = payload.get("response")
        if isinstance(response_payload, dict):
            img_b64, types = _extract_image_b64(response_payload)
            output_types.extend(types)
            if img_b64:
                final_b64 = img_b64

        img_b64, types = _extract_image_b64(payload)
        output_types.extend(types)
        if img_b64:
            final_b64 = img_b64

        if event_type == "response.image_generation_call.partial_image":
            partial = payload.get("partial_image_b64")
            if isinstance(partial, str) and partial:
                last_partial_b64 = partial

        message = _stream_error_message(payload)
        if message:
            last_error = message

    if final_b64:
        return {
            "output": [{"type": "image_generation_call", "result": final_b64}],
            "streamed": True,
        }

    if last_partial_b64:
        print("WARN: 流式响应缺少最终图片，使用最后一张 partial image 兜底", file=sys.stderr)
        return {
            "output": [{"type": "image_generation_call", "result": last_partial_b64}],
            "streamed": True,
            "partial_fallback": True,
        }

    if last_error:
        raise RuntimeError(last_error)

    return {
        "output": [{"type": item_type} for item_type in output_types if item_type],
        "streamed": True,
    }


def call_gpt_image(
    api_key: str,
    prompt: str,
    model: str,
    size: str = IMAGE_SIZE,
    quality: str = IMAGE_QUALITY,
    partial_images: int | None = 1,
) -> dict:
    """调用 Sub2API /v1/responses 获取图片"""
    payload = build_image_payload(
        prompt=prompt,
        model=model,
        size=size,
        quality=quality,
        partial_images=partial_images,
    )

    req = urllib.request.Request(
        SUB2API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            content_type = r.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                return _read_streaming_response(r)
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        print(body[:500], file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def extract_and_save(response: dict, output_path: Path) -> int:
    """从响应中提取 base64 图片并保存，返回字节数"""
    img_b64, output_types = _extract_image_b64(response)

    if not img_b64:
        print(f"ERROR: 响应中没有 image_generation_call 类型的输出", file=sys.stderr)
        print(f"output types: {output_types}", file=sys.stderr)
        sys.exit(1)

    img_bytes = base64.b64decode(img_b64)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(img_bytes)
    return len(img_bytes)


def generate_with_fallbacks(
    api_key: str,
    prompt: str,
    stable_prompt: str,
    output_path: Path,
    primary_model: str,
    fallback_model: str,
) -> tuple[int, str]:
    attempts = [
        (primary_model, IMAGE_SIZE, IMAGE_QUALITY, 1, "primary"),
        (fallback_model, IMAGE_SIZE, IMAGE_QUALITY, 1, "fallback"),
        (primary_model, "1024x1024", "high", None, "stable-fallback"),
    ]

    for idx, (model, size, quality, partial_images, label) in enumerate(attempts):
        if label == "stable-fallback":
            print("\n正在调用稳定回退方案 1024x1024/high/no-partial + gpt-image-2 ...")
        else:
            print(f"\n正在调用 {model} + gpt-image-2 ...")
        try:
            response = call_gpt_image(
                api_key,
                stable_prompt if label == "stable-fallback" else prompt,
                model,
                size=size,
                quality=quality,
                partial_images=partial_images,
            )
            size_bytes = extract_and_save(response, output_path)
            print(f"OK: {size_bytes} bytes -> {output_path}")
            return size_bytes, label
        except SystemExit:
            if idx == len(attempts) - 1:
                print("ERROR: 主模型、回退模型和稳定回退方案都失败了", file=sys.stderr)
                raise
            next_label = attempts[idx + 1][4]
            if next_label == "stable-fallback":
                print("标准大图方案失败，尝试稳定回退方案 ...")
            else:
                print(f"主模型 {model} 失败，尝试回退模型 {fallback_model} ...")
            continue

    raise SystemExit(1)


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
    stable_prompt = build_stable_image_prompt(readme, day_num, topic)

    size, mode = generate_with_fallbacks(
        api_key=api_key,
        prompt=prompt,
        stable_prompt=stable_prompt,
        output_path=output_path,
        primary_model=args.model,
        fallback_model=args.fallback_model,
    )
    print(f"生成模式: {mode}")

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
