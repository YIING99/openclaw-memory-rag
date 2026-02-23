# OpenClaw Memory RAG

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Gateway-blue)](https://github.com/nicepkg/openclaw)

[English](README.md) | 中文

> 给 OpenClaw 龙虾装上长期记忆——用 Hybrid Search（向量语义 70% + BM25 关键词 30%）实现跨会话精准知识召回。

---

## 这个项目是什么？

一套**开箱即用的 Memory RAG 方案**，让你的 OpenClaw AI Agent 具备跨会话的语义搜索能力。

**核心能力**：
- 用自然语言搜索历史知识（"之前那篇关于 XX 的文章"）
- Hybrid Search 双通道：向量语义匹配 + BM25 精确关键词
- 飞书多维表格双写同步（可选）
- Daily 日志自动归档（防止噪音污染搜索）

**最终效果**：
```
你："之前有没有讲过美国手机号的？"
龙虾：找到了！Tello eSIM，5美元月租美国手机号……（精准召回）

你："帮我找一下关于 AI 幻觉的记录"
龙虾：找到了！信任链污染定律——描述≠现实……（精准召回）
```

## 仓库结构

```
openclaw-memory-rag/
├── README.md                          # English README
├── README.zh-CN.md                    # 中文 README（本文件）
├── LICENSE                            # MIT License
├── docs/
│   └── technical-report.zh-CN.md      # 技术方案报告（含行业方案对比）
├── scripts/
│   ├── sync-feishu-to-memory.py       # 飞书单表 → memory/ 同步脚本
│   ├── sync-feishu-to-memory-multi.py # 飞书多表 → memory/ 同步脚本
│   └── move-daily-logs.sh             # Daily 日志归档脚本
└── examples/
    ├── openclaw-config.json            # memorySearch 配置示例
    ├── soul-dualwrite-snippet.md       # SOUL.md 双写规则片段
    └── knowledge-file-template.md      # 知识文件模板
```

---

## 前置条件

| 条件 | 说明 | 没有的话 |
|------|------|---------|
| **一只 OpenClaw 龙虾** | 已经能正常对话的 OpenClaw Gateway 实例 | 先装 OpenClaw |
| **VPS 或服务器** | 龙虾运行的机器，能 SSH 登录 | 可以用 DigitalOcean $6/月 |
| **Embedding API Key** | 用于将文本转为向量（本教程用智谱 ZAI） | 下面第一步会教你申请 |
| **知识内容** | 你想让龙虾记住的知识（文章、笔记、经验……） | 至少准备 5-10 条 |

**可选但推荐**：
- 飞书多维表格（结构化存储 + 可视化管理）
- 飞书应用（用于 API 同步）

---

## 第一步：申请 Embedding API Key

### 推荐：智谱 ZAI embedding-3

**为什么选它**：
- 中文语义理解优秀（比通用多语言模型好很多）
- 2048 维向量（信息密度高）
- 兼容 OpenAI 接口协议（OpenClaw 原生支持）
- 成本低（按量付费）

**申请步骤**：

1. 打开 [智谱 AI 开放平台](https://open.bigmodel.cn/)
2. 注册账号并登录
3. 进入「控制台」→「API Keys」→ 创建一个新的 API Key
4. **重要**：进入「资源包」页面，确认 embedding 有可用额度
   - 注意：GLM Coding Pro 套餐**不包含** embedding 用量，需要单独订阅

**记下你的 API Key**，后面要用。格式类似：`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx`

### 备选方案

| 模型 | 优点 | 缺点 | 适合场景 |
|------|------|------|---------|
| **ZAI embedding-3（推荐）** | 中文好，2048维 | 需付费 | 中文为主的知识库 |
| OpenAI text-embedding-3-small | 多语言，生态好 | 需翻墙，贵 | 英文为主 |
| Gemini embedding-001 | 免费额度 | 日限额容易打满 | 测试用 |
| 本地 embeddinggemma | 免费离线 | 中文差，占内存 | 不推荐 |

---

## 第二步：配置 memorySearch

SSH 登录你的 VPS，编辑 OpenClaw 配置文件。

### 2.1 找到你的 openclaw.json

```bash
# 如果你只有一个龙虾实例
cat ~/.openclaw/openclaw.json

# 如果你有多个实例，找到对应实例的配置
# 例如第二只龙虾的配置可能在 /root/bot2-home/.openclaw/openclaw.json
cat /root/bot2-home/.openclaw/openclaw.json
```

### 2.2 添加 memorySearch 配置

在 `openclaw.json` 的 `agents.defaults` 中添加 `memorySearch` 块。

完整配置示例见 [`examples/openclaw-config.json`](examples/openclaw-config.json)。

**如果你用 ZAI embedding-3**：

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "openai",
        "model": "embedding-3",
        "remote": {
          "baseUrl": "https://open.bigmodel.cn/api/paas/v4/",
          "apiKey": "YOUR_ZAI_API_KEY_HERE"
        },
        "query": {
          "hybrid": {
            "enabled": true,
            "vectorWeight": 0.7,
            "textWeight": 0.3,
            "candidateMultiplier": 4
          }
        },
        "cache": {
          "enabled": true,
          "maxEntries": 10000
        }
      }
    }
  }
}
```

**如果你用 OpenAI embedding**：

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "remote": {
          "apiKey": "YOUR_OPENAI_API_KEY_HERE"
        },
        "query": {
          "hybrid": {
            "enabled": true,
            "vectorWeight": 0.7,
            "textWeight": 0.3,
            "candidateMultiplier": 4
          }
        },
        "cache": {
          "enabled": true,
          "maxEntries": 10000
        }
      }
    }
  }
}
```

