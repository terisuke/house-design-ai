"""
YOLOv8セグメンテーションモデルのトレーニングモジュール。
ローカル環境でのトレーニングを担当します。
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
import argparse

# ロギング設定
logger = logging.getLogger(__name__)


def update_data_yaml(
    yaml_path: str,
    train_dir: str,
    val_dir: str
) -> bool:
    """
    data.yamlファイルを更新してトレーニング・検証データのパスを設定します。
    
    Args:
        yaml_path: data.yamlファイルのパス
        train_dir: トレーニングデータディレクトリのパス
        val_dir: 検証データディレクトリのパス
        
    Returns:
        更新成功時はTrue、失敗時はFalse
    """
    try:
        # YAMLファイルを読み込み
        with open(yaml_path, 'r') as f:
            data_config = yaml.safe_load(f)
        
        # データパスを更新
        data_config['train'] = train_dir
        data_config['val'] = val_dir
        
        # 更新したYAMLを書き込み
        with open(yaml_path, 'w') as f:
            yaml.dump(data_config, f)
        
        logger.info(f"data.yamlを更新しました: train={train_dir}, val={val_dir}")
        return True
        
    except Exception as e:
        logger.error(f"data.yaml更新エラー: {e}")
        return False


def train_model(args: argparse.Namespace) -> int:
    """
    YOLOv8セグメンテーションモデルをトレーニングします。
    
    Args:
        args: コマンドライン引数
        
    Returns:
        成功時は0、失敗時は1
    """
    try:
        # データ設定ファイルの更新
        if not update_data_yaml(args.data_yaml, args.train_dir, args.val_dir):
            logger.error("data.yamlの更新に失敗しました")
            return 1
        
        # モデル名の標準化（セグメンテーションモデルであることを確認）
        model_path = args.model
        if not model_path.endswith("-seg.pt"):
            base_name = model_path.replace(".pt", "")
            model_path = f"{base_name}-seg.pt"
        
        # モデルのインポート
        try:
            from ultralytics import YOLO
        except ImportError:
            logger.error("ultralyticsパッケージがインストールされていません")
            return 1
        
        # モデルのロード
        logger.info(f"モデルをロード中: {model_path}")
        model = YOLO(model_path)
        
        # トレーニングパラメータの設定
        train_params = {
            'data': args.data_yaml,
            'epochs': args.epochs,
            'batch': args.batch_size,
            'imgsz': args.imgsz,
            'exist_ok': True,  # 既存のトレーニング結果を上書き
        }
        
        # トレーニングの実行
        logger.info(f"トレーニングを開始: {args.epochs}エポック, バッチサイズ={args.batch_size}")
        results = model.train(**train_params)
        
        # トレーニング結果のロギング
        best_fitness = results.fitness
        logger.info(f"トレーニング完了: best fitness={best_fitness}")
        
        # 最良のモデルのパスを表示
        best_model_path = os.path.join(model.trainer.save_dir, "weights", "best.pt")
        if os.path.exists(best_model_path):
            logger.info(f"最良のモデルを保存: {best_model_path}")
            print(f"トレーニングが完了しました。最良のモデル: {best_model_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"トレーニングエラー: {e}", exc_info=True)
        return 1


# コマンドライン実行用
if __name__ == "__main__":
    # 引数パーサーの設定
    parser = argparse.ArgumentParser(description="YOLOv8セグメンテーションモデルのトレーニング")
    
    parser.add_argument("--model", type=str, default="yolov8m-seg.pt",
                      help="ベースYOLOv8モデル")
    parser.add_argument("--epochs", type=int, default=100,
                      help="トレーニングエポック数")
    parser.add_argument("--batch_size", type=int, default=16,
                      help="バッチサイズ")
    parser.add_argument("--imgsz", type=int, default=640,
                      help="入力画像サイズ")
    parser.add_argument("--data_yaml", type=str, default="config/data.yaml",
                      help="data.yamlファイルのパス")
    parser.add_argument("--train_dir", type=str, default="datasets/house/train",
                      help="トレーニングデータディレクトリのパス")
    parser.add_argument("--val_dir", type=str, default="datasets/house/val",
                      help="検証データディレクトリのパス")
    
    args = parser.parse_args()
    
    # トレーニングの実行
    exit_code = train_model(args)
    import sys
    sys.exit(exit_code)