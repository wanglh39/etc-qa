# AGENTS.md 鈥?椤圭洰瑙勫垯涓庤蹇?
## 鍩烘湰瑙勫垯

### 浠ｇ爜淇敼瑙勫垯
1. **鏀逛唬鐮佸墠鍏堥棶鐢ㄦ埛**锛屼笉瑕佽嚜浣滀富寮?2. **浠ｇ爜鏂囦欢鍙啓浠ｇ爜锛屼笉瑕佸姞娉ㄩ噴**锛堥櫎闈炵敤鎴锋槑纭姹傦級
3. **蹇呴』浣跨敤绠€浣撲腑鏂囧洖澶?*
4. **鏀逛唬鐮佸墠蹇呴』鍋氬奖鍝嶈寖鍥磋瘎浼?*锛屽叿浣撳寘鎷細
   - **鍙楀奖鍝嶇殑妯″潡**锛氬摢浜涙枃浠?绫?鍑芥暟浼氳娉㈠強
   - **鍗曞厓娴嬭瘯**锛氬摢浜涙祴璇曠被/鏂规硶闇€瑕佹柊澧炴垨鏇存柊
   - **闆嗘垚娴嬭瘯**锛氬摢浜涢泦鎴愭祴璇曞彲鑳藉彈褰卞搷
   - **娴嬭瘎**锛氭敼鍔ㄦ秹鍙婂摢涓祴璇勮剼鏈紙eval_asr/eval_rag/eval_structure_ingest/eval_prompt_diff锛夛紝缁欏嚭鏈湴杩愯鍛戒护
   - **鏃ュ織**锛氭敼鍔ㄥ鏄惁闇€瑕佸姞logger.info/warning/error
   - **LangSmith**锛氭敼鍔ㄥ鏄惁闇€瑕佸姞@traceable瑁呴グ鍣?   - 璇勪及缁撴灉浠ヨ〃鏍煎舰寮忓憟鐜扮粰鐢ㄦ埛锛岀‘璁ゅ悗鍐嶆敼
5. **姣忔鏀瑰姩蹇呴』鍚屾琛ュ叏鍙娴嬫€?*锛屽叿浣撳寘鎷細
   - **鏃ュ織**锛氬叧閿祦绋嬪叆鍙?鍑哄彛/寮傚父澶勫姞 `logger.info/warning/error`锛屾棩蹇楀唴瀹硅鑳藉畾浣嶉棶棰橈紙鍚叧閿彉閲忓€硷級
   - **LangSmith**锛氭柊澧炵殑Service灞傛柟娉曟垨鍏抽敭涓氬姟鍑芥暟鍔?`@traceable(name="xxx")`锛宯ame鐢ㄦā鍧梍鏂规硶鍛藉悕锛堝 `rag_query`銆乣asr_transcribe`锛?   - 杩欎袱姝ュ拰鍐欎唬鐮佸悓姝ヨ繘琛岋紝涓嶆槸浜嬪悗琛?6. **姣忔鏀瑰姩蹇呴』鍚屾鏇存柊鏍稿績鏂囨。**锛屽叿浣撳寘鎷細
   - `docs/鐩綍缁撴瀯.md`锛氶」鐩洰褰曠粨鏋?   - `docs/鏋舵瀯鍥?md`锛氭鏋?鏋舵瀯鍥?   - `docs/鎸戞垬鏉妧鏈枃绋?md`锛氭妧鏈枃妗?   - 杩欎笁涓枃妗ｅ拰鍐欎唬鐮佸悓姝ユ敼锛屾敼瀹屼富鍔ㄥ憡鐭ョ敤鎴锋敼浜嗗摢浜?   - 鐒跺悗璇㈤棶鐢ㄦ埛鏄惁闇€瑕佹洿鏂板叾浣欐枃妗ｏ紙API鎺ュ彛鏂囨。銆佹暟鎹簱璁捐鏂囨。銆佸紑鍙戣鑼冦€佹暟鎹鑼冦€佷氦鎺ユ竻鍗曘€侀珮骞跺彂婕旇繘璺嚎銆丄I浜や簰鑴氭湰銆丷EADME绛夛級
7. **姣忔鏀瑰姩瀹屾垚鍚庡繀椤昏闂敤鎴锋槸鍚﹂渶瑕乬it鎻愪氦**锛屼笉瑕佽嚜鍔ㄦ彁浜?
### 娴嬭瘯瑙勫垯锛堝己鍒讹級
1. **姣忔鏀逛唬鐮佸悗蹇呴』璺戝崟鍏冩祴璇?*锛屼笉鑳借烦杩?2. **鍗曞厓娴嬭瘯涓嶅姞杞界湡瀹炴ā鍨?*锛坒unasr.AutoModel/SentenceTransformer/MilvusClient绛夛級锛岀敤mock鏇夸唬銆備絾鍏佽import搴撴湰韬紙濡倀orch锛夌敤浜巔atch
3. **鍗曞厓娴嬭瘯淇濇寔闀滃儚娴嬭瘯缁撴瀯**锛氭祴璇曠被瀵瑰簲婧愮爜绫伙紝娴嬭瘯鏂规硶瀵瑰簲婧愮爜鏂规硶
4. **鍗曞厓娴嬭瘯閫氳繃鍚庯紝璇㈤棶鐢ㄦ埛鏄惁闇€瑕佽窇闆嗘垚娴嬭瘯**
5. **闆嗘垚娴嬭瘯閫氳繃鍚庯紙鎴栫敤鎴疯烦杩囬泦鎴愭祴璇曞悗锛夛紝璇㈤棶鐢ㄦ埛鏄惁闇€瑕佽窇娴嬭瘎**锛屽苟缁欏嚭瀵瑰簲鐨勬祴璇勮剼鏈矾寰勫拰鏈湴杩愯鍛戒护
6. sandbox娴嬭瘯鍛戒护锛歚python -m pytest tests/ -x -q -o addopts="" --ignore=tests/integration`锛坄-o addopts=""`鍘绘帀coverage閬垮厤鍔犺浇鎵€鏈夋ā鍧楋級
7. 鏈湴娴嬭瘯鍛戒护锛歚C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe -m pytest tests/ -x -q`
8. sandbox鏈?20绉掕秴鏃讹紝heavy渚濊禆锛坒unasr/sentence_transformers/pymilvus锛夌殑娴嬭瘯鍙兘鍦ㄦ湰鍦扮粓绔窇
9. conftest.py宸瞞ock langsmith/langchain_core/langgraph锛坣oop traceable瑁呴グ鍣級锛岄伩鍏?绉掑鍏ュ紑閿€

