#!/usr/bin/env bash
# marker 批处理完成后整理输出：
#   letters/_md_tmp/<year>/<year>.md  →  letters/<year>.md
#   清理 _md_tmp/ 临时目录

set -euo pipefail

ROOT="/home/dtl/projects/data/BuffettLetters"
LETTERS="$ROOT/letters"
TMP="$LETTERS/_md_tmp"

cd "$ROOT"

if [[ ! -d "$TMP" ]]; then
    echo "$TMP 不存在，无需整理"
    exit 0
fi

ok=0
miss=0
for d in "$TMP"/*/; do
    name=$(basename "$d")
    md="$d/$name.md"
    if [[ -f "$md" ]]; then
        mv "$md" "$LETTERS/$name.md"
        ok=$((ok+1))
        echo "  ✓ $name.md ($(wc -c < "$LETTERS/$name.md") 字节)"
    else
        echo "  ✗ 缺失: $md"
        miss=$((miss+1))
    fi
done

# 清理 marker 输出的元数据 + 空目录
rm -rf "$TMP"

echo "完成。整理 $ok 份，缺失 $miss 份。"
echo "letters/ 主目录 *.md 数量: $(ls $LETTERS/*.md 2>/dev/null | wc -l)"
echo "letters/original_pdf/ PDF 数量: $(ls $LETTERS/original_pdf/*.pdf 2>/dev/null | wc -l)"
