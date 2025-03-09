#!/usr/bin/env python3
"""
データセットの可視化を実行するためのヘルパースクリプト。
src/visualization/dataset.py モジュールを直接呼び出します。
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.visualization.dataset import main as visualize_main

if __name__ == "__main__":
    # コマンドライン引数をそのままvisualize_mainに渡す
    sys.exit(visualize_main())