import pytest

from config.schemas import (
    VALIDATORS,
    AsrConfig,
    CacheConfig,
    DedupConfig,
    HydeConfig,
    LlmConfig,
    MilvusEnvConfig,
    MysqlEnvConfig,
    MysqlPoolConfig,
    ServerConfig,
    ThresholdConfig,
    validate_config,
)


class TestServerConfig:
    def test_valid(self):
        c = ServerConfig(port=8000, title="test", version="1.0", workers=1)
        assert c.host == "0.0.0.0"
        assert c.workers == 1

    def test_port_out_of_range(self):
        with pytest.raises(Exception):
            ServerConfig(port=0, title="test", version="1.0", workers=1)

    def test_port_too_high(self):
        with pytest.raises(Exception):
            ServerConfig(port=70000, title="test", version="1.0", workers=1)

    def test_workers_zero(self):
        with pytest.raises(Exception):
            ServerConfig(port=8000, title="test", version="1.0", workers=0)


class TestCacheConfig:
    def test_valid(self):
        c = CacheConfig(active_ids_ttl=30, config_ttl=60)
        assert c.active_ids_ttl == 30

    def test_ttl_zero(self):
        with pytest.raises(Exception):
            CacheConfig(active_ids_ttl=0, config_ttl=60)


class TestMysqlEnvConfig:
    def test_valid(self):
        c = MysqlEnvConfig(
            host="localhost",
            port=3306,
            user="root",
            password="123",
            database="test",
            pool=MysqlPoolConfig(max_usage=100, ping=5),
        )
        assert c.host == "localhost"

    def test_port_invalid(self):
        with pytest.raises(Exception):
            MysqlEnvConfig(
                host="localhost",
                port=0,
                user="root",
                password="123",
                database="test",
                pool=MysqlPoolConfig(max_usage=100, ping=5),
            )


class TestMilvusEnvConfig:
    def test_valid(self):
        c = MilvusEnvConfig(db_path="./test.db", collection_name="qa")
        assert c.db_path == "./test.db"


class TestLlmConfig:
    def test_valid(self):
        c = LlmConfig(
            enabled=True,
            provider="openai",
            api_key="sk-xxx",
            base_url="https://api.example.com",
            model="gpt-4",
            temperature=0.1,
            max_tokens=1024,
        )
        assert c.temperature == 0.0 or c.temperature >= 0

    def test_api_key_empty(self):
        with pytest.raises(Exception):
            LlmConfig(
                enabled=True,
                provider="openai",
                api_key="",
                base_url="https://api.example.com",
                model="gpt-4",
                temperature=0.1,
                max_tokens=1024,
            )

    def test_api_key_env_placeholder(self):
        with pytest.raises(Exception):
            LlmConfig(
                enabled=True,
                provider="openai",
                api_key="${DEEPSEEK_KEY}",
                base_url="https://api.example.com",
                model="gpt-4",
                temperature=0.1,
                max_tokens=1024,
            )

    def test_temperature_out_of_range(self):
        with pytest.raises(Exception):
            LlmConfig(
                enabled=True,
                provider="openai",
                api_key="sk-xxx",
                base_url="https://api.example.com",
                model="gpt-4",
                temperature=3.0,
                max_tokens=1024,
            )


class TestThresholdConfig:
    def test_gap_mode(self):
        c = ThresholdConfig(
            mode="gap",
            gap_high=0.15,
            gap_mid=0.08,
            gap_low=0.03,
            floor_high=0.5,
            floor_mid=0.3,
            floor_low=0.15,
            high=0.7,
            low=0.3,
            min=0.1,
        )
        assert c.mode == "gap"

    def test_absolute_mode(self):
        c = ThresholdConfig(
            mode="absolute",
            gap_high=0.15,
            gap_mid=0.08,
            gap_low=0.03,
            floor_high=0.5,
            floor_mid=0.3,
            floor_low=0.15,
            high=0.7,
            low=0.3,
            min=0.1,
        )
        assert c.mode == "absolute"

    def test_invalid_mode(self):
        with pytest.raises(Exception):
            ThresholdConfig(
                mode="invalid",
                gap_high=0.15,
                gap_mid=0.08,
                gap_low=0.03,
                floor_high=0.5,
                floor_mid=0.3,
                floor_low=0.15,
                high=0.7,
                low=0.3,
                min=0.1,
            )


