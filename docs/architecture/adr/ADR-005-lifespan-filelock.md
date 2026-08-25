# ADR-005: FastAPI lifespan + FileLock 管理模型生命周期

**状态**：已接受  
**日期**：2026-07-20

## 背景

开发环境使用 uvicorn --reload（热重载），会启动主+子双进程。模型加载（Embedding/Reranker/ASR）和 Milvus 初始化需要在子进程执行，避免主进程浪费 GPU 显存和 Milvus 锁冲突。

## 决策

采用 **FastAPI lifespan + FileLock 进程锁**。

## 理由

1. **显存浪费**：主进程不加载模型，GPU 显存只占一份（8GB 限制）
2. **锁冲突**：FileLock 串行化 Milvus 初始化，防止 reload 重启时新旧子进程争抢 SQLite 文件锁
3. **热重载保留**：开发体验不受影响，改代码自动重载
4. **资源清理**：lifespan shutdown 自动关闭 Milvus 连接，无资源泄漏

## 实现

```python
# app.py
async def lifespan(app):
    # 子进程才执行
    lock = FileLock("etc_qa_milvus_init.lock", timeout=30)
    with lock:
        load_models()        # Embedding + Reranker + ASR
        init_milvus()        # Milvus 连接 + 集合加载
        start_scheduler()    # APScheduler
    yield
    # shutdown
    stop_scheduler()
    close_milvus()
```

## 代价

- workers=1（多 worker 会各自占一份显存，GPU 不够）
- reload 时有短暂初始化延迟（模型加载 5-10s，可接受）

## 参考

- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [filelock 库](https://py-filelock.readthedocs.io/)