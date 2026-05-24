# ScholarMine

**Agent-Orchestrated Academic Literature Mining Pipeline**

> 自然语言输入 → 智能关键词扩展 → 20+ 平台并行抓取 → 自动筛选分类 → LLM 批量信息提取 → Markdown + CSV 输出

## 核心能力

- **一句话启动**：`scholarmine plan "研究主题"` — Agent 自动解析意图、生成关键词、推断提取 Schema
- **大规模抓取**：单次可抓 1000-5000 篇，覆盖 arXiv、Semantic Scholar、Sci-Hub 等 20+ 平台
- **智能筛选**：自动剔除勘误/综述/无关文献，四级分类归档
- **批量 LLM 提取**：40-50 篇/批发送 DeepSeek V4，输出 128K 结构化数据
- **标准输出**：每篇独立 .md + 汇总 .csv，15+ 字段灵活定制

## 快速开始

### 1. 安装

```bash
cd ScholarMine
pip install -e .
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY
```

### 3. 运行

```bash
# 规划（Agent 生成关键词 + Schema + 执行计划）
scholarmine plan "single-atom catalysts for CO2 electroreduction 2023-2025" -n 1500

# 执行（直接从配置文件跑）
scholarmine run

# 查看状态
scholarmine status

# 断点续跑
scholarmine resume
```

## 架构

```
用户自然语言
    │
    ▼
┌─────────────┐     ┌──────────────────────────────────────┐
│  Agent 层    │────▶│  生成 config.yaml（关键词/平台/Schema） │
│  (智能规划)   │     └──────────────────────────────────────┘
└─────────────┘                       │
                                      ▼
┌──────────────────────────────────────────────────────────┐
│                   Pipeline 层（可靠执行引擎）               │
│                                                           │
│  Stage 1 ──▶ Stage 2 ──▶ Stage 3 ──▶ Stage 4 ──▶ Stage 5 │
│  关键词      文献抓取     筛选分类     信息提取     拆分存储  │
│  25 words   2000 PDFs   accepted/    llm_raw/     *.md     │
│                         rejected/    batch        *.csv    │
└──────────────────────────────────────────────────────────┘
```

## 项目结构

```
ScholarMine/
├── config/
│   ├── default.yaml          # 全局默认配置
│   ├── platforms.yaml        # 20 个平台配置
│   └── schemas/              # 可复用提取 Schema
├── src/scholar_mine/
│   ├── cli.py                # CLI 入口
│   ├── agent/                # Agent 层（规划/关键词/Schema推断）
│   ├── pipeline/             # Pipeline 层（5 个 Stage）
│   ├── crawlers/             # 20 个爬虫
│   ├── llm/                  # DeepSeek API 客户端
│   ├── pdf/                  # PDF 读取 + 参考文献切除
│   ├── store/                # MD/CSV 写入
│   └── utils/                # 日志/断点/重试/校验
└── tests/
```

## 依赖

- Python ≥ 3.11
- DeepSeek API (V4-Flash)
- PyMuPDF (PDF 解析)
- 20+ 学术平台 API

## License

MIT