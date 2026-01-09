#!/usr/bin/env python3
"""
YouTube Audio Library Bulk Downloader
Downloads ALL tracks and organizes by their metadata
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime
import logging
import re
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BulkAudioDownloader:
    def __init__(self):
        self.api_url = "https://thibaultjanbeyer.github.io/YouTube-Free-Audio-Library-API/api.json"
        self.base_dir = Path("youtube_music")
        
        # Create main directory
        self.base_dir.mkdir(exist_ok=True)
        
        # Load download history
        self.history_file = self.base_dir / "download_history.json"
        self.downloaded_ids = self.load_downloaded_ids()
        
        logger.info(f"Already downloaded: {len(self.downloaded_ids)} tracks")
    
    def load_downloaded_ids(self):
        """Load IDs of already downloaded tracks"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('downloaded_ids', []))
            except:
                return set()
        return set()
    
    def save_downloaded_id(self, track_id):
        """Save track ID to history"""
        self.downloaded_ids.add(track_id)
        
        data = {
            'downloaded_ids': list(self.downloaded_ids),
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def get_safe_filename(self, artist, title, track_id):
        """Create safe filename"""
        # Clean special characters
        clean_artist = re.sub(r'[<>:"/\\|?*]', '_', artist)[:50]
        clean_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
        
        # Remove extra spaces
        clean_artist = ' '.join(clean_artist.split())
        clean_title = ' '.join(clean_title.split())
        
        # Create filename
        if clean_artist and clean_artist != 'Unknown':
            filename = f"{clean_artist} - {clean_title}.mp3"
        else:
            filename = f"{clean_title}.mp3"
        
        return filename
    
    def create_category_folder(self, category):
        """Create folder for category if needed"""
        if not category:
            category = "uncategorized"
        
        # Clean category name
        category = re.sub(r'[<>:"/\\|?*]', '_', category)
        category = category.replace(' ', '_').lower()
        
        folder = self.base_dir / category
        folder.mkdir(exist_ok=True)
        
        return folder
    
    def download_track(self, track, index, total):
        """Download single track"""
        try:
            track_id = track.get('id', '')
            if not track_id:
                logger.warning(f"No ID for track")
                return False
            
            # Skip if already downloaded
            if track_id in self.downloaded_ids:
                logger.debug(f"Already downloaded: {track.get('name', 'Unknown')}")
                return True
            
            # Get track info
            track_name = track.get('name', 'Unknown Track')
            artist = track.get('artist', 'Unknown Artist')
            genre = track.get('genre', '')
            mood = track.get('mood', '')
            
            # Create category from genre or mood
            category = genre if genre else mood
            if not category:
                category = "uncategorized"
            
            # Create folder and filename
            category_folder = self.create_category_folder(category)
            filename = self.get_safe_filename(artist, track_name, track_id)
            filepath = category_folder / filename
            
            # Skip if file exists
            if filepath.exists():
                file_size = filepath.stat().st_size / (1024 * 1024)
                logger.info(f"✓ File exists: {filename} ({file_size:.1f} MB)")
                self.save_downloaded_id(track_id)
                return True
            
            # Download URL
            download_url = f"https://drive.google.com/uc?export=download&id={track_id}"
            
            logger.info(f"↓ [{index}/{total}] {artist} - {track_name}")
            
            # Download with session
            session = requests.Session()
            response = session.get(download_url, stream=True, timeout=60)
            
            # Handle Google Drive confirmation
            for key, value in response.cookies.items():
                if 'download_warning' in key:
                    confirm_url = f"{download_url}&confirm={value}"
                    response = session.get(confirm_url, stream=True)
                    break
            
            # Get file size for progress
            total_size = int(response.headers.get('content-length', 0))
            
            # Download file
            with open(filepath, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    # Download with simple progress
                    chunk_size = 8192
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
            
            # Verify download
            if filepath.exists() and filepath.stat().st_size > 0:
                file_size = filepath.stat().st_size / (1024 * 1024)
                logger.info(f"✅ Downloaded: {filename} ({file_size:.1f} MB)")
                
                # Save metadata
                self.save_track_metadata(track, filepath)
                
                # Mark as downloaded
                self.save_downloaded_id(track_id)
                
                return True
            else:
                logger.error(f"❌ Download failed: {track_name}")
                if filepath.exists():
                    filepath.unlink()  # Delete empty file
                return False
            
        except Exception as e:
            logger.error(f"Error downloading track: {e}")
            return False
    
    def save_track_metadata(self, track, filepath):
        """Save track metadata as JSON"""
        try:
            metadata = {
                'id': track.get('id', ''),
                'name': track.get('name', ''),
                'artist': track.get('artist', ''),
                'genre': track.get('genre', ''),
                'mood': track.get('mood', ''),
                'duration': track.get('duration', ''),
                'bpm': track.get('bpm', ''),
                'download_date': datetime.now().isoformat(),
                'file_size': filepath.stat().st_size,
                'file_path': str(filepath)
            }
            
            metadata_file = filepath.with_suffix('.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.debug(f"Could not save metadata: {e}")
    
    def fetch_all_tracks(self):
        """Fetch all tracks from API"""
        try:
            logger.info("Fetching audio library...")
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            tracks = data.get('all', [])
            
            logger.info(f"Total tracks available: {len(tracks)}")
            return tracks
            
        except Exception as e:
            logger.error(f"Error fetching tracks: {e}")
            return []
    
    def download_batch(self, tracks, batch_size=100, start_from=0):
        """Download tracks in batches"""
        total = len(tracks)
        
        if start_from > 0:
            tracks = tracks[start_from:]
            logger.info(f"Resuming from track {start_from + 1}")
        
        successful = 0
        failed = 0
        
        for i, track in enumerate(tracks, start_from + 1):
            if self.download_track(track, i, total):
                successful += 1
            else:
                failed += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
            # Print progress every 10 tracks
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{total} ({successful}✓ {failed}✗)")
        
        return successful, failed
    
    def print_summary(self):
        """Print download summary"""
        print("\n" + "="*60)
        print("DOWNLOAD SUMMARY")
        print("="*60)
        
        # Count tracks in each category
        categories = {}
        total_tracks = 0
        
        for item in self.base_dir.iterdir():
            if item.is_dir():
                mp3_files = list(item.glob("*.mp3"))
                if mp3_files:
                    categories[item.name] = len(mp3_files)
                    total_tracks += len(mp3_files)
        
        # Print categories
        for category, count in sorted(categories.items()):
            print(f"{category.upper():20} {count:4} tracks")
        
        print("-"*60)
        print(f"{'TOTAL':20} {total_tracks:4} tracks")
        print(f"\nLocation: {self.base_dir.absolute()}")
        
        # Show sample files
        print("\nSample files in first category:")
        first_category = list(categories.keys())[0] if categories else None
        if first_category:
            category_dir = self.base_dir / first_category
            files = list(category_dir.glob("*.mp3"))[:3]
            for file in files:
                print(f"  • {file.name}")
        
        print("="*60)
    
    def run(self, limit=None, resume=False):
        """Main download process"""
        print("="*60)
        print("YOUTUBE AUDIO BULK DOWNLOADER")
        print("Downloading ALL tracks • No filters")
        print("="*60)
        
        try:
            # Fetch all tracks
            all_tracks = self.fetch_all_tracks()
            if not all_tracks:
                logger.error("No tracks found!")
                return
            
            # Apply limit if specified
            if limit:
                all_tracks = all_tracks[:limit]
                logger.info(f"Limiting to {limit} tracks")
            
            # Check for resume
            start_from = 0
            if resume and self.history_file.exists():
                downloaded_count = len(self.downloaded_ids)
                start_from = downloaded_count
                logger.info(f"Resuming from track {start_from + 1}")
            
            # Calculate new tracks
            new_tracks = [t for t in all_tracks if t.get('id', '') not in self.downloaded_ids]
            
            if not new_tracks:
                print(f"\n✨ All {len(all_tracks)} tracks already downloaded!")
                self.print_summary()
                return
            
            print(f"\n📥 Ready to download {len(new_tracks)} new tracks")
            print("This will take a while. Go grab some coffee! ☕\n")
            
            time.sleep(2)  # Give user time to read
            
            # Start download
            successful, failed = self.download_batch(new_tracks)
            
            # Summary
            print("\n" + "="*60)
            print("DOWNLOAD COMPLETE")
            print("="*60)
            print(f"✅ Successful: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"📊 Success rate: {(successful/(successful+failed))*100:.1f}%" if (successful+failed) > 0 else "0%")
            
            self.print_summary()
            
            # Integration instructions
            print("\n🎵 READY FOR STREAMING!")
            print(f"\nCopy ALL audio files to stream folder:")
            print(f"  cp {self.base_dir}/*/*.mp3 assets/audio/")
            print(f"\nOr copy specific categories:")
            print(f"  cp {self.base_dir}/ambient/*.mp3 assets/audio/")
            print(f"  cp {self.base_dir}/cinematic/*.mp3 assets/audio/")
            print(f"  cp {self.base_dir}/relaxing/*.mp3 assets/audio/")
            
        except KeyboardInterrupt:
            print("\n⚠️ Download interrupted")
            self.print_summary()
        except Exception as e:
            logger.error(f"Error: {e}")

# ==================== SIMPLE DOWNLOAD SCRIPT ====================
def simple_download():
    """Simple one-command download"""
    print("="*60)
    print("SIMPLE YOUTUBE AUDIO DOWNLOADER")
    print("="*60)
    
    downloader = BulkAudioDownloader()
    
    print("\nOptions:")
    print("1. Download 50 tracks (quick test)")
    print("2. Download 200 tracks (good start)")
    print("3. Download 1000 tracks (large collection)")
    print("4. Download ALL tracks (5142+ tracks)")
    
    choice = input("\nChoose (1-4): ").strip()
    
    if choice == "1":
        downloader.run(limit=50)
    elif choice == "2":
        downloader.run(limit=200)
    elif choice == "3":
        downloader.run(limit=1000)
    elif choice == "4":
        downloader.run()
    else:
        print("Invalid choice. Downloading 100 tracks.")
        downloader.run(limit=100)

# ==================== CHECK & PREPARE ====================
def prepare_for_streaming():
    """Prepare downloaded audio for streaming"""
    base_dir = Path("youtube_music")
    stream_dir = Path("assets/audio")
    
    if not base_dir.exists():
        print("No audio downloaded yet!")
        return
    
    # Create stream directory
    stream_dir.mkdir(parents=True, exist_ok=True)
    
    # Count existing files
    existing_files = list(stream_dir.glob("*.mp3"))
    
    print("="*60)
    print("PREPARE FOR STREAMING")
    print("="*60)
    
    total_copied = 0
    for category_dir in base_dir.iterdir():
        if category_dir.is_dir():
            mp3_files = list(category_dir.glob("*.mp3"))
            if mp3_files:
                print(f"\n📁 {category_dir.name}: {len(mp3_files)} tracks")
                
                # Copy files
                copied = 0
                for mp3_file in mp3_files:
                    target_file = stream_dir / mp3_file.name
                    
                    # Skip if already exists
                    if target_file.exists():
                        continue
                    
                    # Copy file
                    import shutil
                    shutil.copy2(mp3_file, target_file)
                    copied += 1
                
                if copied > 0:
                    print(f"  → Copied {copied} new files")
                    total_copied += copied
                else:
                    print("  → All files already in stream folder")
    
    print(f"\n✅ Total new files copied: {total_copied}")
    print(f"📊 Total in stream folder: {len(list(stream_dir.glob('*.mp3')))}")
    print(f"📍 Location: {stream_dir.absolute()}")
    print("="*60)

# ==================== MAIN ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Audio Bulk Downloader")
    parser.add_argument("--simple", action="store_true", help="Simple download wizard")
    parser.add_argument("--limit", type=int, help="Limit number of tracks")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted download")
    parser.add_argument("--prepare", action="store_true", help="Prepare for streaming")
    
    args = parser.parse_args()
    
    if args.prepare:
        prepare_for_streaming()
    elif args.simple:
        simple_download()
    else:
        downloader = BulkAudioDownloader()
        downloader.run(limit=args.limit, resume=args.resume)