### 娴嬭瘎瑙勫垯锛堝己鍒讹級
1. **娴嬭瘎鍦ㄥ崟鍏冩祴璇?闆嗘垚娴嬭瘯涔嬪悗杩涜**锛氬崟鍏冩祴璇曢€氳繃鈫掕闂泦鎴愭祴璇曗啋闆嗘垚娴嬭瘯閫氳繃鎴栬烦杩囧悗鈫掕闂祴璇?2. **姣忔鏀瑰姩蹇呴』缁欏嚭娴嬭瘎鍛戒护**锛岃鐢ㄦ埛鍙互鐩存帴澶嶅埗鍒版湰鍦扮粓绔繍琛?3. 娴嬭瘎鑴氭湰鐩綍锛歚scripts/eval/`锛屽彲鐢ㄨ剼鏈細
   - `eval_asr.py`锛欰SR璇嗗埆鍑嗙‘鐜?妫€绱㈠懡涓巼璇勬祴锛堟敼asr/鐩稿叧浠ｇ爜鏃剁敤锛?   - `eval_rag.py`锛歊AG妫€绱㈠彫鍥炵巼+鍑嗙‘鐜囪瘎娴嬶紙鏀箁ag/鐩稿叧浠ｇ爜鏃剁敤锛?   - `eval_structure_ingest.py`锛氬叆搴撶粨鏋勫寲璐ㄩ噺璇勬祴锛堟敼structure_ingest鐩稿叧浠ｇ爜鏃剁敤锛?   - `eval_prompt_diff.py`锛氭彁绀鸿瘝鐗堟湰before/after瀵规瘮璇勬祴锛堟敼prompt/templates/*.j2鏃剁敤锛?   - `eval_rag_perf.py`锛歊AG妫€绱㈡€ц兘鍩哄噯娴嬭瘯锛?姝ュ垎姝ヨ鏃?p50/p95/p99鍒嗕綅缁熻锛堟帓鏌ユ绱㈡參鏃剁敤锛?4. 娴嬭瘎杩愯鍛戒护鏍煎紡锛歚C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe scripts/eval/eval_xxx.py`
