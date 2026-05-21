#!/usr/bin/env bash
# 用 marker 把 letters/*.pdf 转成 Markdown
# 1. 把 PDF 移到 letters/original_pdf/
# 2. marker batch 跑出 letters/_md_tmp/<name>/<name>.md
# 3. 把生成的 .md 平铺移到 letters/<name>.md
#
# CPU 加速：
#   - OMP_NUM_THREADS=16 配合 --workers 4，覆盖 64 物理核
#   - PyTorch 2.12 自带 mkldnn / AMX bf16 内核，自动启用
#   - --disable_image_extraction 跳过图片，纯文本快
#
# 依赖：marker-pdf 已装，模型已缓存 ~/.cache/datalab/models/

set -euo pipefail

ROOT="/home/dtl/projects/data/BuffettLetters"
LETTERS="$ROOT/letters"
ORIG="$LETTERS/original_pdf"
TMP="$LETTERS/_md_tmp"

cd "$ROOT"
mkdir -p "$ORIG" "$TMP"

# 1. 把所有 PDF 移到 original_pdf（如还没移）
moved=0
for f in "$LETTERS"/*.pdf; do
    [[ -e "$f" ]] || continue
    mv "$f" "$ORIG/"
    moved=$((moved+1))
done
echo "[1/3] 移动 $moved 份 PDF 到 $ORIG"

# 2. marker 批跑
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-16}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-16}"
export TOKENIZERS_PARALLELISM=false

WORKERS="${WORKERS:-4}"
echo "[2/3] marker --workers $WORKERS（每 worker $OMP_NUM_THREADS 线程）"

time marker "$ORIG" \
    --workers "$WORKERS" \
    --output_dir "$TMP" \
    --output_format markdown \
    --disable_image_extraction \
    --skip_existing

# 3. 把每份 PDF 输出目录里的 .md 平铺到 letters/
echo "[3/3] 整理输出"
for d in "$TMP"/*/; do
    name=$(basename "$d")
    md="$d/$name.md"
    if [[ -f "$md" ]]; then
        mv "$md" "$LETTERS/$name.md"
        echo "  ✓ $name.md"
    else
        echo "  ✗ 缺失: $md"
    fi
done

# 清理临时目录
rm -rf "$TMP"
echo "完成。letters/ 下 *.md 与 letters/original_pdf/*.pdf 并列。"