**关键参数解释**：

| 参数 | 含义 | 建议值 | 为什么 |
|------|------|--------|--------|
| `provider` | 接口协议 | `"openai"` | ZAI 兼容 OpenAI 协议，所以写 openai |
| `model` | Embedding 模型名 | `"embedding-3"` | ZAI 的模型名 |
| `remote.baseUrl` | API 地址 | 智谱的 URL | 不填则默认 OpenAI 官方 |
| `vectorWeight` | 语义搜索权重 | `0.7` | 70% 靠语义理解 |
| `textWeight` | 关键词搜索权重 | `0.3` | 30% 靠精确匹配 |
| `candidateMultiplier` | 候选扩展倍数 | `4` | 搜 4 倍候选再排序，提高精度 |

### 2.3 验证配置

```bash
# 检查 JSON 格式是否正确（不报错就是 OK）
python3 -c "import json; json.load(open('openclaw.json'))"
```

---

## 第三步：准备知识文件

这是**最关键的一步**——你要告诉龙虾"记住什么"。

### 3.1 知识文件存放位置

```bash
# 进入你的龙虾 workspace 的 memory 目录
ls ~/.openclaw/workspace/memory/

# 多实例用户示例
ls /root/bot2-home/.openclaw/workspace/memory/
```

如果 `memory/` 目录不存在，创建它：

```bash
mkdir -p ~/.openclaw/workspace/memory/
```

### 3.2 知识文件格式

**每条知识 = 一个独立的 .md 文件。** 这是本方案的核心原则。

文件模板见 [`examples/knowledge-file-template.md`](examples/knowledge-file-template.md)。

### 3.3 文件命名

- **有飞书记录**：用飞书记录 ID 命名，如 `recvbmdEE6JDXb.md`
- **无飞书**：用有意义的短名，如 `tello-esim.md`、`n26-bank.md`
- **避免**：中文文件名、空格、特殊字符

### 3.4 实际案例

**文件名**：`tello-esim.md`

```markdown
## [2026-02-16] Tello eSIM：5美元月租美国手机号
- **类型**：🔗 工具发现 | **来源**：公众号 | **评级**：⭐⭐ 值得加工
- **标签**：海外工具, 开发技巧, eSIM, 支付工具

**核心洞察**：Tello 是基于 T-Mobile 网络的虚拟运营商（MVNO），
提供真实美国手机号码（非VoIP虚拟号），支持 eSIM 线上购买，
月租5美元起。通过 WiFi Calling 技术在国内可用，
能接收银行/券商验证码、注册 AI 服务。

**关键论点**：
- 三大优势：实体运营商号码、eSIM线上购买、WiFi Calling
- 对比：Google Voice 免费但易封号、Ultra Mobile 需实体卡

**行动项**：试用 Tello eSIM，写"必备海外工具"系列文章

**搜索关键词**：Tello, eSIM, 美国手机号, 虚拟号码, 海外号码,
T-Mobile, WiFi Calling, 接收验证码, 注册AI服务, 月租5美元
```

### 3.5 搜索关键词怎么写？

搜索关键词**不是给人看的，是给搜索引擎看的**。写的时候想：

> "如果用户用什么词来搜索，应该能找到这条知识？"

包含三类词：
1. **核心概念**：Tello, eSIM, T-Mobile
2. **中文同义词**：美国手机号, 虚拟号码, 海外号码
3. **使用场景**：接收验证码, 注册AI服务, 月租5美元

### 3.6 为什么一条知识 = 一个文件？

这是本方案最重要的设计决策。对比：

