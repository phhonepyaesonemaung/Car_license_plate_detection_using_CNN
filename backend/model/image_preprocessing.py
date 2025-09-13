import cv2
import os
from glob import glob

def preprocess_images(input_dir, output_dir, gamma=0.7, clip_limit=2.2, tile_grid_size=(8,8)):
    os.makedirs(output_dir, exist_ok=True)
    for img_path in glob(os.path.join(input_dir, '*.jpg')):
        img = cv2.imread(img_path)
        if img is None:
            continue  # Skip unreadable files

        # Convert to LAB color space for better contrast enhancement
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        # Apply CLAHE to L-channel
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        img_clahe = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        # Apply gamma correction to control exposure
        img_float = img_clahe / 255.0
        img_gamma = cv2.pow(img_float, gamma)
        img_gamma = (img_gamma * 255).astype('uint8')

        # Save preprocessed image
        cv2.imwrite(os.path.join(output_dir, os.path.basename(img_path)), img_gamma)

# Define your sets
sets = ['train', 'valid', 'test']
base_dir = 'datasets'

for s in sets:
    input_dir = os.path.join(base_dir, s, 'images')
    output_dir = os.path.join(base_dir, s, 'images_preprocessed')
    preprocess_images(input_dir, output_dir)