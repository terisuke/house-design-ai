#!/usr/bin/env python
"""
データセット分割・アップロードスクリプト

datasets/house ディレクトリ内のアノテーション済みファイルを
7:3の比率でトレーニング用と検証用に分割し、
Google Cloud Storage バケットにアップロードします。

使用方法:
    python scripts/split_and_upload_dataset.py

必要な環境変数:
    GOOGLE_APPLICATION_CREDENTIALS: GCP認証情報のパス
"""

import argparse
import logging
import os
import random
import shutil
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

GCS_BUCKET_NAME = "yolo-v11-training"
GCS_TRAIN_IMAGES_PATH = "house/train/images/"
GCS_TRAIN_LABELS_PATH = "house/train/labels/"
GCS_VAL_IMAGES_PATH = "house/val/images/"
GCS_VAL_LABELS_PATH = "house/val/labels/"

SOURCE_DIR = "datasets/house"
TRAIN_IMAGES_DIR = "datasets/house/train/images"
TRAIN_LABELS_DIR = "datasets/house/train/labels"
VAL_IMAGES_DIR = "datasets/house/val/images"
VAL_LABELS_DIR = "datasets/house/val/labels"

TRAIN_RATIO = 0.7
VAL_RATIO = 0.3


def get_image_and_label_files(
    source_dir: str
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    ソースディレクトリから画像ファイルとラベルファイルを取得します。

    Args:
        source_dir: ソースディレクトリのパス

    Returns:
        画像ファイルとラベルファイルの辞書のタプル
    """
    image_files = {}
    label_files = {}

    for filename in os.listdir(source_dir):
        file_path = os.path.join(source_dir, filename)

        if os.path.isdir(file_path):
            continue

        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            base_name = os.path.splitext(filename)[0]
            image_files[base_name] = file_path

        elif filename.lower().endswith('.txt'):
            base_name = os.path.splitext(filename)[0]
            label_files[base_name] = file_path

    return image_files, label_files


def split_dataset(
    image_files: Dict[str, str],
    label_files: Dict[str, str],
    train_ratio: float = 0.7
) -> Tuple[List[str], List[str]]:
    """
    データセットをトレーニング用と検証用に分割します。

    Args:
        image_files: 画像ファイルの辞書 {base_name: file_path}
        label_files: ラベルファイルの辞書 {base_name: file_path}
        train_ratio: トレーニングデータの比率

    Returns:
        トレーニング用と検証用のbase_nameリストのタプル
    """
    valid_base_names = [
        base_name for base_name in image_files.keys()
        if base_name in label_files
    ]

    random.shuffle(valid_base_names)

    split_idx = int(len(valid_base_names) * train_ratio)
    train_base_names = valid_base_names[:split_idx]
    val_base_names = valid_base_names[split_idx:]

    logger.info(f"データセット分割: 全{len(valid_base_names)}ファイル中、"
                f"トレーニング用{len(train_base_names)}ファイル、"
                f"検証用{len(val_base_names)}ファイル")

    return train_base_names, val_base_names


def prepare_local_directories() -> bool:
    """
    ローカルディレクトリを準備します。

    Returns:
        成功時はTrue、失敗時はFalse
    """
    try:
        dirs = [
            TRAIN_IMAGES_DIR, TRAIN_LABELS_DIR,
            VAL_IMAGES_DIR, VAL_LABELS_DIR
        ]
        for dir_path in dirs:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)

            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"ディレクトリを作成しました: {dir_path}")

        return True

    except Exception as e:
        logger.error(f"ディレクトリ準備エラー: {e}")
        return False


def copy_files_to_directories(
    train_base_names: List[str],
    val_base_names: List[str],
    image_files: Dict[str, str],
    label_files: Dict[str, str]
) -> bool:
    """
    ファイルを適切なディレクトリにコピーします。

    Args:
        train_base_names: トレーニング用のbase_nameリスト
        val_base_names: 検証用のbase_nameリスト
        image_files: 画像ファイルの辞書
        label_files: ラベルファイルの辞書

    Returns:
        成功時はTrue、失敗時はFalse
    """
    try:
        for base_name in train_base_names:
            if base_name in image_files:
                src_path = image_files[base_name]
                file_ext = os.path.splitext(src_path)[1]
                dst_path = os.path.join(
                    TRAIN_IMAGES_DIR, f"{base_name}{file_ext}")
                shutil.copy2(src_path, dst_path)

            if base_name in label_files:
                src_path = label_files[base_name]
                dst_path = os.path.join(TRAIN_LABELS_DIR, f"{base_name}.txt")
                shutil.copy2(src_path, dst_path)

        for base_name in val_base_names:
            if base_name in image_files:
                src_path = image_files[base_name]
                file_ext = os.path.splitext(src_path)[1]
                dst_path = os.path.join(
                    VAL_IMAGES_DIR, f"{base_name}{file_ext}")
                shutil.copy2(src_path, dst_path)

            if base_name in label_files:
                src_path = label_files[base_name]
                dst_path = os.path.join(VAL_LABELS_DIR, f"{base_name}.txt")
                shutil.copy2(src_path, dst_path)

        train_images = len(os.listdir(TRAIN_IMAGES_DIR))
        train_labels = len(os.listdir(TRAIN_LABELS_DIR))
        val_images = len(os.listdir(VAL_IMAGES_DIR))
        val_labels = len(os.listdir(VAL_LABELS_DIR))

        logger.info("ファイルコピー完了:")
        logger.info(f"  トレーニング画像: {train_images}ファイル")
        logger.info(f"  トレーニングラベル: {train_labels}ファイル")
        logger.info(f"  検証画像: {val_images}ファイル")
        logger.info(f"  検証ラベル: {val_labels}ファイル")

        return True

    except Exception as e:
        logger.error(f"ファイルコピーエラー: {e}")
        return False


def upload_to_gcs() -> bool:
    """
    分割したデータセットをGoogle Cloud Storageにアップロードします。

    Returns:
        成功時はTrue、失敗時はFalse
    """
    try:
        from src.cloud.storage import upload_directory_to_gcs

        logger.info(
            f"トレーニング画像をアップロード中: {TRAIN_IMAGES_DIR} -> "
            f"gs://{GCS_BUCKET_NAME}/{GCS_TRAIN_IMAGES_PATH}")
        train_images_result = upload_directory_to_gcs(
            bucket_name=GCS_BUCKET_NAME,
            source_directory=TRAIN_IMAGES_DIR,
            destination_prefix=GCS_TRAIN_IMAGES_PATH
        )

        logger.info(
            f"トレーニングラベルをアップロード中: {TRAIN_LABELS_DIR} -> "
            f"gs://{GCS_BUCKET_NAME}/{GCS_TRAIN_LABELS_PATH}")
        train_labels_result = upload_directory_to_gcs(
            bucket_name=GCS_BUCKET_NAME,
            source_directory=TRAIN_LABELS_DIR,
            destination_prefix=GCS_TRAIN_LABELS_PATH
        )

        logger.info(
            f"検証画像をアップロード中: {VAL_IMAGES_DIR} -> "
            f"gs://{GCS_BUCKET_NAME}/{GCS_VAL_IMAGES_PATH}")
        val_images_result = upload_directory_to_gcs(
            bucket_name=GCS_BUCKET_NAME,
            source_directory=VAL_IMAGES_DIR,
            destination_prefix=GCS_VAL_IMAGES_PATH
        )

        logger.info(
            f"検証ラベルをアップロード中: {VAL_LABELS_DIR} -> "
            f"gs://{GCS_BUCKET_NAME}/{GCS_VAL_LABELS_PATH}")
        val_labels_result = upload_directory_to_gcs(
            bucket_name=GCS_BUCKET_NAME,
            source_directory=VAL_LABELS_DIR,
            destination_prefix=GCS_VAL_LABELS_PATH
        )

        total_success = (
            train_images_result["success"] +
            train_labels_result["success"] +
            val_images_result["success"] +
            val_labels_result["success"]
        )

        total_error = (
            train_images_result["error"] +
            train_labels_result["error"] +
            val_images_result["error"] +
            val_labels_result["error"]
        )

        logger.info(
            f"アップロード完了: 成功={total_success}ファイル, "
            f"失敗={total_error}ファイル")

        return total_error == 0

    except Exception as e:
        logger.error(f"GCSアップロードエラー: {e}")
        return False


def update_data_yaml() -> bool:
    """
    data.yamlファイルを更新してGCSパスを設定します。

    Returns:
        成功時はTrue、失敗時はFalse
    """
    try:
        import yaml

        yaml_path = "config/data.yaml"

        with open(yaml_path, "r") as f:
            data_config = yaml.safe_load(f)

        data_config["train"] = (
            f"gs://{GCS_BUCKET_NAME}/{GCS_TRAIN_IMAGES_PATH}"
        )
        data_config["val"] = (
            f"gs://{GCS_BUCKET_NAME}/{GCS_VAL_IMAGES_PATH}"
        )

        with open(yaml_path, "w") as f:
            yaml.dump(data_config, f)

        logger.info(
            f"data.yamlを更新しました: "
            f"train={data_config['train']}, val={data_config['val']}")
        return True

    except Exception as e:
        logger.error(f"data.yaml更新エラー: {e}")
        return False


def main():
    """
    メイン処理
    """
    parser = argparse.ArgumentParser(
        description="データセット分割・アップロードスクリプト")
    parser.add_argument(
        "--source-dir", type=str, default=SOURCE_DIR,
        help="ソースディレクトリのパス")
    parser.add_argument(
        "--train-ratio", type=float, default=TRAIN_RATIO,
        help="トレーニングデータの比率")
    parser.add_argument(
        "--update-yaml", action="store_true",
        help="data.yamlファイルを更新するかどうか")

    args = parser.parse_args()

    logger.info("データセット分割・アップロード処理を開始")

    if not os.path.exists(args.source_dir):
        logger.error(f"ソースディレクトリが存在しません: {args.source_dir}")
        return 1

    image_files, label_files = get_image_and_label_files(args.source_dir)

    if not image_files:
        logger.error(f"画像ファイルが見つかりません: {args.source_dir}")
        return 1

    if not label_files:
        logger.error(f"ラベルファイルが見つかりません: {args.source_dir}")
        return 1

    train_base_names, val_base_names = split_dataset(
        image_files, label_files, args.train_ratio
    )

    if not prepare_local_directories():
        logger.error("ローカルディレクトリの準備に失敗しました")
        return 1

    if not copy_files_to_directories(
        train_base_names, val_base_names, image_files, label_files
    ):
        logger.error("ファイルのコピーに失敗しました")
        return 1

    if not upload_to_gcs():
        logger.error("GCSへのアップロードに失敗しました")
        return 1

    if args.update_yaml:
        if not update_data_yaml():
            logger.error("data.yamlの更新に失敗しました")
            return 1

    logger.info("データセット分割・アップロード処理が完了しました")
    return 0


if __name__ == "__main__":
    exit_code = main()
    import sys
    sys.exit(exit_code)
