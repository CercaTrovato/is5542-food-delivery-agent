# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "langgraph==1.2.19",
#     "langchain==1.4.9",
#     "langchain-openai==1.7.4",
#     "starlette==1.10.0",
#     "uvicorn==0.54.0",
#     "httpx==0.28.1",
# ]
# ///

"""Check model failures and configuration privacy without making external API calls."""

import argparse
import json
import tempfile
from datetime import datetime
from pathlib import Path
import httpx
from openai import APIConnectionError, APIStatusError
from starlette.testclient import TestClient

from ord001_langchain import ScriptedOrderModel
from ord001_web import create_app
from ord001_web_service import DemoService, default_model

SENTINEL = "synthetic-private-credential-do-not-expose"


class FailingModel(ScriptedOrderModel):
    failure_status: int = 0

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        request = httpx.Request("POST", "https://api.deepseek.com/chat/completions",
                                headers={"Authorization": "Bearer " + SENTINEL})
        if not self.failure_status:
            raise APIConnectionError(request=request, message=SENTINEL)
        response = httpx.Response(self.failure_status, request=request)
        raise APIStatusError(SENTINEL, response=response, body={"error": SENTINEL})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for code, label in ((401, "无效凭据"), (402, "账户余额不足"), (429, "服务限流"), (0, "连接失败")):
        svc = DemoService(model=FailingModel(failure_status=code))
        try:
            with TestClient(create_app(svc)) as client:
                client.post("/api/customer/login", json={"customer_id": "U001"})
                response = client.post("/api/customer/messages", json={"text": "你好，请问您是？"})
                assert response.status_code == 503
                assert response.json()["error"] == "model_unavailable"
                assert SENTINEL not in response.text
                view = client.get("/api/customer/state").json()
                assert not view["tickets"] and view["confirmation"] is None
                assert SENTINEL not in json.dumps(svc.runs())
                results.append({"case": label + "有明确错误且不泄露凭据、不建单", "status": "passed"})
        finally:
            svc.store.close()

    with tempfile.TemporaryDirectory(prefix="ord001-config-") as directory:
        config = Path(directory) / "model.json"
        config.write_text(json.dumps({"model": "deepseek-flash", "base_url": "https://api.deepseek.com", "api_key": SENTINEL}))
        model, name = default_model(config)
        svc = DemoService(model=model, model_label=name)
        try:
            with TestClient(create_app(svc)) as client:
                response = client.get("/api/health")
                assert response.status_code == 200 and response.json()["model_mode"] == "live"
                assert SENTINEL not in response.text and "api_key" not in response.text
                assert str(config) not in response.text
                results.append({"case": "健康接口只返回模型模式，不包含密钥与私有配置路径", "status": "passed"})
        finally:
            svc.store.close()

    report = {"checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
              "mode": "isolated synthetic provider failures; no external API calls", "results": results,
              "summary": {"passed": len(results), "failed": 0}}
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