5. 娴嬭瘎鑴氭湰闇€鏈湴杩愯锛堝姞杞界湡瀹炴ā鍨?DB+Milvus锛夛紝sandbox瓒呮椂璺戜笉浜?
## 椤圭洰淇℃伅

- **椤圭洰鏍圭洰褰?*: `C:\Users\wlh19\Desktop\鎸戞垬鏉痋etc_qa\`
- **Python鐜**: conda鐜`etc_qa`锛圥ython 3.10锛夛紝瑙ｉ噴鍣ㄨ矾寰刞C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe`
- **鎶€鏈爤**: MySQL + Milvus LITE + FastAPI + Vue3 + LangGraph + LangSmith
- **鐢ㄦ埛鏄皬鐧?*锛氬彧鎳傜帺鍏风骇React锛堝墠绔敼鐢╒ue3锛夛紝涓嶆噦Docker/Milvus/FastAPI/Reranker

## 鍏抽敭鏋舵瀯鍐崇瓥

### ASR
- 浼祦寮忔ā寮忥紙PseudoStreamingBackend锛夛細VAD鍒囧彞 鈫?Fun-ASR-Nano绂荤嚎璇嗗埆 鈫?鍥炶皟on_final
- **鍚姩棰勭儹+澶嶇敤**锛氭湇鍔″惎鍔ㄦ椂warmup棰勫姞杞芥ā鍨嬶紙閬垮厤棣栭€氬欢杩?0-30绉掞級锛宻tart_stream澶嶇敤backend锛宻top_stream涓嶉攢姣侊紱棰勭儹澶辫触閫€鍖栦负鎳掑姞杞藉厹搴?- 鍙屽０閬撳満鏅笉闇€瑕乨iarizer锛堢墿鐞嗗０閬撳垎绂伙級锛屽崟澹伴亾娣烽煶鎵嶉渶瑕乸yannote
- 娴佸紡璺緞锛圵ebSocket+浼祦寮忥級蹇呴』搴旂敤绾犻敊琛紙_apply_corrections锛?
### RAG
- 鍙岃矾骞惰鍙洖锛歍hreadPoolExecutor(max_workers=2)骞惰璺慚ilvus鍚戦噺+BM25鍏抽敭璇?- RRF鍚堝苟锛坵eighted_rrf: vector_weight=0.7, bm25_weight=0.3锛?- Reranker绮炬帓锛圕rossEncoder锛?- Milvus瀹氭湡閲嶈繛锛堟瘡30娆℃煡璇富鍔╛reconnect锛岄伩鍏峠RPC too_many_pings锛?
### 鐘舵€佹満
- SessionState鏋氫妇锛欼DLE 鈫?LISTENING 鈫?QUERY_READY 鈫?CANDIDATES_SHOWN 鈫?RESOLVED
- WebSocket閲宊set_state鍑芥暟绠＄悊鐘舵€佽浆鎹?閫氱煡鍓嶇
- 鎺у埗娑堟伅锛歴elect_answer锛堚啋RESOLVED锛夈€乺eset锛堚啋IDLE锛?
### 鍙娴嬫€?- 鏃ュ織锛歴tdout + `logs/etc_qa.log`锛?0MB杞浆锛?涓浠斤級
- LangSmith @traceable锛歛sr_transcribe銆乺ag_query銆乺ecall銆乿ector_recall銆乥m25_recall銆乺erank

