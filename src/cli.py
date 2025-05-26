#!/usr/bin/env python3
"""
House Design AI プロジェクトのコマンドラインインターフェース
このモジュールは、トレーニング、推論、Vertex AI操作、間取り生成などのサブコマンドを提供します。
"""
import argparse
import logging
import sys
from typing import List, Optional

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("house-design-ai")


def setup_vertex_parser(subparsers):
    """Vertex AI関連の引数パーサーを設定"""
    parser = subparsers.add_parser("vertex", help="Vertex AI上でカスタムジョブを実行")

    # 基本設定
    parser.add_argument(
        "--project_id", type=str, default="yolov8environment", help="GCPプロジェクトID"
    )
    parser.add_argument(
        "--region", type=str, default="asia-northeast1", help="GCPリージョン"
    )
    parser.add_argument(
        "--job_name",
        type=str,
        default="yolo11-custom-training-job",
        help="Vertex AIジョブ名",
    )
    parser.add_argument(
        "--container_uri",
        type=str,
        default="asia-northeast1-docker.pkg.dev/yolov8environment/yolov8-repository/yolov11-training-image:v2",
        help="コンテナイメージURI",
    )
    parser.add_argument(
        "--service_account",
        type=str,
        default="yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com",
        help="サービスアカウント",
    )
    parser.add_argument(
        "--staging_bucket",
        type=str,
        default="gs://yolo-v11-training-staging",
        help="ステージングバケット (gs://から始まる)",
    )
    parser.add_argument(
        "--machine_type", type=str, default="n1-highmem-8", help="マシンタイプ"
    )
    parser.add_argument(
        "--accelerator_type",
        type=str,
        default="NVIDIA_TESLA_T4",
        help="アクセラレータタイプ (GPUなしの場合は 'none' を指定)",
    )
    parser.add_argument(
        "--accelerator_count", type=int, default=1, help="アクセラレータ数"
    )
    parser.add_argument(
        "--save_dir", type=str, help="結果保存ディレクトリ (指定しない場合は自動生成)"
    )

    # トレーニング用の引数 - デフォルト値を以前の設定に合わせて更新
    train_args = parser.add_argument_group(
        "トレーニング引数", "Vertex AIジョブに転送される引数"
    )
    train_args.add_argument(
        "--bucket_name",
        type=str,
        default="yolo-v11-training",
        help="データセット用GCSバケット名",
    )
    train_args.add_argument(
        "--model",
        type=str,
        default="gs://yolo-v11-training/runs/segment/train_20250311-143512/weights/best.pt",
        help="使用するYOLOモデル",
    )
    train_args.add_argument(
        "--epochs", type=int, default=600, help="トレーニングエポック数"
    )
    train_args.add_argument("--batch_size", type=int, default=16, help="バッチサイズ")
    train_args.add_argument("--imgsz", type=int, default=640, help="入力画像サイズ")
    train_args.add_argument(
        "--optimizer",
        type=str,
        default="SGD",  # 変更: Adam → SGD
        help="オプティマイザ (Adam, SGD)",
    )
    train_args.add_argument(
        "--lr0", type=float, default=0.005, help="初期学習率"  # 変更: 0.01 → 0.005
    )
    train_args.add_argument(
        "--upload_bucket",
        type=str,
        default="yolo-v11-training",
        help="モデルアップロード先GCSバケット",
    )
    train_args.add_argument(
        "--upload_dir",
        type=str,
        default="trained_models",
        help="アップロード先ディレクトリ",
    )
    train_args.add_argument(
        "--iou_threshold",
        type=float,
        default=0.65,  # 変更: 0.7 → 0.65
        help="IoUしきい値",
    )
    train_args.add_argument(
        "--conf_threshold",
        type=float,
        default=0.2,  # 変更: 0.25 → 0.2
        help="信頼度しきい値",
    )
    train_args.add_argument(
        "--rect",
        action="store_true",
        default=True,  # 変更: default=True を追加
        help="矩形トレーニングを有効化",
    )
    train_args.add_argument(
        "--cos_lr",
        action="store_true",
        default=True,  # 変更: default=True を追加
        help="コサイン学習率スケジューラを使用",
    )
    train_args.add_argument(
        "--mosaic", type=float, default=1.0, help="モザイク拡張確率"
    )
    train_args.add_argument(
        "--degrees", type=float, default=10.0, help="画像回転角度"  # 変更: 0.0 → 10.0
    )
    train_args.add_argument(
        "--scale", type=float, default=0.6, help="画像スケール拡張"  # 変更: 0.5 → 0.6
    )
    train_args.add_argument(
        "--single_cls", action="store_true", help="すべてのクラスを単一クラスとして扱う"
    )

    return parser


