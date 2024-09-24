# Google Takeout Photo Extractor

## Overview

The Google Takeout Photo Extractor is a Python application designed to process and organize photos and videos extracted from Google Takeout. The application performs the following tasks:

1. **Extract Metadata**: Extracts the date taken for images and videos.
2. **Detect Duplicates**: Detects duplicate images using perceptual hashing.
3. **Organize Files**: Copies images and videos to separate directories (`images` and `videos`).
4. **Rename Files**: Renames files to a standardized format (`<date_taken>-<unique_id>.<ext>` for videos and `<date_taken>-<img_hash>.<ext>` for images).
5. **Handle Duplicates**: For duplicate images, appends `_duplicate_1`, `_duplicate_2`, etc., to the filename.
6. **Multi-threading**: Utilizes multi-threading to process files concurrently, with the maximum number of threads set to 50% of the available CPU cores.

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - `pillow`
  - `moviepy`
  - `imagehash`

You can install the required packages using pip:

```bash
pip install pillow moviepy imagehash
```

## How the Application Works

### 1. Metadata Extraction

- **Images**: The application uses the `PIL` library to extract EXIF metadata, specifically the `DateTimeOriginal` field, which contains the date the photo was taken.
- **Videos**: The application uses the `moviepy` library to extract the `creation_time` metadata, which contains the date the video was created.

### 2. Duplicate Detection

- **Images**: The application calculates a perceptual hash for each image using the `imagehash` library. If an image with the same hash is found, it is considered a duplicate.
- **Videos**: Videos do not have a perceptual hash, so they are identified by their unique ID.

### 3. File Organization

- **Directories**: The application creates two main directories: `images` and `videos`. Duplicate images are stored in a separate directory named after their hash value.
- **File Naming**:
  - **Images**: Files are renamed to `<date_taken>-<img_hash>.<ext>`. For duplicate images, the filename is appended with `_duplicate_1`, `_duplicate_2`, etc.
  - **Videos**: Files are renamed to `<date_taken>-<unique_id>.<ext>`.

### 4. Multi-threading

- The application uses the `concurrent.futures.ThreadPoolExecutor` to process files concurrently. The maximum number of threads is set to 50% of the available CPU cores to balance performance and system load.

## How to Run the Application

### 1. Prepare Your Environment

Ensure you have Python installed and the required packages:

```bash
pip install pillow moviepy imagehash
```

### 2. Download the Script

Save the following script as `google_takeout_photo_extractor.py`:

```python
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

    # Calculate 50% of available CPU cores
    max_workers = max(1, int(os.cpu_count() * 0.5))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_file, file_path, ext, image_extensions, video_extensions, images_output_dir, videos_output_dir, image_hashes) for file_path, ext in file_paths]
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    root_directory = '/path/to/your/folder'  # Replace with your folder path
    output_directory = '/path/to/output/folder'  # Replace with your output folder path
    process_files(root_directory, output_directory)
```

### 3. Run the Script

Navigate to the directory containing the script and run it using Python:

```bash
python google_takeout_photo_extractor.py
```

### 4. Input and Output Directories

- **Input Directory**: Replace `'/path/to/your/folder'` with the path to the directory containing the photos and videos extracted from Google Takeout.
- **Output Directory**: Replace `'/path/to/output/folder'` with the path where you want the organized photos and videos to be saved.

### 5. Review the Output

- The application will create two directories: `images` and `videos` in the specified output directory.
- Duplicate images will be stored in the `images` directory with filenames appended with `_duplicate_1`, `_duplicate_2`, etc.
- Videos will be stored in the `videos` directory with filenames formatted as `<date_taken>-<unique_id>.<ext>`.

## Conclusion

The Google Takeout Photo Extractor is a powerful tool for organizing and managing photos and videos extracted from Google Takeout. By leveraging multi-threading and perceptual hashing, it efficiently processes large datasets, ensuring that your media files are well-organized and duplicates are handled appropriately.