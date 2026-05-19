import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "generate-learning-card.py"
spec = importlib.util.spec_from_file_location("generate_learning_card", MODULE_PATH)
generate_learning_card = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_learning_card)


class PromptDistillationTests(unittest.TestCase):
    def test_distills_first_3000_chars_into_concise_visual_brief(self):
        body = """
## 1. 构建系统的核心模型

| 对象 | 含义 |
|---|---|
| Source | 原始输入 |
| Rule | 如何生成输出 |
| Target | 可构建目标 |
| Artifact | 构建产物 |

```makefile
app: main.o util.o
	gcc main.o util.o -o app
```

## 2. 增量构建：只做必要的事
输入、命令、环境和工具链共同决定 cache key。

## 3. 调度执行
拓扑排序决定依赖顺序，并行 worker 执行互不依赖的节点。
""" + ("填充内容。" * 900) + "\n## 999. 超出 3000 字后不应进入摘要\n"

        brief = generate_learning_card.distill_learning_brief(body, max_source_chars=3000)

        self.assertLessEqual(len(brief), 1400)
        self.assertIn("构建系统的核心模型", brief)
        self.assertIn("增量构建", brief)
        self.assertIn("调度执行", brief)
        self.assertIn("Source", brief)
        self.assertIn("Artifact", brief)
        self.assertNotIn("```", brief)
        self.assertNotIn("gcc main.o", brief)
        self.assertNotIn("超出 3000 字后不应进入摘要", brief)

    def test_build_image_prompt_uses_distilled_brief_instead_of_raw_readme_body(self):
        readme = """---
day: 26
topic: Build System
status: planned
---

# Day 26：构建系统

## 核心模型
Source / Rule / Target / Artifact 是构建系统的四个核心对象。

```text
raw code fence should not be copied directly
```

## 缓存策略
基于内容哈希的 cache key 能支持远程缓存和可复现构建。
"""

        prompt = generate_learning_card.build_image_prompt(readme, "26", "Build System")

        self.assertIn("提炼后的内容 brief", prompt)
        self.assertIn("Source / Rule / Target / Artifact", prompt)
        self.assertIn("缓存策略", prompt)
        self.assertNotIn("raw code fence should not be copied directly", prompt)
        self.assertLess(len(prompt), 2600)

    def test_day26_prompt_is_compact_after_distilling_first_3000_chars(self):
        readme = (MODULE_PATH.parent / "day-26-build-system" / "README.md").read_text()

        prompt = generate_learning_card.build_image_prompt(readme, "26", "Build System")

        self.assertLess(len(prompt), 700)
        self.assertIn("Source / Rule / Target / Artifact", prompt)
        self.assertIn("内容哈希", prompt)
        self.assertIn("增量构建", prompt)
        self.assertNotIn("哪些文件变了", prompt)
        self.assertNotIn("在一个很小的项目里", prompt)
        self.assertNotIn("动态依赖很灵活", prompt)
        self.assertNotIn("远程缓存对大型仓库", prompt)

    def test_image_payload_can_disable_partial_images_for_stable_fallback(self):
        payload = generate_learning_card.build_image_payload(
            prompt="brief prompt",
            model="gpt-5.4",
            size="1024x1024",
            quality="high",
            partial_images=None,
        )

        tool = payload["tools"][0]
        self.assertEqual(payload["model"], "gpt-5.4")
        self.assertEqual(tool["type"], "image_generation")
        self.assertEqual(tool["model"], "gpt-image-2")
        self.assertEqual(tool["size"], "1024x1024")
        self.assertEqual(tool["quality"], "high")
        self.assertIs(payload["stream"], True)
        self.assertNotIn("partial_images", tool)

    def test_streaming_response_prefers_final_image_over_partial(self):
        final_b64 = "ZmluYWw="
        partial_b64 = "cGFydGlhbA=="
        lines = [
            b"event: response.image_generation_call.partial_image\n",
            json.dumps({
                "type": "response.image_generation_call.partial_image",
                "partial_image_b64": partial_b64,
            }).encode().join((b"data: ", b"\n")),
            b"\n",
            b"event: response.output_item.done\n",
            json.dumps({
                "type": "response.output_item.done",
                "item": {
                    "type": "image_generation_call",
                    "result": final_b64,
                },
            }).encode().join((b"data: ", b"\n")),
            b"\n",
            b"data: [DONE]\n\n",
        ]

        response = generate_learning_card._read_streaming_response(iter(lines))

        self.assertEqual(response["output"][0]["result"], final_b64)
        self.assertTrue(response["streamed"])

    def test_streaming_response_uses_partial_image_as_fallback(self):
        partial_b64 = "cGFydGlhbA=="
        lines = [
            b"event: response.image_generation_call.partial_image\n",
            json.dumps({
                "type": "response.image_generation_call.partial_image",
                "partial_image_b64": partial_b64,
            }).encode().join((b"data: ", b"\n")),
            b"\n",
            b"data: [DONE]\n\n",
        ]

        with contextlib.redirect_stderr(io.StringIO()):
            response = generate_learning_card._read_streaming_response(iter(lines))

        self.assertEqual(response["output"][0]["result"], partial_b64)
        self.assertTrue(response["partial_fallback"])

    def test_stable_prompt_is_ultra_compact_distilled_from_readme(self):
        readme = (MODULE_PATH.parent / "day-26-build-system" / "README.md").read_text()

        prompt = generate_learning_card.build_stable_image_prompt(readme, "26", "Build System")

        self.assertLess(len(prompt), 300)
        self.assertIn("Day 26", prompt)
        self.assertIn("构建系统", prompt)
        self.assertIn("Source/Rule/Target/Artifact", prompt)
        self.assertIn("内容哈希", prompt)
        self.assertIn("DAG调度", prompt)

    def test_generation_falls_back_to_1024_high_without_partial_images(self):
        calls = []
        original_call = generate_learning_card.call_gpt_image
        original_extract = generate_learning_card.extract_and_save
        try:
            def fake_call(api_key, prompt, model, size="1536x1024", quality="medium", partial_images=1):
                calls.append((model, size, quality, partial_images))
                if len(calls) < 3:
                    raise SystemExit(1)
                return {"output": [{"type": "image_generation_call", "result": "fake"}]}

            def fake_extract(response, output_path):
                return 1234567

            generate_learning_card.call_gpt_image = fake_call
            generate_learning_card.extract_and_save = fake_extract

            with contextlib.redirect_stdout(io.StringIO()):
                size, label = generate_learning_card.generate_with_fallbacks(
                    api_key="key",
                    prompt="prompt",
                    stable_prompt="stable prompt",
                    output_path=Path("out.png"),
                    primary_model="gpt-5.4",
                    fallback_model="gpt-5.5",
                )
        finally:
            generate_learning_card.call_gpt_image = original_call
            generate_learning_card.extract_and_save = original_extract

        self.assertEqual(size, 1234567)
        self.assertEqual(label, "stable-fallback")
        self.assertEqual(calls[0], ("gpt-5.4", "1536x1024", "medium", 1))
        self.assertEqual(calls[1], ("gpt-5.5", "1536x1024", "medium", 1))
        self.assertEqual(calls[2], ("gpt-5.4", "1024x1024", "high", None))


if __name__ == "__main__":
    unittest.main()
