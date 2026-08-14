# ETC瀹㈡湇QA鏅鸿兘妫€绱㈢郴缁?
鍩轰簬 Milvus 鍚戦噺鏁版嵁搴?+ MySQL + LangGraph Agent 鐨?ETC 瀹㈡湇 QA 鏅鸿兘妫€绱㈢郴缁熴€傚鏈嶈緭鍏ラ棶棰樺悗锛岄€氳繃鍚戦噺妫€绱?+ BM25 + Reranker 鎵惧埌鏈€鍖归厤鐨勭瓟妗堣瘽鏈紝鏂伴棶棰橀€氳繃 Agent 娴佹按绾挎爣鍑嗗寲鍚庡叆搴撱€?
## 鎶€鏈爤

| 灞傜骇 | 鎶€鏈?| 鐗堟湰/璇存槑 |
|------|------|----------|
| 鍚庣 | FastAPI + Uvicorn | Python 3.10 |
| 鍚戦噺鏁版嵁搴?| Milvus Lite | 鏈湴鏂囦欢锛屾棤闇€鐙珛閮ㄧ讲 |
| 鍏崇郴鏁版嵁搴?| MySQL 8.x | Docker 瀹瑰櫒 |
| Embedding | bge-large-zh-v1.5 | 1024 缁?|
| Reranker | bge-reranker-large | CrossEncoder |
| LLM | DeepSeek API | 瑙勬暣/鍒嗙被/HyDE |
| Agent | LangGraph | 鐘舵€佸浘缂栨帓 |
| BM25 | jieba + rank_bm25 | 鍏抽敭璇嶅彫鍥?|
| ASR | FunASR | 璇煶璇嗗埆 |
| 杩借釜 | LangSmith | 鍏ㄩ摼璺拷韪?|

## 鐜瑕佹眰

- Python 3.10+
- Docker Desktop锛堢敤浜庡惎鍔?MySQL锛?- DeepSeek API Key锛堝幓 https://platform.deepseek.com 娉ㄥ唽鑾峰彇锛?
## 蹇€熷紑濮?
### 鏂瑰紡涓€锛氫竴閿惌寤猴紙鎺ㄨ崘锛?
Windows:
```bash
setup.bat
```

Linux/Mac:
```bash
chmod +x setup.sh
./setup.sh
```

鑴氭湰浼氳嚜鍔ㄥ畬鎴愶細瀹夎渚濊禆 -> 涓嬭浇妯″瀷 -> 鍚姩MySQL -> 鍒濆鍖栨暟鎹簱

### 鏂瑰紡浜岋細鎵嬪姩鎼缓

1. 瀹夎渚濊禆
```bash
pip install -r requirements.txt
```

2. 閰嶇疆鐜鍙橀噺
```bash
cp .env.template .env
# 缂栬緫 .env锛屽～鍏?DeepSeek API Key
```

3. 涓嬭浇妯″瀷锛堢害5.6GB锛?```bash
pip install modelscope
python scripts/setup/download_models.py
```

| 妯″瀷 | 鐢ㄩ€?| 澶у皬 |
|------|------|------|
| bge-large-zh-v1.5 | Embedding鍚戦噺鍖?| ~1.3GB |
| bge-reranker-large | Reranker绮炬帓 | ~2.2GB |
| Fun-ASR-Nano-2512 | 璇煶璇嗗埆 | ~2.1GB |

4. 鍚姩 MySQL + 鍒濆鍖栨暟鎹簱
```bash
docker compose -f docker-compose.dev.yml up -d mysql
python scripts/data/init_db.py dev
```

5. 鍚姩鏈嶅姟
```bash
python main.py
```

璁块棶 API 鏂囨。: http://localhost:8000/docs

## Docker 鍚姩

```bash
# 寮€鍙戠幆澧冿紙鐑洿鏂帮級
docker compose -f docker-compose.dev.yml up -d

# 鐢熶骇鐜
docker compose up -d
```

## 娴嬭瘯

