import os
import shutil
from PIL import Image
from PIL.ExifTags import TAGS
from moviepy.editor import VideoFileClip
from datetime import datetime
import uuid
import imagehash
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_image_metadata(file_path):
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            if exif_data:
                exif = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
                date_taken = exif.get('DateTimeOriginal', 'Unknown')
                return date_taken
            else:
                return 'Unknown'
    except Exception as e:
        print(f"Error reading metadata for {file_path}: {e}")
        return 'Unknown'

def get_video_metadata(file_path):
    try:
        clip = VideoFileClip(file_path)
        creation_time = clip.reader.infos.get('creation_time', 'Unknown')
        if isinstance(creation_time, datetime):
            return creation_time.strftime('%Y:%m:%d %H:%M:%S')
        else:
            return 'Unknown'
    except Exception as e:
        print(f"Error reading metadata for {file_path}: {e}")
        return 'Unknown'

def process_file(file_path, ext, image_extensions, video_extensions, images_output_dir, videos_output_dir, image_hashes):
    try:
        if ext in image_extensions:
            date_taken = get_image_metadata(file_path)
            output_subdir = images_output_dir

            # Calculate image hash
            with Image.open(file_path) as img:
                img_hash = str(imagehash.average_hash(img))

            # Check for duplicates
            if img_hash in image_hashes:
                print(f"Duplicate image detected: {file_path} is a duplicate of {image_hashes[img_hash]}")
                duplicate_count = image_hashes[img_hash]['duplicate_count']
                image_hashes[img_hash]['duplicate_count'] += 1
                if date_taken != 'Unknown':
                    date_taken_formatted = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S').strftime('%Y-%m-%d')
                else:
                    date_taken_formatted = 'unknown'

                new_file_name = f"{date_taken_formatted}-{img_hash}_duplicate_{duplicate_count}{ext}"
                duplicate_file_path = os.path.join(output_subdir, new_file_name)
                shutil.copy2(file_path, duplicate_file_path)
                print(f"Duplicate copied to: {duplicate_file_path}")
                return

            image_hashes[img_hash] = {'file_path': file_path, 'duplicate_count': 1}

        elif ext in video_extensions:
            date_taken = get_video_metadata(file_path)  # Attempt to get video metadata
            output_subdir = videos_output_dir
        else:
            return

        unique_id = str(uuid.uuid4())
        if date_taken != 'Unknown':
            date_taken_formatted = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S').strftime('%Y-%m-%d')
        else:
            date_taken_formatted = 'unknown'

        if ext in image_extensions:
            new_file_name = f"{date_taken_formatted}-{img_hash}{ext}"
        elif ext in video_extensions:
            new_file_name = f"{date_taken_formatted}-{unique_id}{ext}"

        new_file_path = os.path.join(output_subdir, new_file_name)

        shutil.copy2(file_path, new_file_path)

        print(f"File: {os.path.basename(file_path)}, Date Taken: {date_taken}, Unique ID: {unique_id}, Copied to: {new_file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def process_files(root_dir, output_dir):
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv')

    images_output_dir = os.path.join(output_dir, 'images')
    videos_output_dir = os.path.join(output_dir, 'videos')

    os.makedirs(images_output_dir, exist_ok=True)
    os.makedirs(videos_output_dir, exist_ok=True)

    image_hashes = {}
    file_paths = []

    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(subdir, file)
            ext = os.path.splitext(file)[1].lower()
            file_paths.append((file_path, ext))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_file, file_path, ext, image_extensions, video_extensions, images_output_dir, videos_output_dir, image_hashes) for file_path, ext in file_paths]
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    root_directory = 'D:/input'  # Replace with your folder path
    output_directory = 'D:/output'  # Replace with your output folder path
    process_files(root_directory, output_directory)