### 鎻愮ず璇嶇鐞?- 妯℃澘鏂囦欢浼樺厛锛歅romptEngine鍔犺浇浼樺厛绾?.j2鏂囦欢 > DB鐑慨 > 浠ｇ爜fallback
- prompt/templates/*.j2锛?涓ā鏉匡紙judge/hyde_judge/hyde/structure_ingest锛夛紝git绠＄悊鐗堟湰
- .j2鏂囦欢鍚珄# metadata #}澶存敞閲婏紙prompt_key/description/variables锛夛紝Jinja2娓叉煋鏃惰嚜鍔ㄥ墺绂?- 璋冭瘯杈圭晫锛氭敼鎸囦护鏂囧瓧锛堣鑹?瑙勫垯/鏍煎紡锛夛紝涓嶅垹{{鍙橀噺}}鍗犱綅绗︼紙浠ｇ爜杩愯鏃跺～鍏咃級
- version_manager.py浠嶄负DB-based锛圥hase 2鍙敼git-based锛夛紝API璺敱涓嶅彉

## 宸插畬鎴愮殑閲嶈鏀瑰姩

1. corrections鍔?E T C"鈫?ETC"绛夊瓧姣嶇┖鏍肩籂閿欙紙config/asr.yaml锛?2. greeting姝ｅ垯鍔?涓轰綘濂?"涓轰綘"锛坅sr/ws_helpers.py锛?3. 娴佸紡璺緞鍔犵籂閿欒〃搴旂敤锛坅sr/websocket.py + scripts/eval/eval_asr.py锛?4. RAG find_expected_id鍔犳ā绯婂尮閰?+ test_questions.json鍔爀xpected_qa_id鎵嬪姩鏄犲皠
5. VAD鎹㈡垚numpy鑳介噺VAD + min_silence_ms=200锛坰cripts/eval/eval_asr.py锛?6. 鍙岃矾鍙洖骞惰锛坮ag/recall.py锛?7. ASR妯″瀷澶嶇敤锛屼笉姣忔閲嶆柊鍔犺浇锛坅sr/streaming.py锛?8. 鐘舵€佹満锛坅sr/ws_state.py + asr/websocket.py锛?9. Milvus瀹氭湡閲嶈繛闃瞭oo_many_pings锛坉b/milvus_client.py锛?10. 鏃ュ織鏂囦欢+杞浆锛坲tils/logger.py锛?11. LangSmith @traceable鍔犲埌QAService.query鍜孉SRService.transcribe
12. ASR妯″瀷鍚姩棰勭儹锛坅sr/streaming.py warmup + app.py create_service璋冪敤锛夛紝閬垮厤棣栭€氱敤鎴风瓑妯″瀷鍔犺浇10-30绉?13. tests/asr/闀滃儚鏁寸悊锛氭媶鍒唗est_ws_helpers.py+test_ws_state.py锛屽悎骞秚est_websocket_endpoint.py鍒皌est_websocket.py
14. 鎻愮ず璇嶆枃浠跺寲绠＄悊锛圥hase 1锛夛細鎻愬彇4涓?j2妯℃澘鍒皃rompt/templates/锛孭romptEngine浼樺厛璇绘枃浠?DB>浠ｇ爜fallback锛実it绠＄悊鐗堟湰
15. RAG妫€绱㈡€ц兘浼樺寲锛歀LM鍔爐imeout=10s+max_retries=1+max_tokens鍑忚嚦256锛宊standardize鍔?00鏉RU缂撳瓨+瓒呮椂闄嶇骇鐢ㄥ師闂妫€绱?
## 娴嬭瘯瑕嗙洊

- tests/asr/test_ws_helpers.py: TestIsGreeting/TestIsCorrection/TestHasPronoun/TestCharOverlapRatio/TestGetRecentAudio/TestExtractChannel/TestDoQuery/TestIdentifySpeaker/TestDoDiarizeSegment
- tests/asr/test_ws_state.py: TestQueryAccumulator/TestQueryCache/TestContextWindow/TestVADSilenceDetector/TestVADFeedAudio/TestAccumulatorCheckTimeout/TestSessionState
- tests/asr/test_websocket.py: WebSocket绔偣娴嬭瘯(asr_stream绔埌绔?+TestStateMachine/TestControlMessageUpdate/TestOnFinalCorrections/TestFilterPipeline
- tests/asr/test_streaming.py: test_start_stream_reuses_backend, test_stop_stream_preserves_backend, TestStreamingASRServiceWarmup
- tests/asr/test_service.py: test_apply_corrections_etc_spaces绛?- tests/rag/test_recall.py: test_parallel_recall绛?- tests/agent/test_prompt_engine.py: TestPromptEngineRender/TestPromptEngineShadowAndEdgeCases/TestPromptEngineFileTemplate锛堟枃浠惰鍙?DB闄嶇骇+fallback鍏滃簳锛?- tests/asr/涓巃sr/闀滃儚缁撴瀯涓€涓€瀵瑰簲

## 寰呭畬鎴?
- 鍓嶇Vue3寮€鍙?- 绛旇京鏉愭枡鏁寸悊
- eval_asr.py鏈湴閲嶈窇楠岃瘉鍏ㄩ儴淇鏁堟灉
- 闆嗘垚娴嬭瘯鏇存柊锛堝闇€瑕侊級