# Docker 使用教程

## 一、Docker 是什么？

**一句话：Docker = 把你的运行环境打包成盒子，别人开箱即用。**

### 没有 Docker 的问题

```
你的电脑：Python 3.10 + MySQL 8.0 + 依赖全装好 → 能跑
队友电脑：Python 3.12 + 没装MySQL + 依赖版本冲突 → 跑不起来
```

### 有 Docker 之后

```
你的电脑：docker compose up → 能跑
队友电脑：docker compose up → 能跑（环境一模一样）
```

---

## 二、核心概念（3 个词就够）

| 概念 | 类比 | 说明 |
|------|------|------|
| **镜像 (Image)** | 安装光盘 | 打包好的环境模板（只读） |
| **容器 (Container)** | 运行中的程序 | 从镜像启动的实例（可读写） |
| **Compose** | 一键启动脚本 | 编排多个容器（MySQL + 应用一起启动） |

```
镜像 ──docker run──→ 容器（运行中）
光盘 ──放入光驱──→ 运行中的程序
```

---

## 三、安装

### Windows
1. 下载 Docker Desktop：https://www.docker.com/products/docker-desktop/
2. 安装后重启电脑
3. 打开 Docker Desktop，等待启动完成（托盘图标变绿）

### 验证安装
```bash
docker --version        # 看到 Docker version xx.x.x 就对了
docker compose version  # 看到 Docker Compose version 就对了
```

---

## 四、本项目常用命令

### 4.1 启动所有服务（MySQL + 应用）
```bash
# 开发环境
docker compose -f docker-compose.dev.yml up -d

# 生产环境
docker compose up -d
```

`-d` = 后台运行（不占终端窗口）

### 4.2 只启动 MySQL

```bash
docker compose -f docker-compose.dev.yml up -d mysql
```

### 4.3 启动应用（MySQL 已在运行）
```bash
docker compose -f docker-compose.dev.yml up -d etc-qa
```

### 4.4 查看运行状态
```bash
docker compose -f docker-compose.dev.yml ps
```

输出示例：
```
NAME         STATUS       PORTS
mysql        running      0.0.0.0:3306->3306/tcp
etc-qa       running      0.0.0.0:8000->8000/tcp
```

### 4.5 查看日志

```bash
# 查看应用日志
docker compose -f docker-compose.dev.yml logs etc-qa

# 实时跟踪日志（Ctrl+C 退出）
docker compose -f docker-compose.dev.yml logs -f etc-qa

# 查看最后 50 行
docker compose -f docker-compose.dev.yml logs --tail 50 etc-qa
```

### 4.6 停止服务

```bash
# 停止所有容器
docker compose -f docker-compose.dev.yml down

# 停止并删除数据（⚠️ 会清空MySQL数据！）
docker compose -f docker-compose.dev.yml down -v
```

### 4.7 重启服务

```bash
docker compose -f docker-compose.dev.yml restart etc-qa
```

### 4.8 重新构建镜像（改了代码或依赖后）

```bash
docker compose -f docker-compose.dev.yml build etc-qa
docker compose -f docker-compose.dev.yml up -d etc-qa
```

---

## 五、Docker Desktop 图形界面

### 5.1 打开方式

双击桌面图标或托盘图标 → 打开 Docker Desktop

### 5.2 界面说明

```
┌──────────────────────────────────────────────┐
│ 左侧栏：                                      │
│   Containers  → 查看运行中的容器（对应 docker ps）│
│   Images      → 查看镜像列表                    │
│   Volumes     → 查看数据卷                      │
│                                               │
│ 主区域：                                        │
│   容器列表 → 每个容器有 启动/停止/重启/删除 按钮   │
│   点击容器名 → 查看日志（对应 docker logs）       │
└──────────────────────────────────────────────┘
```

### 5.3 常用操作

| 操作 | 图形界面 | 等价命令 |
|------|---------|---------|
| 启动容器 | Containers → 点容器 → Start | `docker start 容器名` |
| 停止容器 | Containers → 点容器 → Stop | `docker stop 容器名` |
| 查看日志 | 点容器名 → Logs 标签 | `docker logs 容器名` |
| 删除容器 | 点容器 → Delete | `docker rm 容器名` |
| 进入容器终端 | 点容器 → Exec 标签 | `docker exec -it 容器名 sh` |

---

## 六、本项目的 Docker 架构

```
docker-compose.dev.yml 启动后：

┌─────────────────────────────────────────┐
│ Docker 网络                              │
│                                         │
│ ┌──────────┐     ┌──────────────────┐   │
│ │ MySQL    │     │ etc-qa 应用      │   │
│ │ 端口3306 │←──→ │ 端口8000        │   │
│ │ 数据持久化│      │ 挂载models/     │   │
│ └──────────┘     │ 挂载data/       │   │
│                   └──────────────────┘   │
└─────────────────────────────────────────┘
        ↓                     ↓
   本地:3306              本地:8000
   (Navicat等连接)        (浏览器访问API)
```

### 什么在 Docker 里，什么不在？

| 项目 | 在哪 | 原因 |
|------|------|------|
| MySQL | Docker 容器 | 队友不用自己装 |
| Python + 依赖 | Docker 镜像 | 环境一致 |
| Milvus 数据 | Docker Volume | 自动管理 |
| ASR模型文件 | 本地 `models/` 目录 | 太大（~2.1G），挂载进容器 |
| API Key | 本地 `.env` 文件 | 不能进镜像，防泄露（含 SiliconFlow + DeepSeek） |
| 源代码 | 本地目录 | 开发时改代码，容器里实时生效（--reload） |

---

## 七、常见问题

### Q: Docker Desktop 启动很慢？
正常现象，首次启动需要 30-60 秒。等托盘图标变绿即可。

### Q: 端口被占用？
```
Error: Bind for 0.0.0.0:3306 failed: port is already allocated
```
说明你本地已经装了 MySQL 占了 3306 端口。两种解决方式：
1. 关掉本地 MySQL 服务
2. 改 `docker-compose.dev.yml` 中的端口：`"3307:3306"`（外部用 3307 连）

### Q: 容器启动后立刻退出？
查看日志找原因：
```bash
docker compose -f docker-compose.dev.yml logs etc-qa
```

### Q: 改了代码但不生效？
开发环境用了 `--reload`，代码改动会自动生效。如果没生效：
```bash
docker compose -f docker-compose.dev.yml restart etc-qa
```

### Q: 改了 requirements.txt 不生效？
需要重新构建镜像：
```bash
docker compose -f docker-compose.dev.yml build etc-qa
docker compose -f docker-compose.dev.yml up -d etc-qa
```

### Q: 想完全重置环境？
```bash
docker compose -f docker-compose.dev.yml down -v   # 删除容器+数据卷
docker compose -f docker-compose.dev.yml up -d       # 重新启动
```
⚠️ `-v` 会删除 MySQL 数据，需要重新运行 `init_db.py`

### Q: 容器里怎么执行命令？
```bash
# 进入应用容器的终端
docker compose -f docker-compose.dev.yml exec etc-qa sh

# 直接执行单条命令
docker compose -f docker-compose.dev.yml exec etc-qa python scripts/data/init_db.py dev
```

### Q: Windows 下 Docker 很卡？
Docker Desktop → Settings → Resources：
- Memory: 建议 4GB+
- CPUs: 建议 2+
- Disk: 建议 20GB+
