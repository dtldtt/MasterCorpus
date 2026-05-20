# BRK-Annual-Meeting-Supplement

补充原 `BRK-Annual-Meeting/` 子目录中**缺失的年份**：2017、2018、2024、2025（2023 暂未找到完整文字稿，跳过）。

每份文件均**附带原始来源说明**，请在引用时注意区分翻译者和编辑版本。

## 目录结构

```
BRK-Annual-Meeting-Supplement/
├── 2017/
│   └── 2017_BRK_AnnualMeeting_EN.pdf            # CNBC 编辑版（73 页）
├── 2018/
│   └── 2018_BRK_AnnualMeeting_EN.pdf            # CNBC 编辑版（145 页）
├── 2023/                                         # ⚠️ 暂缺，CNBC 仅有视频和分段精彩片段
├── 2024/
│   ├── 2024_BRK_AnnualMeeting_EN_morning.md     # 上午场逐字稿
│   ├── 2024_BRK_AnnualMeeting_EN_afternoon.md   # 下午场逐字稿
│   └── 2024_BRK_AnnualMeeting_CN.md             # 中文 4 万字版（公众号转载）
└── 2025/
    ├── 2025_BRK_AnnualMeeting_EN.md             # 完整逐字稿
    └── 2025_BRK_AnnualMeeting_CN.md             # 中文按问题分段整理版
```

## 各年份资源说明

### 2017 — `2017_BRK_AnnualMeeting_EN.pdf`

- **来源**：ValuePickr Forum 第三方镜像
- **原始版本**：CNBC 提供的 **Edited Transcript**（编辑版，非逐字稿）
- **原文链接**：<https://forum.valuepickr.com/uploads/default/original/2X/7/7e8e091d9fdbc77fd45d49479502f73a832bde4d.pdf>
- **规模**：73 页，约 24.4 万字符
- **完整性**：覆盖完整问答（开场 → Wells Fargo 讨论 → 收盘）

### 2018 — `2018_BRK_AnnualMeeting_EN.pdf`

- **来源**：AWS S3 第三方托管镜像
- **原始版本**：CNBC 提供的 **Edited Transcript**（编辑版）
- **原文链接**：<https://s3.amazonaws.com/static.contentres.com/media/documents/e3ab342f-baae-465d-a5d3-41a789b624cb.pdf>
- **规模**：145 页，约 26.6 万字符
- **完整性**：覆盖开场至股东大会决议结束

### 2023 — 暂缺

完整文字稿目前在网上未找到统一版本：
- CNBC Buffett Archive 仅提供官方视频和按主题切片的精彩片段：<https://buffett.cnbc.com/2023-berkshire-hathaway-annual-meeting/>
- 国内媒体多为新闻摘要而非全程实录

待后续找到完整版再补充。

### 2024 — 三份文件

- **`2024_BRK_AnnualMeeting_EN_morning.md`**（上午场，约 11 万字符）
  - 来源：[Good Investing - Tilman Versch](https://www.good-investing.net/2025/04/20/warren-buffett-berkshires-2024-annual-shareholder-meeting/)
- **`2024_BRK_AnnualMeeting_EN_afternoon.md`**（下午场，约 9 万字符）
  - 来源：[Good Investing - Tilman Versch](https://www.good-investing.net/2025/04/22/berkshire-hathaway-annual-meeting-2024-transcript-afternoon-session/)
- **`2024_BRK_AnnualMeeting_CN.md`**（中文 4 万字版）
  - 来源：CSDN @datawhale 转载，原始来源为微信公众号
  - 原文链接：<https://blog.csdn.net/datawhale/article/details/138480852>
  - 内容：含巴菲特/芒格继任、苹果减持、美元贬值、并购讨论等热点
  - 规模：4.3 万中文字符

### 2025 — 两份文件

- **`2025_BRK_AnnualMeeting_EN.md`**（约 15 万字符）
  - 来源：[Steady Compounding](https://steadycompounding.com/transcript/brk-2025/)
  - 完整逐字稿，含巴菲特宣布交班 Greg Abel 的著名对话
- **`2025_BRK_AnnualMeeting_CN.md`**（约 1.7 万中文字符）
  - 来源：新浪财经（华尔街见闻汇总）
  - 原文链接：<https://finance.sina.cn/china/gjcj/2025-05-04/detail-inevkfsy6079193.d.html>
  - **⚠️ 注意**：这是按问题编号（Q1-Q32）整理的**摘要版**，不是逐字稿，但覆盖全部 32 个股东问答
  - 与 wuxiaoda/BRK-Annual-Meeting 历年中文逐字稿风格不同，引用时请注意

## ⚠️ 数据质量提示

1. **来源异质性**：本目录收集自 5 个不同来源，编辑/翻译水平、详略程度不一致。
   - 2017/2018 是 **CNBC 编辑版**（删去无关内容，但保留所有问答）
   - 2024/2025 EN 是 **第三方逐字稿**
   - 2024 CN 是 **公众号自行整理的中文版**（约 4 万字，相对完整）
   - 2025 CN 是 **新闻整理的精华版**（按问题分段，描述+引用混合）
2. **与 `BRK-Annual-Meeting/` 的区别**：原目录来自 [wuxiaoda/BRK-Annual-Meeting](https://github.com/wuxiaoda/BRK-Annual-Meeting)，由「一朵喵」等单一翻译者按上午/下午/上中下篇拆分；本目录文件不遵循该拆分约定，文件命名独立。
3. **2023 缺失**：见上述说明。

## 重新生成

```bash
cd /home/dtl/projects/data/BuffettLetters
python3 scripts/fetch_meetings.py
```

脚本会自动跳过已存在的 PDF，HTML 内容会从 `/tmp/brk_html_cache/` 读取缓存（删除该目录可强制重新抓取）。

## 数据规模汇总

| 年份 | 英文 | 中文 |
|---|---|---|
| 2017 | PDF 482 KB / 73 页 | — |
| 2018 | PDF 679 KB / 145 页 | — |
| 2023 | ⚠️ 暂缺 | ⚠️ 暂缺 |
| 2024 | MD 110 KB（上午）+ 89 KB（下午） | MD 138 KB（4 万中文字符） |
| 2025 | MD 151 KB | MD 56 KB（1.7 万中文字符，摘要版） |
