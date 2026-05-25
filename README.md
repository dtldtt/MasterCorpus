# MasterCorpus — 投资大师公开材料归档

为 BigV-twins 项目准备的投资大师 RAG 语料源仓库。每位大师一个子目录，
存放公开演讲 / 致股东信 / 著作（电子版）/ 大会问答的原始或转换 markdown。

## 目录结构

```
MasterCorpus/
├── buffett/                     # 巴菲特（先行者）
│   ├── letters/                  # 1977-2024 致股东信 (md + pdf)
│   ├── BRK-Annual-Meeting/       # 1994-2022 股东大会中文 Q&A
│   ├── BRK-Annual-Meeting-Supplement/
│   ├── scripts/                  # 抓取 / 转换脚本
│   └── README.md                 # 巴菲特独立 README（数据来源 + 流程）
│
├── munger/                      # 查理·芒格
│   ├── books/                    # 《穷查理宝典》epub
│   └── speeches/                 # 4 篇核心演讲（fs.blog + Wayback 抓取）
│       ├── 1994-a-lesson-on-elementary-worldly-wisdom-usc-marshall-school.md
│       ├── 1995-the-psychology-of-human-misjudgment-harvard-law-school.md
│       ├── 2007-usc-law-commencement-wisdom-speech.md
│       └── 2017-the-munger-operating-system-tilson-hosts.md
│
├── graham/                      # 本杰明·格雷厄姆
│   └── books/
│       ├── 聪明的投资者.epub
│       └── 《证券分析》.pdf
│
└── lynch/                       # 彼得·林奇
    └── books/
        ├── 彼得·林奇的成功投资.epub
        ├── 战胜华尔街.epub
        └── 彼得·林奇教你理财.mobi
```

## 大师状态

| Slug | 中文名 | Corpus 体量 | RAG 索引 | BigV-twins 集成 |
|------|--------|------------|----------|---------------|
| `buffett` | 沃伦·巴菲特 | 致股东信 48 + 大会 Q&A 36 年 | ✅ buffett.db (75 MB) | ✅ |
| `munger` | 查理·芒格 | 4 演讲 + 1 epub (51 MB) | ⏳ 待建 | ⏳ |
| `graham` | 本杰明·格雷厄姆 | 2 本书（epub + pdf） | ⏳ 待建 | ⏳ |
| `lynch` | 彼得·林奇 | 3 本书（2 epub + 1 mobi） | ⏳ 待建 | ⏳ |

## 数据流

```
private:masters-corpus/   ← 用户上传 / 我抓取的源
       ↓ tar.gz over local 中转
highper:MasterCorpus/      ← 本仓库（git push GitHub）
       ↓ ingest_<slug>.py（PDF/EPUB/MOBI → md → bge-m3 嵌入）
highper:BigV-twins/twins/<slug>.db   ← RAG 索引产物
       ↓ rsync over local 中转
private:BigV-twins/twins/<slug>.db   ← 服务消费
```

## 工具栈

- **PDF → Markdown**：[Marker](https://github.com/datalab-to/marker)（巴菲特已用过；speeches 直接是 md）
- **EPUB / MOBI → Markdown**：`calibre ebook-convert`（统一处理所有电子书格式）
- **嵌入模型**：`BAAI/bge-m3`（中英双语，1024 维，最大 8192 tokens；和 zhihu twins 一致）
- **向量存储**：`sqlite-vec` 扩展（同 zhihu twins）

## 引用约定（chat 用）

每个 chunk 在 `chunks` 表里都有 `zhihu_id` 字段（被借用为通用 source ID）：

| 大师 | source ID 格式 |
|------|---------------|
| buffett | `letter-<year>-<section_idx>` / `meeting-<year>-<filename_hash8>-<qa_idx>` |
| munger | `speech-<year>-<slug_hash8>-<chunk_idx>` / `book-<book_hash8>-<chapter_idx>` |
| graham | `book-<book_hash8>-<chapter_idx>` |
| lynch | `book-<book_hash8>-<chapter_idx>` |

zhihu 归档站 (https://8-155-174-112.nip.io:8000/masters/) 渲染相应 markdown，
chat 引用按 hash 路由 `/m/<year>/<hash8>` 跳转。

## 复现某位大师的入库流程

```bash
# Buffett (existing — 不用重跑)
cd /home/dtl/projects/data/MasterCorpus/buffett
# scripts/ 下有完整 fetch + convert 流水

# Munger / Graham / Lynch (新)
cd /home/dtl/projects/BigV-twins
python scripts/ingest_munger.py --data-dir /home/dtl/projects/data/MasterCorpus/munger
python scripts/ingest_graham.py --data-dir /home/dtl/projects/data/MasterCorpus/graham
python scripts/ingest_lynch.py --data-dir /home/dtl/projects/data/MasterCorpus/lynch
# 产物：~/projects/BigV-twins/twins/{munger,graham,lynch}.db
```

## License

各大师材料按其原作权利人许可使用。本仓库仅做学习研究用，**不得用于商业用途、再分发或公开二次发布**。
- 巴菲特致股东信：Berkshire Hathaway 公开内容
- 芒格演讲：fs.blog / Farnam Street 转载或 Wayback Machine 历史快照
- 商业出版书籍（穷查理宝典 / 证券分析 / 聪明的投资者 / 林奇三部曲等）：
  仅限本人投资研究学习，禁止再分发。
