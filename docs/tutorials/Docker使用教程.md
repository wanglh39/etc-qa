# Docker 浣跨敤鏁欑▼

## 涓€銆丏ocker 鏄粈涔堬紵

**涓€鍙ヨ瘽锛欴ocker = 鎶婁綘鐨勮繍琛岀幆澧冩墦鍖呮垚鐩掑瓙锛屽埆浜哄紑绠卞嵆鐢ㄣ€?*

### 娌℃湁 Docker 鐨勯棶棰?
```
浣犵殑鐢佃剳锛歅ython 3.10 + MySQL 8.0 + 渚濊禆鍏ㄨ濂?鈫?鑳借窇 鉁?闃熷弸鐢佃剳锛歅ython 3.12 + 娌¤MySQL + 渚濊禆鐗堟湰鍐茬獊 鈫?璺戜笉璧锋潵 鉂?```

### 鏈?Docker 涔嬪悗

```
浣犵殑鐢佃剳锛歞ocker compose up 鈫?鑳借窇 鉁?闃熷弸鐢佃剳锛歞ocker compose up 鈫?鑳借窇 鉁咃紙鐜涓€妯′竴鏍凤級
```

---

## 浜屻€佹牳蹇冩蹇碉紙3 涓瘝灏卞锛?
| 姒傚康 | 绫绘瘮 | 璇存槑 |
|------|------|------|
| **闀滃儚 (Image)** | 瀹夎鍏夌洏 | 鎵撳寘濂界殑鐜妯℃澘锛堝彧璇伙級 |
| **瀹瑰櫒 (Container)** | 杩愯涓殑绋嬪簭 | 浠庨暅鍍忓惎鍔ㄧ殑瀹炰緥锛堝彲璇诲啓锛?|
| **Compose** | 涓€閿惎鍔ㄨ剼鏈?| 缂栨帓澶氫釜瀹瑰櫒锛圡ySQL + 搴旂敤涓€璧峰惎鍔級 |

```
闀滃儚 鈹€鈹€docker run鈹€鈹€鈫?瀹瑰櫒锛堣繍琛屼腑锛?鍏夌洏 鈹€鈹€鏀惧叆鍏夐┍鈹€鈹€鈫? 杩愯涓殑绋嬪簭
```

---

## 涓夈€佸畨瑁?
### Windows
1. 涓嬭浇 Docker Desktop锛歨ttps://www.docker.com/products/docker-desktop/
2. 瀹夎鍚庨噸鍚數鑴?3. 鎵撳紑 Docker Desktop锛岀瓑寰呭惎鍔ㄥ畬鎴愶紙鎵樼洏鍥炬爣鍙樼豢锛?
### 楠岃瘉瀹夎
```bash
docker --version        # 鐪嬪埌 Docker version xx.x.x 灏卞浜?docker compose version  # 鐪嬪埌 Docker Compose version 灏卞浜?```

---

## 鍥涖€佹湰椤圭洰甯哥敤鍛戒护

### 4.1 鍚姩鎵€鏈夋湇鍔★紙MySQL + 搴旂敤锛?
```bash
# 寮€鍙戠幆澧?docker compose -f docker-compose.dev.yml up -d

# 鐢熶骇鐜
docker compose up -d
```

`-d` = 鍚庡彴杩愯锛堜笉鍗犵粓绔獥鍙ｏ級

### 4.2 鍙惎鍔?MySQL

```bash
docker compose -f docker-compose.dev.yml up -d mysql
```

### 4.3 鍚姩搴旂敤锛圡ySQL 宸插湪杩愯锛?
```bash
docker compose -f docker-compose.dev.yml up -d etc-qa
```

### 4.4 鏌ョ湅杩愯鐘舵€?
```bash
docker compose -f docker-compose.dev.yml ps
```

杈撳嚭绀轰緥锛?```
NAME         STATUS       PORTS
mysql        running      0.0.0.0:3306->3306/tcp
etc-qa       running      0.0.0.0:8000->8000/tcp
```

### 4.5 鏌ョ湅鏃ュ織

