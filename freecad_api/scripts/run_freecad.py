import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    FreeCADを使用して3Dモデルを生成するメインスクリプト
    """
    logger.info("FreeCAD CLIスクリプトを開始します")
    
    import FreeCAD
    import Part
    
    doc = FreeCAD.newDocument("Example")
    
    box = Part.makeBox(10, 10, 10)
    
    obj = doc.addObject("Part::Feature", "Box")
    obj.Shape = box
    
    doc.recompute()
    
    output_dir = os.environ.get("OUTPUT_DIR", "/tmp")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "model.FCStd")
    doc.saveAs(output_file)
    
    logger.info(f"モデルを保存しました: {output_file}")
    
    bucket_name = os.environ.get("BUCKET_NAME")
    if bucket_name:
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob("models/model.FCStd")
            blob.upload_from_filename(output_file)
            logger.info(f"モデルをCloud Storageにアップロードしました: gs://{bucket_name}/models/model.FCStd")
        except Exception as e:
            logger.error(f"Cloud Storageへのアップロードに失敗しました: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