```bash
# 鍗曞厓娴嬭瘯锛?64 passed, 96%瑕嗙洊鐜囷級
python -m pytest tests/ -q --ignore=tests/integration

# 闆嗘垚娴嬭瘯锛?42 passed, 84%瑕嗙洊鐜囷級
python -m pytest tests/integration/ -m integration -v
```

## 鐜璇存槑

閫氳繃鐜鍙橀噺 ETC_QA_ENV 鍒囨崲锛?
| 鐜 | 鐢ㄩ€?| MySQL 搴?| 鍚姩鏂瑰紡 |
|------|------|----------|---------|
| dev | 鏃ュ父寮€鍙?| etc_qa | python main.py |
| test | 娴嬭瘯 | etc_qa_test | ETC_QA_ENV=test python main.py |
| prod | 鐢熶骇 | etc_qa | docker compose up -d |

## 椤圭洰缁撴瀯

```
etc_qa/
鈹溾攢鈹€ agent/           # LangGraph Agent锛堥棶棰樿鏁?鍒嗙被/HyDE/鍏ュ簱鏀瑰啓锛?鈹溾攢鈹€ api/             # FastAPI 璺敱
鈹溾攢鈹€ asr/             # 璇煶璇嗗埆
鈹溾攢鈹€ config/          # 閰嶇疆鏂囦欢锛圷AML + Pydantic鏍￠獙锛?鈹溾攢鈹€ db/              # MySQL + Milvus 瀹㈡埛绔?鈹溾攢鈹€ models/          # 鏈湴妯″瀷鏂囦欢锛堜笉鍏it锛屼笉鍏ocker闀滃儚锛?鈹溾攢鈹€ rag/             # 鍙洖 + Reranker + 闃堝€煎垽瀹?鈹溾攢鈹€ prompt/          # 鎻愮ず璇嶇増鏈鐞?+ 褰卞瓙娴嬭瘯
鈹溾攢鈹€ scripts/         # 鏁版嵁鍒濆鍖?璇勪及/缁存姢鑴氭湰
鈹溾攢鈹€ tests/           # 鍗曞厓娴嬭瘯 + 闆嗘垚娴嬭瘯
鈹溾攢鈹€ docs/            # 鏂囨。
鈹溾攢鈹€ docker-compose.dev.yml  # 寮€鍙戠幆澧?鈹溾攢鈹€ docker-compose.yml      # 鐢熶骇鐜
鈹溾攢鈹€ setup.bat / setup.sh    # 涓€閿惌寤鸿剼鏈?鈹斺攢鈹€ .env.template           # 鐜鍙橀噺妯℃澘
```

## 鏂囨。

| 鏂囨。 | 璇存槑 |
|------|------|
| [寮€鍙戠幆澧冩惌寤?md](docs/寮€鍙戠幆澧冩惌寤?md) | 闃熷弸涓婃墜鎸囧崡 |
| [Git浣跨敤鏁欑▼.md](docs/Git浣跨敤鏁欑▼.md) | Git 鍥惧舰鐣岄潰 + 鍛戒护琛?|
| [Docker浣跨敤鏁欑▼.md](docs/Docker浣跨敤鏁欑▼.md) | Docker 浣跨敤鎸囧崡 |
| [鏋舵瀯鍥?md](docs/鏋舵瀯鍥?md) | 绯荤粺鏋舵瀯銆佹牳蹇冮摼璺?|
| [鐩綍缁撴瀯.md](docs/鐩綍缁撴瀯.md) | 鐩綍缁撴瀯 + 浠ｇ爜璋冪敤鍏崇郴 |
| [API鎺ュ彛鏂囨。.md](docs/API鎺ュ彛鏂囨。.md) | REST API 璇存槑 |
| [鏁版嵁搴撹璁℃枃妗?md](docs/鏁版嵁搴撹璁℃枃妗?md) | 琛ㄧ粨鏋?+ 瀛楁璇存槑 |
| [寮€鍙戣鑼?md](docs/寮€鍙戣鑼?md) | 浠ｇ爜瑙勮寖銆佹彁浜よ鑼?|
| [浜ゆ帴娓呭崟.md](docs/浜ゆ帴娓呭崟.md) | 宸插畬鎴?寰呭紑鍙?娉ㄦ剰浜嬮」 |