"""
YOLOv8データセットの可視化モジュール。
データセット内の画像とアノテーションを視覚的に確認するための機能を提供します。
"""
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import yaml
import argparse
import random
import logging
from typing import List, Dict, Any, Union, Optional, Tuple

# ロギング設定
logger = logging.getLogger(__name__)

def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    YAMLファイルを読み込みます。
    
    Args:
        file_path: YAMLファイルのパス
        
    Returns:
        YAMLの内容を表す辞書
    """
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"YAMLファイルの読み込みに失敗しました: {e}")
        return {}

def plot_one_box(
    x: List[float], 
    img: np.ndarray, 
    color: Optional[List[int]] = None, 
    label: Optional[str] = None, 
    line_thickness: int = 3
) -> None:
    """
    画像上にバウンディングボックスを描画します。
    
    Args:
        x: [x1, y1, x2, y2] 形式のバウンディングボックス座標
        img: 描画対象の画像
        color: ボックスの色 (BGR形式)
        label: ボックスに表示するラベル
        line_thickness: 線の太さ
    """
    tl = line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1
    color = color or [random.randint(0, 255) for _ in range(3)]
    c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
    cv2.rectangle(img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
    if label:
        tf = max(tl - 1, 1)
        t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)
        cv2.putText(img, label, (c1[0], c1[1] - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)

def plot_segment(
    img: np.ndarray, 
    segments: List[List[float]], 
    color: Optional[List[int]] = None, 
    label: Optional[str] = None, 
    line_thickness: int = 3
) -> None:
    """
    画像上にセグメンテーションマスク（ポリゴン）を描画します。
    
    Args:
        img: 描画対象の画像
        segments: ポリゴンの頂点座標のリスト
        color: ポリゴンの色 (BGR形式)
        label: ポリゴンに表示するラベル
        line_thickness: 線の太さ
    """
    tl = line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1
    color = color or [np.random.randint(0, 255) for _ in range(3)]
    
    # ポリゴン座標をint32に変換
    points = np.array(segments, dtype=np.int32)
    
    # ポリゴンを描画
    cv2.polylines(img, [points], True, color, thickness=tl, lineType=cv2.LINE_AA)
    
    # ラベルを描画（ポリゴンの左上に配置）
    if label:
        tf = max(tl - 1, 1)
        x_min, y_min = np.min(points[:, 0]), np.min(points[:, 1])
        t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
        c1 = (int(x_min), int(y_min))
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)
        cv2.putText(img, label, (c1[0], c1[1] - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)

def visualize_dataset(
    data_yaml: str, 
    num_samples: int = 5, 
    output_dir: str = 'visualization_results',
    override_train_path: Optional[str] = None
) -> bool:
    """
    データセットの画像とアノテーションを視覚化します。
    
    Args:
        data_yaml: data.yamlファイルのパス
        num_samples: 視覚化するサンプル数
        output_dir: 出力ディレクトリ
        override_train_path: 設定ファイルのtrainパスを上書きする場合の値
        
    Returns:
        成功時はTrue、失敗時はFalse
    """
    try:
        # データ設定を読み込み
        data_config = load_yaml(data_yaml)
        if not data_config:
            logger.error(f"データ設定の読み込みに失敗しました: {data_yaml}")
            return False
            
        # override_train_pathが指定されている場合、trainパスを上書き
        if override_train_path:
            original_train = data_config.get('train', '')
            data_config['train'] = override_train_path
            logger.info(f"トレーニングパスを上書きしました: {original_train} -> {override_train_path}")
            
        class_names = data_config.get('names', [])
        if not class_names:
            logger.error("クラス名が設定されていません")
            return False
            
        logger.info(f"クラス名: {class_names}")
        
        # トレーニングデータディレクトリを取得
        train_dir = data_config.get('train', '')
        if isinstance(train_dir, list):
            train_dir = train_dir[0] if train_dir else ''
            
        if not train_dir:
            logger.error("トレーニングディレクトリが設定されていません")
            return False
            
        logger.info(f"設定されたトレーニングディレクトリ: {train_dir}")
        
        # 画像とラベルのディレクトリ構造を検出
        possible_img_dirs = [
            os.path.join(train_dir, 'images'),  # 標準的なYOLOv8構造
            train_dir,                           # 直接画像がある場合
        ]
        
        img_dir = None
        for dir_path in possible_img_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                img_dir = dir_path
                break
        
        if img_dir is None:
            logger.error(f"画像ディレクトリが見つかりません。次のパスを確認しました: {possible_img_dirs}")
            return False
        
        # 対応するラベルディレクトリを探す
        possible_label_dirs = [
            os.path.join(os.path.dirname(img_dir), 'labels'),  # 標準的なYOLOv8構造
            os.path.join(train_dir, 'labels'),                 # 別の一般的な構造
            os.path.join(os.path.dirname(train_dir), 'labels') # さらに別の可能性
        ]
        
        label_dir = None
        for dir_path in possible_label_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                label_dir = dir_path
                break
        
        if label_dir is None:
            logger.error(f"ラベルディレクトリが見つかりません。次のパスを確認しました: {possible_label_dirs}")
            return False
        
        logger.info(f"使用する画像ディレクトリ: {img_dir}")
        logger.info(f"使用するラベルディレクトリ: {label_dir}")
        
        # 出力ディレクトリを作成
        os.makedirs(output_dir, exist_ok=True)
        
        # 画像リストを取得
        img_files = [f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
        
        if not img_files:
            logger.error(f"{img_dir} ディレクトリに画像ファイルが見つかりません")
            return False
        
        # サンプル数を制限
        if num_samples > 0 and num_samples < len(img_files):
            img_files = img_files[:num_samples]
        
        processed_count = 0
        
        # 各画像とそのアノテーションを処理
        for img_file in img_files:
            img_path = os.path.join(img_dir, img_file)
            label_file = os.path.splitext(img_file)[0] + '.txt'
            label_path = os.path.join(label_dir, label_file)
            
            if not os.path.exists(label_path):
                logger.warning(f"ラベルファイルが見つかりません: {label_path}")
                continue
            
            # 画像を読み込み
            img = cv2.imread(img_path)
            if img is None:
                logger.warning(f"画像を読み込めませんでした: {img_path}")
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            h, w, _ = img.shape
            
            # アノテーションを読み込み
            with open(label_path, 'r') as f:
                lines = f.readlines()
            
            # 各アノテーションを処理
            for line in lines:
                line = line.strip().split()
                if len(line) < 5:  # 最小でもクラスIDとx,y,w,hが必要
                    continue
                    
                class_id = int(line[0])
                class_name = class_names[class_id] if class_id < len(class_names) else f"Unknown-{class_id}"
                
                # YOLOフォーマットの座標をピクセル座標に変換
                if len(line) == 5:  # バウンディングボックス形式
                    x_center, y_center, width, height = map(float, line[1:5])
                    x1 = int((x_center - width / 2) * w)
                    y1 = int((y_center - height / 2) * h)
                    x2 = int((x_center + width / 2) * w)
                    y2 = int((y_center + height / 2) * h)
                    plot_one_box([x1, y1, x2, y2], img, label=f"{class_name} (ID:{class_id})")
                else:  # セグメンテーション形式
                    # セグメントポイントをピクセル座標に変換
                    segments = []
                    for i in range(1, len(line), 2):
                        if i+1 < len(line):
                            x = float(line[i]) * w
                            y = float(line[i+1]) * h
                            segments.append([x, y])
                    
                    if segments:
                        plot_segment(img, segments, label=f"{class_name} (ID:{class_id})")
            
            # 可視化結果を保存
            plt.figure(figsize=(12, 8))
            plt.imshow(img)
            plt.title(f"Image: {img_file}")
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"vis_{os.path.splitext(img_file)[0]}.png"))
            plt.close()
            
            logger.info(f"画像を処理しました: {img_file}")
            processed_count += 1
        
        logger.info(f"合計 {processed_count} 枚の画像を処理しました")
        return True
        
    except Exception as e:
        logger.error(f"データセットの視覚化中にエラーが発生しました: {e}", exc_info=True)
        return False

def main() -> int:
    """
    コマンドラインからの実行用エントリーポイント
    
    Returns:
        成功時は0、失敗時は1
    """
    parser = argparse.ArgumentParser(description="YOLOv8データセットを視覚化")
    parser.add_argument("--data_yaml", type=str, default="data.yaml", help="data.yamlファイルのパス")
    parser.add_argument("--num_samples", type=int, default=5, help="表示するサンプル数")
    parser.add_argument("--output_dir", type=str, default="visualization_results", help="出力ディレクトリ")
    parser.add_argument("--override_train_path", type=str, help="データ設定のtrainパスを上書きする値")
    
    args = parser.parse_args()
    
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    success = visualize_dataset(
        args.data_yaml, 
        args.num_samples, 
        args.output_dir,
        args.override_train_path
    )
    
    if success:
        print(f"可視化結果は {args.output_dir} ディレクトリに保存されました")
        return 0
    else:
        print("データセットの視覚化に失敗しました")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())