```
❌ 错误做法：10 条知识合并在 1 个大文件里
   → 搜索引擎按固定长度切分（chunk），一个 chunk 可能包含
     A 记录的后半段 + B 记录的前半段
   → 搜索"Tello eSIM"命中的 chunk，开头却是 GLM-5 的内容
   → 精度暴跌

✅ 正确做法：10 条知识 = 10 个独立文件
   → 每个文件刚好一个 chunk
   → 搜索命中 = 完整的一条知识
   → 精度最高
```

实测数据：拆分文件后，搜索精度提升 23%（Tello 从 0.632 → 0.777）。

---

## 第四步：构建向量索引

知识文件准备好后，需要"向量化"——让搜索引擎理解每条知识的语义。

### 4.1 构建索引

```bash
# ⚠️ 多实例用户必须先设 HOME！
# 如果你只有一个龙虾，跳过这行
export HOME=/root/bot2-home   # 改成你的龙虾配置目录的父目录

# 进入 OpenClaw 目录
cd ~/.openclaw

# 构建索引（--force 表示强制重建）
npx openclaw memory index --force
```

**成功标志**：
```
Memory index updated (main).
```

**常见报错和解决方案**：

| 报错 | 原因 | 解决 |
|------|------|------|
| `No API key found for provider openai` | HOME 没设对，读了别的实例配置 | `export HOME=` 设为正确路径 |
| `ECONNREFUSED` | API 地址不通 | 检查 `remote.baseUrl` 是否正确 |
| `401 Unauthorized` | API Key 无效 | 检查 Key 是否正确、是否有 embedding 额度 |
| 无任何输出 | memory/ 目录为空 | 先创建知识文件 |

### 4.2 测试搜索

```bash
# 测试一下！
npx openclaw memory search '你的搜索词'

# 示例
npx openclaw memory search '美国手机号'
npx openclaw memory search 'AI幻觉防治'
```

**理想结果**：
```
0.777 memory/tello-esim.md:1-16
## [2026-02-16] Tello eSIM：5美元月租美国手机号
...
```

格式说明：`分数 文件路径:行范围`
- 分数越高越相关（1.0 = 完美匹配）
- 0.3 以上通常就是有效结果

---

## 第五步：管理 Daily 日志（防止噪音污染）

OpenClaw 会自动在 memory/ 目录生成 daily 心跳日志（`2026-02-23.md`），内容大量是"✅ 正常，无异常"。

**这些日志会严重干扰搜索精度**——90% 是噪音，被向量化后挤占真正知识的排名。

### 5.1 使用归档脚本

将 [`scripts/move-daily-logs.sh`](scripts/move-daily-logs.sh) 复制到你的龙虾 HOME 目录：

```bash
cp move-daily-logs.sh ~/move-daily-logs.sh
chmod +x ~/move-daily-logs.sh
```

### 5.2 设置自动定时任务

```bash
# 添加 cron：每天早上 6 点归档一次
(crontab -l 2>/dev/null; echo '0 6 * * * $HOME/move-daily-logs.sh') | crontab -

# 验证
crontab -l | grep move-daily
```

### 5.3 手动执行一次

```bash
~/move-daily-logs.sh

# 检查结果
echo "=== memory 目录（应该只有知识文件 + 今天的 daily）==="
ls ~/.openclaw/workspace/memory/

echo "=== archive 目录（归档的 daily 文件）==="
ls ~/.openclaw/workspace/daily-archive/
```

---

## 第六步：设置双写机制（可选但强烈推荐）

如果你的龙虾会自动捕获知识到飞书多维表格，那需要确保**飞书写了 → memory/ 也有**。

### 6.1 方案 A：SOUL.md 双写规则

在你的龙虾 SOUL.md 中追加双写规则。完整片段见 [`examples/soul-dualwrite-snippet.md`](examples/soul-dualwrite-snippet.md)。

### 6.2 方案 B：Cron 自动同步脚本

**单表同步**：[`scripts/sync-feishu-to-memory.py`](scripts/sync-feishu-to-memory.py)

**多表同步**：[`scripts/sync-feishu-to-memory-multi.py`](scripts/sync-feishu-to-memory-multi.py)

部署方式：

```bash
# 修改脚本顶部的配置（APP_ID、SECRET、TABLE_ID 等）
vi ~/sync_feishu_to_memory.py

# 设置定时运行（每6小时）
(crontab -l 2>/dev/null; echo '30 */6 * * * /usr/bin/python3 $HOME/sync_feishu_to_memory.py >> /tmp/feishu-sync.log 2>&1') | crontab -
```

---

## 第七步：验证一切正常

### 7.1 完整检查清单