```bash
# 鏌ョ湅搴旂敤鏃ュ織
docker compose -f docker-compose.dev.yml logs etc-qa

# 瀹炴椂璺熻釜鏃ュ織锛圕trl+C 閫€鍑猴級
docker compose -f docker-compose.dev.yml logs -f etc-qa

# 鏌ョ湅鏈€杩?50 琛?docker compose -f docker-compose.dev.yml logs --tail 50 etc-qa
```

### 4.6 鍋滄鏈嶅姟

```bash
# 鍋滄鎵€鏈夊鍣?docker compose -f docker-compose.dev.yml down

# 鍋滄骞跺垹闄ゆ暟鎹紙鈿狅笍 浼氭竻绌篗ySQL鏁版嵁锛侊級
docker compose -f docker-compose.dev.yml down -v
```

### 4.7 閲嶅惎鏈嶅姟

```bash
docker compose -f docker-compose.dev.yml restart etc-qa
```

### 4.8 閲嶆柊鏋勫缓闀滃儚锛堟敼浜嗕唬鐮佹垨渚濊禆鍚庯級

```bash
docker compose -f docker-compose.dev.yml build etc-qa
docker compose -f docker-compose.dev.yml up -d etc-qa
```

---

## 浜斻€丏ocker Desktop 鍥惧舰鐣岄潰

### 5.1 鎵撳紑鏂瑰紡

鍙屽嚮妗岄潰鍥炬爣鎴栨墭鐩樺浘鏍?鈫?鎵撳紑 Docker Desktop

### 5.2 鐣岄潰璇存槑

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹? 宸︿晶鏍忥細                                      鈹?鈹?   Containers  鈫?鏌ョ湅杩愯涓殑瀹瑰櫒锛堝搴?docker ps锛?鈹?鈹?   Images      鈫?鏌ョ湅闀滃儚鍒楄〃                    鈹?鈹?   Volumes     鈫?鏌ョ湅鏁版嵁鍗?                     鈹?鈹?                                               鈹?鈹? 涓诲尯鍩燂細                                        鈹?鈹?   瀹瑰櫒鍒楄〃 鈫?姣忎釜瀹瑰櫒鏈?鍚姩/鍋滄/閲嶅惎/鍒犻櫎 鎸夐挳    鈹?鈹?   鐐瑰嚮瀹瑰櫒鍚?鈫?鏌ョ湅鏃ュ織锛堝搴?docker logs锛?       鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

### 5.3 甯哥敤鎿嶄綔

| 鎿嶄綔 | 鍥惧舰鐣岄潰 | 绛変环鍛戒护 |
|------|---------|---------|
| 鍚姩瀹瑰櫒 | Containers 鈫?鐐瑰鍣?鈫?Start | `docker start 瀹瑰櫒鍚峘 |
| 鍋滄瀹瑰櫒 | Containers 鈫?鐐瑰鍣?鈫?Stop | `docker stop 瀹瑰櫒鍚峘 |
| 鏌ョ湅鏃ュ織 | 鐐瑰鍣ㄥ悕 鈫?Logs 鏍囩 | `docker logs 瀹瑰櫒鍚峘 |
| 鍒犻櫎瀹瑰櫒 | 鐐瑰鍣?鈫?Delete | `docker rm 瀹瑰櫒鍚峘 |
| 杩涘叆瀹瑰櫒缁堢 | 鐐瑰鍣?鈫?Exec 鏍囩 | `docker exec -it 瀹瑰櫒鍚?sh` |

---

## 鍏€佹湰椤圭洰鐨?Docker 鏋舵瀯

```
docker-compose.dev.yml 鍚姩鍚庯細

鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹? Docker 缃戠粶                              鈹?鈹?                                         鈹?鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?鈹? 鈹? MySQL    鈹?     鈹? etc-qa 搴旂敤      鈹? 鈹?鈹? 鈹? 绔彛3306 鈹?鈫愨攢鈹€鈫?鈹? 绔彛8000        鈹? 鈹?鈹? 鈹? 鏁版嵁鎸佷箙鍖栤攤      鈹? 鎸傝浇models/     鈹? 鈹?鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹? 鎸傝浇data/       鈹? 鈹?鈹?                    鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?        鈫?                     鈫?   鏈湴:3306              鏈湴:8000
   (Navicat绛夎繛鎺?        (娴忚鍣ㄨ闂瓵PI)
```

