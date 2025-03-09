#!/usr/bin/env python3
"""
House Design AI エントリーポイント
このファイルはVertex AI環境でのフォールバックエントリーポイントとして機能し、
src.cliモジュールにリダイレクトします。
"""
import sys
from src.cli import main

if __name__ == "__main__":
    sys.exit(main()) 