"""Tests for voucher vectorize message consumer."""

from pathlib import Path
import sys
import types
from typing import Any


def _prepare_src_import_path() -> None:
    """Ensure src directory is importable for modules.* imports."""
    test_file: Path = Path(__file__).resolve()
    project_root: Path = test_file.parents[4]
    src_root: Path = project_root / "src"
    src_root_str: str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


def _install_fake_rocketmq() -> None:
    """Install a lightweight rocketmq module stub for unit tests."""
    fake_module = types.ModuleType("rocketmq")

    class ClientConfiguration:
        def __init__(self, endpoints: str, credentials: Any) -> None:
            self.endpoints = endpoints
            self.credentials = credentials

    class Credentials:
        pass

    class Message:
        topic: str
        keys: str
        tag: str
        body: bytes

    class Producer:
        def __init__(self, config: Any, topics: tuple[str, ...]) -> None:
            self.config = config
            self.topics = topics

        def startup(self) -> None:
            return None

        def send(self, message: Any) -> Any:
            return types.SimpleNamespace(message_id="fake", status="SUCCESS")

        def shutdown(self) -> None:
            return None

    class ConsumeResult:
        SUCCESS = "SUCCESS"

    class FilterExpression:
        def __init__(self, expression: str) -> None:
            self.expression = expression

    class MessageListener:
        pass

    class PushConsumer:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def startup(self) -> None:
            return None

        def shutdown(self) -> None:
            return None

    fake_module.ClientConfiguration = ClientConfiguration
    fake_module.Credentials = Credentials
    fake_module.Message = Message
    fake_module.Producer = Producer
    fake_module.ConsumeResult = ConsumeResult
    fake_module.FilterExpression = FilterExpression
    fake_module.MessageListener = MessageListener
    fake_module.PushConsumer = PushConsumer
    sys.modules["rocketmq"] = fake_module


def _build_valid_payload() -> dict[str, Any]:
    """Build valid camelCase payload for voucher dto."""
    return {
        "operation": "UPDATE",
        "id": 201,
        "shopId": 301,
        "shopName": "BBQ",
        "x": 120.1,
        "y": 30.2,
        "h3hex": "8a2a1072b59ffff",
        "title": "套餐",
        "description": "描述",
        "rules": "规则",
        "payValue": 100,
        "actualValue": 150,
        "type": 0,
        "status": 1,
        "createTime": "2026-01-01T00:00:00",
        "updateTime": "2026-01-01T00:00:00",
        "dailyLimit": 10,
    }


def test_parse_payload_success_and_missing_required() -> None:
    """Parse returns dto for valid payload and None for invalid payload."""
    _prepare_src_import_path()
    _install_fake_rocketmq()
    from modules.table_vectorize.listener.voucher_vectorize_message_consumer import (
        VoucherVectorizeMessageConsumer,
    )

    class FakeService:
        """Fake service used for consumer construction."""

        async def handle_message(self, dto: Any) -> None:
            return None

    class FakeProducer:
        """Fake producer used for consumer construction."""

        def send_vectorize_task(self, payload: Any, retry_count: int = 0) -> None:
            return None

    consumer = VoucherVectorizeMessageConsumer(FakeService(), FakeProducer())

    payload = consumer.parse_payload(_build_valid_payload())
    assert payload is not None
    assert payload.id == 201
    assert payload.retry_count == 0

    invalid_payload = _build_valid_payload()
    invalid_payload.pop("title")
    assert consumer.parse_payload(invalid_payload) is None


def test_requeue_payload_increments_retry_count() -> None:
    """Requeue sends payload through producer with next retry count."""
    _prepare_src_import_path()
    _install_fake_rocketmq()
    from modules.table_vectorize.listener.voucher_vectorize_message_consumer import (
        VoucherVectorizeMessageConsumer,
    )

    class FakeService:
        """Fake service used for consumer construction."""

        async def handle_message(self, dto: Any) -> None:
            return None

    class FakeProducer:
        """Fake producer that captures send calls."""

        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def send_vectorize_task(self, payload: Any, retry_count: int = 0) -> None:
            self.calls.append({"payload": payload, "retry_count": retry_count})

    producer = FakeProducer()
    consumer = VoucherVectorizeMessageConsumer(FakeService(), producer)
    parsed = consumer.parse_payload(_build_valid_payload())
    assert parsed is not None

    consumer.requeue_payload(parsed, retry_count=parsed.retry_count + 1)

    assert len(producer.calls) == 1
    assert producer.calls[0]["retry_count"] == 1