```bash
echo "=== 1. 配置文件检查 ==="
python3 -c "
import json, os
c = json.load(open(os.path.expanduser('~/.openclaw/openclaw.json')))
ms = c.get('agents',{}).get('defaults',{}).get('memorySearch',{})
print('  provider:', ms.get('provider','❌ 未配置'))
print('  model:', ms.get('model','❌ 未配置'))
print('  hybrid:', '✅ 开启' if ms.get('query',{}).get('hybrid',{}).get('enabled') else '❌ 未开启')
" 2>/dev/null || echo "  ❌ 配置文件解析失败"

echo ""
echo "=== 2. 知识文件检查 ==="
echo "  文件数量: $(ls ~/.openclaw/workspace/memory/*.md 2>/dev/null | wc -l)"
echo "  最新文件:"
ls -lt ~/.openclaw/workspace/memory/*.md 2>/dev/null | head -3

echo ""
echo "=== 3. 搜索测试 ==="
npx openclaw memory search '测试搜索' 2>/dev/null | head -5
echo "(如果有结果显示分数和文件名，就是成功了)"

echo ""
echo "=== 4. Cron 任务检查 ==="
crontab -l 2>/dev/null | grep -E 'move-daily|sync_feishu' || echo "  ⚠️ 未设置定时任务"
```

### 7.2 搜索测试用例

```bash
# 用知识标题搜索（应该高分命中）
npx openclaw memory search '你的某条知识标题'

# 用同义词搜索（测试语义理解）
npx openclaw memory search '换一种说法描述你的知识'

# 用口语化表达搜索（测试自然语言）
npx openclaw memory search '之前好像有一篇讲XX的'
```

**分数参考**：
- 0.7+ 精准命中
- 0.4-0.7 相关命中
- 0.3-0.4 模糊相关
- <0.3 可能不相关

---

## 常见问题 FAQ

### Q1：搜索没有任何结果？

1. `ls ~/.openclaw/workspace/memory/` 确认有 .md 文件
2. `npx openclaw memory index --force` 重建索引
3. 检查 openclaw.json 中 memorySearch 配置是否正确
4. 多实例用户：确认 `export HOME=` 设对了

### Q2：搜索结果不准？

1. memory/ 中有 daily 心跳日志（大量噪音）→ 运行归档脚本
2. 多条知识合并在一个大文件中 → 拆分为独立文件
3. 搜索关键词缺失 → 给每个文件加 `**搜索关键词**` 行

### Q3：新增知识后需要重建索引吗？

- **SOUL.md 双写**：OpenClaw 会自动增量索引
- **手动添加文件后**：需要运行 `npx openclaw memory index --force`
- **Cron 同步脚本**：脚本会自动重建索引

### Q4：VPS 内存不够跑 Embedding 模型？

不需要本地跑！本方案用**云端 API**（ZAI embedding-3），3.8GB VPS 完全够用。

### Q5：没有飞书怎么办？

完全可以不用飞书！核心是 memory/ 目录中的 .md 文件。你可以手动创建，或从 Notion/Obsidian 导出。

### Q6：多个龙虾能共享一套知识库吗？

可以：软链接、rsync 同步、或各实例独立维护。

### Q7：hybrid search 的 70/30 权重要调吗？

默认适合大多数场景。语义搜索太模糊 → 降低 vectorWeight；关键词太死板 → 提高 vectorWeight。

---

## 核心原则速查卡

### 原则一：一条知识 = 一个文件 = 一个 chunk

不要把多条知识塞进一个大文件。独立文件 = 精准搜索。

### 原则二：搜索关键词是给机器看的

每个文件底部的 `**搜索关键词**` 行，是 BM25 搜索通道的燃料。写同义词、场景词、英文缩写。

### 原则三：噪音是精度的天敌

memory/ 目录只放高质量知识文件。日志、心跳、临时文件统统归档到别处。

---

## 方案架构一图流

```
你对龙虾说话 / 发文章
         ↓
    龙虾提炼知识
         ↓
   ┌─────┴─────┐
   ↓           ↓
飞书多维表格   memory/{id}.md    ← 双写
(结构化存储)   (向量化存储)
   ↓           ↓
可视化管理    Hybrid Search
标签/评级     vector 70% + BM25 30%
   ↓           ↓
   └─────┬─────┘
         ↓
  用户问"之前那篇..."
         ↓
    精准召回 ✅
```

---

## 技术报告

想了解完整的技术设计、行业方案对比、四轮迭代优化数据？请查看：

📄 [技术方案报告](docs/technical-report.zh-CN.md)

---

## Contributing

欢迎提交 Issue 和 PR！

- **Bug 报告**：请描述你的 OpenClaw 版本、Embedding 模型、复现步骤
- **功能建议**：请描述场景和期望效果
- **脚本改进**：欢迎支持更多知识源（Notion、Obsidian、Telegram 等）

## Star History

如果这个项目对你有帮助，请给一个 Star ⭐

---

*作者：KingMaker | 基于龙虾军团实战经验*