def setup_train_parser(subparsers):
    """トレーニング関連の引数パーサーを設定"""
    parser = subparsers.add_parser("train", help="YOLOv11モデルをローカルでトレーニング")

    # 基本パラメータ
    parser.add_argument(
        "--model",
        type=str,
        default="gs://yolo-v11-training/runs/segment/train_20250311-143512/weights/best.pt",
        help="ベースYOLOモデル (例: yolo11n-seg.pt, yolo11s-seg.pt)",
    )
    parser.add_argument(
        "--epochs", type=int, default=100, help="トレーニングエポック数"
    )
    parser.add_argument("--batch_size", type=int, default=16, help="バッチサイズ")
    parser.add_argument("--imgsz", type=int, default=640, help="入力画像サイズ")
    parser.add_argument(
        "--data_yaml",
        type=str,
        default="/app/config/data.yaml",
        help="data.yamlファイルのパス",
    )

    # ローカル実行用パラメータ
    parser.add_argument(
        "--train_dir",
        type=str,
        default="/app/house/train",
        help="トレーニングデータディレクトリのローカルパス",
    )
    parser.add_argument(
        "--val_dir",
        type=str,
        default="/app/house/val",
        help="検証データディレクトリのローカルパス",
    )

    # GCS/Vertex AI用パラメータ
    parser.add_argument("--bucket_name", type=str, help="GCSバケット名")
    parser.add_argument(
        "--optimizer",
        type=str,
        default="Adam",
        help="最適化アルゴリズム (Adam, SGD, etc.)",
    )
    parser.add_argument("--lr0", type=float, default=0.01, help="初期学習率")
    parser.add_argument(
        "--upload_bucket", type=str, help="モデルをアップロードするGCSバケット"
    )
    parser.add_argument(
        "--upload_dir", type=str, help="モデルをアップロードするGCSディレクトリ"
    )
    parser.add_argument(
        "--iou_threshold", type=float, default=0.7, help="IoUのしきい値"
    )
    parser.add_argument(
        "--conf_threshold", type=float, default=0.25, help="信頼度のしきい値"
    )
    parser.add_argument("--rect", action="store_true", help="矩形トレーニングを有効化")
    parser.add_argument(
        "--cos_lr", action="store_true", help="コサイン学習率スケジューラを有効化"
    )
    parser.add_argument(
        "--mosaic", type=float, default=1.0, help="モザイクデータ拡張の確率"
    )
    parser.add_argument(
        "--degrees", type=float, default=0.0, help="回転データ拡張の最大角度"
    )
    parser.add_argument(
        "--scale", type=float, default=0.5, help="スケールデータ拡張の範囲"
    )
    parser.add_argument("--save_dir", type=str, help="結果を保存するディレクトリ")
    parser.add_argument(
        "--single_cls", action="store_true", help="すべてのクラスを単一クラスとして扱う"
    )

    return parser


def setup_app_parser(subparsers):
    """Streamlitアプリ関連の引数パーサーを設定"""
    parser = subparsers.add_parser("app", help="Streamlitアプリを起動")

    parser.add_argument(
        "--port", type=int, default=8501, help="Streamlitサーバーポート"
    )
    parser.add_argument(
        "--model_path",
        type=str,
        help="使用するモデルパス (指定しない場合はGCSから取得)",
    )

    return parser


def setup_inference_parser(subparsers):
    """推論関連の引数パーサーを設定"""
    parser = subparsers.add_parser("inference", help="YOLOモデルを使って推論実行")

    parser.add_argument(
        "--model_path", type=str, required=True, help="モデルファイルのパス"
    )
    parser.add_argument("--image_path", type=str, help="推論する画像ファイルのパス")
    parser.add_argument("--image_dir", type=str, help="推論する画像ディレクトリのパス")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="inference_results",
        help="推論結果を保存するディレクトリ",
    )

    return parser


def setup_visualize_parser(subparsers):
    """データセット可視化関連の引数パーサーを設定"""
    parser = subparsers.add_parser("visualize", help="YOLOデータセットを視覚化")

    parser.add_argument(
        "--data_yaml", type=str, default="data.yaml", help="data.yamlファイルのパス"
    )
    parser.add_argument("--num_samples", type=int, default=5, help="表示するサンプル数")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="visualization_results",
        help="出力ディレクトリ",
    )

    return parser


