"""
[已弃用] 模拟数据生成脚本 — 请改用 load_public_data.py

保留此文件仅供参考，不再作为项目默认数据入口。
"""

from __future__ import annotations

import warnings

warnings.warn(
    "generate_data.py 已弃用，请运行: python src/load_public_data.py",
    DeprecationWarning,
    stacklevel=1,
)

# 原实现保留在 git 历史中；如需模拟数据可恢复旧版本。

if __name__ == "__main__":
    print("此脚本已弃用。请运行: python src/load_public_data.py")