class TestAsrConfig:
    def test_valid(self):
        c = AsrConfig(enabled=True, model="test", max_duration_ms=30000, sample_rate=16000, tensor_parallel_size=1)
        assert c.device == "cuda"
        assert c.use_vllm is False

    def test_max_duration_zero(self):
        with pytest.raises(Exception):
            AsrConfig(enabled=True, model="test", max_duration_ms=0, sample_rate=16000, tensor_parallel_size=1)


class TestHydeConfig:
    def test_valid(self):
        c = HydeConfig(
            enabled=True, num_questions=3, max_questions_per_qa=5, max_rewrite_per_batch=10, answer_summary_max_len=100
        )
        assert c.conditional is True

    def test_num_questions_zero(self):
        with pytest.raises(Exception):
            HydeConfig(
                enabled=True,
                num_questions=0,
                max_questions_per_qa=5,
                max_rewrite_per_batch=10,
                answer_summary_max_len=100,
            )


class TestDedupConfig:
    def test_valid(self):
        c = DedupConfig(question_threshold=0.92, answer_threshold=0.85)
        assert c.question_threshold == 0.92

    def test_threshold_over_1(self):
        with pytest.raises(Exception):
            DedupConfig(question_threshold=1.5, answer_threshold=0.85)


class TestValidateConfig:
    def test_all_valid(self):
        cfg = {
            "server": {"port": 8000, "title": "test", "version": "1.0", "workers": 1},
            "cache": {"active_ids_ttl": 30, "config_ttl": 60},
            "mysql": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "123",
                "database": "test",
                "pool": {"max_usage": 100, "ping": 5},
            },
            "milvus": {"db_path": "./test.db", "collection_name": "qa"},
            "models": {
                "embed": {"name": "bge", "path": "/models/bge", "dim": 1024},
                "rerank": {"name": "bge-reranker", "path": "/models/reranker"},
                "query_prefix": "",
            },
            "llm": {
                "enabled": True,
                "provider": "openai",
                "api_key": "sk-xxx",
                "base_url": "https://api.example.com",
                "model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            "threshold": {
                "mode": "gap",
                "gap_high": 0.15,
                "gap_mid": 0.08,
                "gap_low": 0.03,
                "floor_high": 0.5,
                "floor_mid": 0.3,
                "floor_low": 0.15,
                "high": 0.7,
                "low": 0.3,
                "min": 0.1,
            },
            "ingest_confidence": {"auto": 0.8, "review": 0.5, "highlight": 0.3},
            "asr": {
                "enabled": True,
                "model": "test",
                "max_duration_ms": 30000,
                "sample_rate": 16000,
                "tensor_parallel_size": 1,
            },
            "hyde": {
                "enabled": True,
                "num_questions": 3,
                "max_questions_per_qa": 5,
                "max_rewrite_per_batch": 10,
                "answer_summary_max_len": 100,
            },
            "dedup": {"question_threshold": 0.92, "answer_threshold": 0.85},
            "data": {"qa_csv": "./data/qa.csv"},
        }
        errors = validate_config(cfg)
        assert errors == []

    def test_missing_section(self):
        errors = validate_config({})
        assert len(errors) == len(VALIDATORS)
        assert any("缺失" in e for e in errors)

    def test_invalid_section(self):
        cfg = {"server": {"port": 0, "title": "test", "version": "1.0"}}
        errors = validate_config(cfg)
        assert len(errors) > 0
        assert any("server" in e for e in errors)

    def test_partial_valid(self):
        cfg = {
            "server": {"port": 8000, "title": "test", "version": "1.0"},
            "cache": {"active_ids_ttl": 30, "config_ttl": 60},
        }
        errors = validate_config(cfg)
        missing_count = sum(1 for e in errors if "缺失" in e)
        assert missing_count == len(VALIDATORS) - 2
