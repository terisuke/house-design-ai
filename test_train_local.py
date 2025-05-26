#!/usr/bin/env python3
"""
ローカルでトレーニングスクリプトの初期化部分をテストするスクリプト
"""

import sys
import os

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.train import train_model
import argparse

# テスト用の引数を作成
args = argparse.Namespace(
    model="yolo11n-seg.pt",  # ローカルモデルを使用
    epochs=1,  # 短いテスト
    batch_size=1,
    imgsz=416,
    data_yaml="config/data.yaml",  # ローカルパス
    train_dir="house/train",  # ローカルパス
    val_dir="house/val",  # ローカルパス
    optimizer="AdamW",
    lr0=0.001,
    iou_threshold=0.5,
    conf_threshold=0.25,
    rect=True,
    cos_lr=True,
    mosaic=1.0,
    degrees=0.0,
    scale=0.5,
    bucket_name=None,  # GCSを使わない
    upload_bucket=None,
    save_dir="test_runs/train"
)

print("Testing train script initialization...")
print(f"Working directory: {os.getcwd()}")
print(f"Data yaml exists: {os.path.exists(args.data_yaml)}")

# このテストはモデルのロードまでしか行わない
# 実際のトレーニングは行わない
print("\nThis is a dry run test - not performing actual training")
print("To run actual training, use the build_and_run_vertex_training.sh script")

# Run initialization test with minimal epochs
try:
    print("\nTesting train_model initialization...")
    # Set epochs to 0 for dry run
    args.epochs = 0
    train_model(args)
    print("Initialization test completed successfully")
except Exception as e:
    print(f"Initialization test failed: {e}")
    sys.exit(1)