def setup_layout_parser(subparsers):
    """間取り生成関連の引数パーサーを設定"""
    parser = subparsers.add_parser("layout-generate", help="CP-SATを使用して3LDK間取りを生成")

    parser.add_argument(
        "--site-width", type=float, default=15.0, help="敷地の幅（m）"
    )
    parser.add_argument(
        "--site-height", type=float, default=12.0, help="敷地の高さ（m）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="layout_results",
        help="生成結果を保存するディレクトリ",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        default=True,
        help="生成された間取りを視覚化する",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="ソルバーのタイムアウト（秒）",
    )

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """メインエントリポイント"""
    parser = argparse.ArgumentParser(
        description="House Design AI CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="詳細ログの表示レベル (-v, -vv, -vvvなど)",
    )

    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

    # サブコマンドパーサーの設定
    setup_vertex_parser(subparsers)
    setup_train_parser(subparsers)
    setup_app_parser(subparsers)
    setup_inference_parser(subparsers)
    setup_visualize_parser(subparsers)
    setup_layout_parser(subparsers)

    parsed_args = parser.parse_args(args)

    # コマンドが指定されていない場合はヘルプを表示
    if not parsed_args.command:
        parser.print_help()
        return 1

    # ログレベルの設定
    if parsed_args.verbose >= 3:
        logging.getLogger().setLevel(logging.DEBUG)
    elif parsed_args.verbose >= 2:
        logging.getLogger().setLevel(logging.INFO)
    elif parsed_args.verbose >= 1:
        logging.getLogger().setLevel(logging.WARNING)

    try:
        # Vertex AIコマンド
        if parsed_args.command == "vertex":
            from src.cloud.vertex import run_vertex_job

            # accelerator_typeが'none'の場合はNoneに変換
            accelerator_type = parsed_args.accelerator_type
            if accelerator_type and accelerator_type.lower() == "none":
                accelerator_type = None

            # トレーニング引数を構築
            training_args = []
            arg_names = [
                "bucket_name",
                "model",
                "epochs",
                "batch_size",
                "imgsz",
                "optimizer",
                "lr0",
                "upload_bucket",
                "upload_dir",
                "iou_threshold",
                "conf_threshold",
                "single_cls",
            ]

            # 基本的な引数を追加
            for name in arg_names:
                if (
                    hasattr(parsed_args, name)
                    and getattr(parsed_args, name) is not None
                ):
                    training_args.extend([f"--{name}", str(getattr(parsed_args, name))])

            # フラグ引数を追加
            flag_args = ["rect", "cos_lr"]
            for name in flag_args:
                if hasattr(parsed_args, name) and getattr(parsed_args, name):
                    training_args.append(f"--{name}")

            # 数値引数を追加
            float_args = ["mosaic", "degrees", "scale"]
            for name in float_args:
                if (
                    hasattr(parsed_args, name)
                    and getattr(parsed_args, name) is not None
                ):
                    training_args.extend([f"--{name}", str(getattr(parsed_args, name))])

            # 引数のデバッグログを追加
            args_str = " ".join(training_args)
            logger.info(f"Vertex AIジョブに渡される引数: {args_str}")

            # ジョブを実行
            run_vertex_job(
                project_id=parsed_args.project_id,
                region=parsed_args.region,
                job_name=parsed_args.job_name,
                container_image_uri=parsed_args.container_uri,
                service_account=parsed_args.service_account,
                staging_bucket=parsed_args.staging_bucket,
                machine_type=parsed_args.machine_type,
                accelerator_type=accelerator_type,
                accelerator_count=parsed_args.accelerator_count,
                args=training_args,
            )

            print(f"Vertex AI ジョブ '{parsed_args.job_name}' が開始されました。")
            print("ジョブの進行状況は Google Cloud Console で確認できます。")
            return 0

        # Streamlitアプリ起動コマンド
        elif parsed_args.command == "app":
            # モデルパスを環境変数に設定（Streamlitアプリで使用）
            import os
            if parsed_args.model_path:
                os.environ["YOLO_MODEL_PATH"] = parsed_args.model_path

            # Streamlitをサブプロセスとして起動
            import subprocess

            streamlit_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "streamlit",
                "app.py",
            )

            cmd = [
                "streamlit",
                "run",
                streamlit_path,
                "--server.port",
                str(parsed_args.port),
            ]

            print(f"Streamlitアプリを起動: {' '.join(cmd)}")
            return subprocess.call(cmd)

        # トレーニングコマンド
        elif parsed_args.command == "train":
            from src.train import train_model

            return train_model(parsed_args)

        # 推論コマンド
        elif parsed_args.command == "inference":
            from src.inference import run_inference

            return run_inference(parsed_args)

        # 可視化コマンド
        elif parsed_args.command == "visualize":
            from src.visualization.dataset import visualize_dataset

            success = visualize_dataset(
                parsed_args.data_yaml, parsed_args.num_samples, parsed_args.output_dir
            )
            return 0 if success else 1
            
        elif parsed_args.command == "layout-generate":
            from src.optimization.cp_sat_solver import generate_3ldk_layout
            import os
            
            if not os.path.exists(parsed_args.output_dir):
                os.makedirs(parsed_args.output_dir)
                
            result = generate_3ldk_layout(
                site_width=parsed_args.site_width,
                site_height=parsed_args.site_height,
                output_dir=parsed_args.output_dir,
                timeout_sec=parsed_args.timeout
            )
            
            if result:
                print(f"間取り生成に成功しました: 総面積 {result.total_area:.1f}m²")
                print(f"結果は {parsed_args.output_dir} に保存されました")
                return 0
            else:
                print("間取り生成に失敗しました")
                return 1

        else:
            print(f"未実装のコマンド: {parsed_args.command}")
            return 1

    except Exception as e:
        logger.error(f"コマンド実行中にエラーが発生しました: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
