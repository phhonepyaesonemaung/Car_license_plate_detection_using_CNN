import cv2
import torch
import os
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import re
import numpy as np

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Load YOLOv5 plate detector
det_model = torch.hub.load('ultralytics/yolov5', 'custom', path='C:/Users/USER/Desktop/Car_license_plate_detection_using_CNN/backend/model/plate_detection.pt')

# Load TrOCR model and processor
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-printed')
model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-printed').to(device)

def clean_plate_string(plate_str):
    # Only keep alphanumeric characters
    return re.sub(r'[^A-Za-z0-9]', '', plate_str)

def recognize_plate_trocr(plate_crop):
    h, w = plate_crop.shape[:2]
    # Remove upper third (adjust as needed)
    main_plate_crop = plate_crop[int(h*0.33):, :]
    pil_img = Image.fromarray(cv2.cvtColor(main_plate_crop, cv2.COLOR_BGR2RGB))
    pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values.to(device)
    generated_ids = model.generate(pixel_values)
    plate_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return plate_text.strip()

def recognize_plate_trocr_ensemble(plate_crop, n=5):
    """
    Run TrOCR multiple times with slight augmentations and use majority voting for each character.
    """
    preds = []
    for _ in range(n):
        # Apply random brightness/contrast augmentation
        aug = plate_crop.copy().astype(np.float32)
        alpha = np.random.uniform(0.9, 1.1)  # contrast
        beta = np.random.uniform(-10, 10)    # brightness
        aug = np.clip(alpha * aug + beta, 0, 255).astype(np.uint8)

        pil_img = Image.fromarray(cv2.cvtColor(aug, cv2.COLOR_BGR2RGB))
        pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values.to(device)
        generated_ids = model.generate(pixel_values)
        plate_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        preds.append(re.sub(r'[^A-Za-z0-9]', '', plate_text.strip()))

    # Majority voting per character position
    if not preds:
        return ""
    max_len = max(len(p) for p in preds)
    result = ""
    for i in range(max_len):
        chars = [p[i] for p in preds if len(p) > i]
        if chars:
            result += max(set(chars), key=chars.count)
    return result

def remove_white_border(plate_crop):
    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(255 - thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        x, y, w, h = cv2.boundingRect(contours[0])
        return plate_crop[y:y+h, x:x+w]
    return plate_crop

def process_plate_crop(plate_crop):
    # Remove white border
    plate_crop = remove_white_border(plate_crop)
    # Remove upper code (if needed)
    h, w = plate_crop.shape[:2]
    main_plate_crop = plate_crop[int(h*0.33):, :]
    return main_plate_crop


# New function for backend: process a single image file
def process_image_file(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Could not read {image_path}")
        return None
    results = det_model(img)
    # Find the best plate detection
    best_plate = None
    best_conf = 0
    for (*box, conf, cls) in results.xyxy[0]:
        if results.names[int(cls)] == 'plate' and conf > best_conf and conf >= 0.8:
            best_plate = box
            best_conf = conf
    if best_plate is not None:
        x1, y1, x2, y2 = map(int, best_plate)
        pad = -10
        h, w = img.shape[:2]
        x1_p = min(max(0, x1 - pad), w)
        y1_p = min(max(0, y1 - pad), h)
        x2_p = max(min(w, x2 + pad), 0)
        y2_p = max(min(h, y2 + pad), 0)
        plate_crop = img[y1_p:y2_p, x1_p:x2_p]
        plate_crop = remove_white_border(plate_crop)
        plate_text = recognize_plate_trocr(plate_crop)
        cleaned_plate_text = clean_plate_string(plate_text)
        final_plate_text = enforce_second_alpha(cleaned_plate_text)
        final_plate_text = enforce_plate_length(final_plate_text, length=6)
        return final_plate_text
    else:
        print("No plate detected with sufficient confidence.")
        return None

def enforce_second_alpha(plate_str):
    # Remove non-alphanumeric characters
    cleaned = re.sub(r'[^A-Za-z0-9]', '', plate_str)
    if len(cleaned) < 2:
        return cleaned  # Not enough characters to enforce
    # If the second character is not an alphabet, try to correct it
    if not cleaned[1].isalpha():
        # Replace with a placeholder or try to infer from common OCR confusions
        # Example: if it's a digit that looks like a letter, map it
        digit_to_alpha = {'0': 'D', '1': 'I', '2': 'Z', '5': 'S', '6': 'G', '8': 'B'}
        corrected = digit_to_alpha.get(cleaned[1], 'A')  # Default to 'A' if unknown
        cleaned = cleaned[0] + corrected + cleaned[2:]
    return cleaned

def enforce_plate_length(plate_str, length=6):
    # Remove non-alphanumeric characters
    cleaned = re.sub(r'[^A-Za-z0-9]', '', plate_str)
    # Only keep the first `length` characters
    return cleaned[:length]

if __name__ == "__main__":
    results = process_images("car_images", "plates_trocr")
    print("\nFinal Results:")
    for plate_img, plate_text in results.items():
        print(f"{plate_img}: {plate_text}")