# BuffettLetters

巴菲特致股东信（Berkshire Hathaway Shareholder Letters）数据集，包含 1977-2024 年共 48 封致股东信。

## 📊 数据来源

数据全部抓取自伯克希尔·哈撒韦官方网站索引页：

- **官网索引**：<https://www.berkshirehathaway.com/letters/letters.html>
- **覆盖年份**：1977 - 2024（共 48 年，无缺失）
- **抓取时间**：2026-05

## 📁 目录结构

```
BuffettLetters/
├── README.md          # 本文件
├── letters/           # 数据：48 份致股东信
│   ├── 1977.md ~ 2001.md   # 25 份 Markdown（由官网 HTML 转换而来）
│   └── 2002.pdf ~ 2024.pdf # 23 份 PDF（官网原始 PDF，未转换）
└── scripts/           # 抓取脚本
    ├── fetch_letters.py   # 主抓取器（多线程并发）
    ├── fetch_retry.py     # 失败项重试
    ├── fetch_final.py     # 特殊路径收尾（处理 chooser 页面）
    └── fetch_repair.py    # 修复 gzip 乱码（curl --compressed）
```

## 📝 数据说明

### Markdown 文件（1977-2001，共 25 份）

由官网 HTML 转换而来。每份文件以以下头部开始：

```markdown
# Berkshire Hathaway Shareholder Letter — YYYY

Source: <原始 URL>

---

（信件正文）
```

特殊路径说明（抓取脚本中已处理）：
- 1977-1997：直接位于 `/letters/YYYY.html`
- 1998-1999：位于 `/letters/YYYYhtm.html`（YYYY.html 是中转选择页）
- 2000-2001：位于 `/YYYYar/YYYYletter.html`（不在 letters 目录下）

### PDF 文件（2002-2024，共 23 份）

官网未提供 HTML 版，直接保存原始 PDF：
- 2002：`/letters/2002pdf.pdf`
- 2003-2024：`/letters/YYYYltr.pdf`

文件大小从 54KB（2022）到 2.4MB（2015，含图表）不等。

## 🛠️ 脚本使用

### 环境依赖

```bash
pip install --break-system-packages markdownify beautifulsoup4 requests
# 系统需要：python3, curl
```

### 完整复现抓取流程

按顺序执行（首次抓取请按此顺序）：

```bash
cd BuffettLetters/scripts

# 1. 主抓取（并发 8 线程，处理 1977-2003 HTML 和 2004-2024 PDF）
python3 fetch_letters.py

# 2. 重试第一轮失败的项（连接超时/重置导致的）
python3 fetch_retry.py

# 3. 处理特殊路径
#    - 2000/2001 真实 HTML 在 /YYYYar/YYYYletter.html
#    - 2002/2003 仅有 PDF（无 HTML 版）
#    - 1982 重试
python3 fetch_final.py

# 4. 修复乱码（如发现 .md 文件包含大量非 ASCII 字符）
python3 fetch_repair.py
```

数据已保存到 `../letters/`，脚本支持幂等（已存在的文件会跳过）。

### 单独脚本说明

| 脚本 | 用途 | 关键点 |
|---|---|---|
| `fetch_letters.py` | 批量并发抓取主脚本 | 8 线程并发，使用 `requests` |
| `fetch_retry.py` | 顺序重试失败项 | 单线程 + 长超时 + 3 次重试 |
| `fetch_final.py` | 处理特殊 URL 路径 | 处理 chooser 页与异常路径 |
| `fetch_repair.py` | 修复 gzip 乱码 | 改用 `curl --compressed` 强制解压 |

## ⚠️ 已知陷阱（抓取时踩过的坑）

1. **gzip 响应未解压**：`requests` 在某些情况下不会自动解压 `Content-Encoding: gzip` 的响应，写入文件后是二进制乱码（外观字节不小，但 76% 都是非 ASCII）。**解决方案**：改用 `curl --compressed`。
2. **1998-1999 中转页**：`YYYY.html` 是 PDF/HTML 选择页，真实内容在 `YYYYhtm.html`。
3. **2000-2001 路径异常**：HTML 不在 `/letters/` 下，而在 `/YYYYar/YYYYletter.html`。
4. **2002-2003 无 HTML 版**：官网仅提供 PDF。
5. **服务器并发限制**：超过 8 线程容易触发连接重置，重试时需顺序请求。

## 📈 数据规模

| 类型 | 数量 | 字数/大小范围 |
|---|---|---|
| Markdown | 25 份 | 3,064 ~ 16,234 词/份 |
| PDF | 23 份 | 54 KB ~ 2.4 MB/份 |
| **总计** | **48 份** | **约 8.6 MB** |

## 🔍 数据质量验证

所有 25 份 Markdown 已验证：
- 非 ASCII 字符占比 < 3%
- 包含 "Warren E. Buffett" 签名
- 字数与年份匹配（早年偏短，后期稳定）

所有 23 份 PDF 已验证：
- 文件头为 `%PDF-` 标识
- 文件大小符合预期

## 🚀 后续建议

如需将 PDF 也转为 Markdown 进行统一文本检索/分析，推荐工具：

- **MinerU**：版面/公式/表格识别质量最佳，适合致股东信这类规整文档
- **Marker**：速度更快，质量略低
- **Markitdown**（微软）：轻量但对复杂版面效果一般

```bash
# 示例：用 MinerU 批量转换 PDF
pip install -U "magic-pdf[full]"
ls letters/*.pdf | xargs -P 6 -I {} magic-pdf -p {} -o letters_md_from_pdf -m auto
```
