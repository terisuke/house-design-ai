"""������"""

import argparse
import logging
from pathlib import Path
from typing import Optional

from ultralytics import YOLO

logger = logging.getLogger(__name__)


def run_inference(args: argparse.Namespace) -> int:
    """�֒�LY�
    
    Args:
        args: ������p
        
    Returns:
        B����
    """
    try:
        # ������
        model = YOLO(args.model)
        
        # ;�ѹ�֗
        image_path = Path(args.image)
        if not image_path.exists():
            logger.error(f";�ա��L�dK�~[�: {image_path}")
            return 1
        
        # �֒�L
        results = model.predict(
            source=str(image_path),
            save=args.save,
            save_txt=args.save_txt,
            save_conf=args.save_conf,
            save_crop=args.save_crop,
            hide_labels=args.hide_labels,
            hide_conf=args.hide_conf,
            conf=args.conf,
            iou=args.iou,
            max_det=args.max_det,
            device=args.device,
            visualize=args.visualize,
            augment=args.augment,
            agnostic_nms=args.agnostic_nms,
            classes=args.classes,
            retina_masks=args.retina_masks,
            boxes=not args.no_boxes,
            show=args.show,
            line_width=args.line_width,
            imgsz=args.imgsz,
            project=args.project,
            name=args.name,
            exist_ok=args.exist_ok,
        )
        
        # P��h:
        for result in results:
            if hasattr(result, "boxes") and result.boxes is not None:
                logger.info(f"�U�_�ָ���p: {len(result.boxes)}")
            if hasattr(result, "masks") and result.masks is not None:
                logger.info(f"���������޹�p: {len(result.masks)}")
        
        logger.info("��L��W~W_")
        return 0
        
    except Exception as e:
        logger.error(f"��-k���LzW~W_: {e}")
        return 1