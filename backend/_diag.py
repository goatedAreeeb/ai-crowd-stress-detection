import traceback, os, sys

sys.stdout = open("_error_log.txt", "w", encoding="utf-8")
sys.stderr = sys.stdout

try:
    from ultralytics import YOLO
    data_path = os.path.abspath("security_dataset/data.yaml")
    print("DATA_PATH:", data_path)
    print("EXISTS:", os.path.exists(data_path))
    
    # Read yaml to verify
    with open(data_path, "r") as f:
        print("YAML CONTENT:")
        print(f.read())
    
    m = YOLO("yolov8m.pt")
    m.train(data=data_path, epochs=1, imgsz=640, batch=2, device="cpu", workers=0)
    print("SUCCESS")
except Exception as e:
    traceback.print_exc()
    print("ERROR:", str(e)[:1000])

sys.stdout.close()