### 浠€涔堝湪 Docker 閲岋紝浠€涔堜笉鍦紵

| 椤圭洰 | 鍦ㄥ摢 | 鍘熷洜 |
|------|------|------|
| MySQL | Docker 瀹瑰櫒 | 闃熷弸涓嶇敤鑷繁瑁?|
| Python + 渚濊禆 | Docker 闀滃儚 | 鐜涓€鑷存€?|
| Milvus 鏁版嵁 | Docker Volume | 鑷姩绠＄悊 |
| 妯″瀷鏂囦欢 | 鏈湴 `models/` 鐩綍 | 澶ぇ锛垀10G锛夛紝鎸傝浇杩涘鍣?|
| API Key | 鏈湴 `.env` 鏂囦欢 | 涓嶈兘杩涢暅鍍忥紝闃叉硠闇?|
| 婧愪唬鐮?| 鏈湴鐩綍 | 寮€鍙戞椂鏀逛唬鐮侊紝瀹瑰櫒閲屽疄鏃剁敓鏁堬紙--reload锛?|

---

## 涓冦€佸父瑙侀棶棰?
### Q: Docker Desktop 鍚姩寰堟參锛?姝ｅ父鐜拌薄锛岄娆″惎鍔ㄩ渶瑕?30-60 绉掋€傜瓑鎵樼洏鍥炬爣鍙樼豢鍗冲彲銆?
### Q: 绔彛琚崰鐢紵
```
Error: Bind for 0.0.0.0:3306 failed: port is already allocated
```
璇存槑浣犳湰鍦板凡缁忚浜?MySQL 鍗犱簡 3306 绔彛銆備袱绉嶈В鍐虫柟寮忥細
1. 鍏虫帀鏈湴 MySQL 鏈嶅姟
2. 鏀?`docker-compose.dev.yml` 涓殑绔彛锛歚"3307:3306"`锛堝閮ㄧ敤 3307 杩烇級

### Q: 瀹瑰櫒鍚姩鍚庣珛鍒婚€€鍑猴紵
鏌ョ湅鏃ュ織鎵惧師鍥狅細
```bash
docker compose -f docker-compose.dev.yml logs etc-qa
```

### Q: 鏀逛簡浠ｇ爜浣嗕笉鐢熸晥锛?寮€鍙戠幆澧冪敤浜?`--reload`锛屼唬鐮佹敼鍔ㄤ細鑷姩鐢熸晥銆傚鏋滄病鐢熸晥锛?```bash
docker compose -f docker-compose.dev.yml restart etc-qa
```

### Q: 鏀逛簡 requirements.txt 涓嶇敓鏁堬紵
闇€瑕侀噸鏂版瀯寤洪暅鍍忥細
```bash
docker compose -f docker-compose.dev.yml build etc-qa
docker compose -f docker-compose.dev.yml up -d etc-qa
```

### Q: 鎯冲畬鍏ㄩ噸缃幆澧冿紵
```bash
docker compose -f docker-compose.dev.yml down -v   # 鍒犻櫎瀹瑰櫒+鏁版嵁鍗?docker compose -f docker-compose.dev.yml up -d       # 閲嶆柊鍚姩
```
鈿狅笍 `-v` 浼氬垹闄?MySQL 鏁版嵁锛岄渶瑕侀噸鏂拌繍琛?`init_db.py`

### Q: 瀹瑰櫒閲屾€庝箞鎵ц鍛戒护锛?```bash
# 杩涘叆搴旂敤瀹瑰櫒鐨勭粓绔?docker compose -f docker-compose.dev.yml exec etc-qa sh

# 鐩存帴鎵ц鍗曟潯鍛戒护
docker compose -f docker-compose.dev.yml exec etc-qa python scripts/data/init_db.py dev
```

### Q: Windows 涓?Docker 寰堝崱锛?Docker Desktop 鈫?Settings 鈫?Resources锛?- Memory: 寤鸿 4GB+
- CPUs: 寤鸿 2+
- Disk: 寤鸿 20GB+
