"""Model adapters.

Every adapter exposes the same method:

    chat(system, messages, tools) -> {"text", "tool_calls", "usage"}

Messages use one internal format so the agent loop never cares which
provider it is talking to:

    {"role": "user", "content": str}
    {"role": "assistant", "text": str, "tool_calls": [{"id", "name", "args"}]}
    {"role": "tool", "id": str, "name": str, "content": str}

Only the standard library is used (urllib), so there are no SDK versions
to pin. API keys come from OPENAI_API_KEY and ANTHROPIC_API_KEY.
"""

import json
import os
import urllib.error
import urllib.request


class ModelError(Exception):
    pass


def _post(url, headers, body, timeout=120):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise ModelError(f"HTTP {e.code}: {e.read().decode()[:500]}") from e
    except urllib.error.URLError as e:
        raise ModelError(f"Network error: {e.reason}") from e


class AnthropicModel:
    def __init__(self, model):
        self.name = f"anthropic:{model}"
        self.model = model
        self.key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.key:
            raise ModelError("Set ANTHROPIC_API_KEY to use Anthropic models.")

    def _convert(self, messages):
        out = []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks = []
                if m.get("text"):
                    blocks.append({"type": "text", "text": m["text"]})
                for tc in m.get("tool_calls", []):
                    blocks.append({"type": "tool_use", "id": tc["id"],
                                   "name": tc["name"], "input": tc["args"]})
                out.append({"role": "assistant", "content": blocks})
            elif m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["id"],
                         "content": m["content"]}
                # Consecutive tool results belong in one user message.
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
        return out

    def chat(self, system, messages, tools):
        body = {
            "model": self.model,
            "max_tokens": 2048,
            "system": system,
            "messages": self._convert(messages),
        }
        if tools:
            body["tools"] = [{"name": t["name"], "description": t["description"],
                              "input_schema": t["parameters"]} for t in tools]
        data = _post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self.key, "anthropic-version": "2023-06-01",
             "content-type": "application/json"},
            body,
        )
        text, calls = [], []
        for block in data.get("content", []):
            if block["type"] == "text":
                text.append(block["text"])
            elif block["type"] == "tool_use":
                calls.append({"id": block["id"], "name": block["name"],
                              "args": block.get("input", {})})
        usage = data.get("usage", {})
        return {"text": "\n".join(text), "tool_calls": calls,
                "usage": {"input": usage.get("input_tokens", 0),
                          "output": usage.get("output_tokens", 0)}}


class OpenAIModel:
    def __init__(self, model):
        self.name = f"openai:{model}"
        self.model = model
        self.key = os.environ.get("OPENAI_API_KEY")
        if not self.key:
            raise ModelError("Set OPENAI_API_KEY to use OpenAI models.")

    def _convert(self, system, messages):
        out = [{"role": "system", "content": system}]
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                msg = {"role": "assistant", "content": m.get("text") or None}
                if m.get("tool_calls"):
                    msg["tool_calls"] = [
                        {"id": tc["id"], "type": "function",
                         "function": {"name": tc["name"],
                                      "arguments": json.dumps(tc["args"])}}
                        for tc in m["tool_calls"]]
                out.append(msg)
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["id"],
                            "content": m["content"]})
        return out

    def chat(self, system, messages, tools):
        body = {"model": self.model, "messages": self._convert(system, messages)}
        if tools:
            body["tools"] = [{"type": "function",
                              "function": {"name": t["name"],
                                           "description": t["description"],
                                           "parameters": t["parameters"]}}
                             for t in tools]
        data = _post(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {self.key}",
             "content-type": "application/json"},
            body,
        )
        msg = data["choices"][0]["message"]
        calls = []
        for tc in msg.get("tool_calls") or []:
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {"_unparseable": tc["function"]["arguments"]}
            calls.append({"id": tc["id"], "name": tc["function"]["name"], "args": args})
        usage = data.get("usage", {})
        return {"text": msg.get("content") or "", "tool_calls": calls,
                "usage": {"input": usage.get("prompt_tokens", 0),
                          "output": usage.get("completion_tokens", 0)}}


class MockModel:
    """Offline stand-in for smoke-testing the harness itself.

    It replays each task's optional `mock` script (tool calls, then a final
    reply), so you can check the runner, graders and report without spending
    API credits. It is not a benchmark of anything.
    """

    def __init__(self, model="oracle"):
        self.name = f"mock:{model}"
        self.script = {}

    def load_task(self, task):
        self.script = task.get("mock", {})

    def chat(self, system, messages, tools):
        planned = self.script.get("tool_calls", [])
        done = sum(1 for m in messages if m["role"] == "tool")
        if done < len(planned):
            tc = planned[done]
            return {"text": "", "usage": {"input": 0, "output": 0},
                    "tool_calls": [{"id": f"mock_{done}", "name": tc["name"],
                                    "args": tc.get("args", {})}]}
        return {"text": self.script.get("reply", ""), "tool_calls": [],
                "usage": {"input": 0, "output": 0}}


def load_model(spec):
    """Turn 'provider:model-name' into an adapter, e.g. 'anthropic:claude-sonnet-5-5'."""
    provider, _, model = spec.partition(":")
    if provider == "anthropic":
        return AnthropicModel(model)
    if provider == "openai":
        return OpenAIModel(model)
    if provider == "mock":
        return MockModel(model or "oracle")
    raise ModelError(f"Unknown provider '{provider}'. Use anthropic:, openai: or mock:.")
