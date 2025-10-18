import os
import shutil

# Remove memes.csv if it exists
csv_path = 'data/memes.csv'
if os.path.exists(csv_path):
    os.remove(csv_path)
    print(f"Deleted: {csv_path}")

# Remove all images in data/images
images_folder = 'data/images'
if os.path.exists(images_folder):
    num_images = 0
    for filename in os.listdir(images_folder):
        file_path = os.path.join(images_folder, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            num_images += 1
    print(f"Deleted {num_images} images from {images_folder}")

print("All meme data has been reset!")
