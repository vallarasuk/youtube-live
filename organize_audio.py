#!/usr/bin/env python3
"""
Audio Organizer - Categorize downloaded tracks
"""

import os
import shutil
from pathlib import Path
import json
import re

def organize_audio():
    base_dir = Path("youtube_music")
    uncategorized_dir = base_dir / "uncategorized"
    
    if not uncategorized_dir.exists():
        print("❌ No uncategorized folder found!")
        return
    
    # Create category folders
    categories = {
        "ambient": ["ambient", "atmospheric", "space", "drone", "ethereal"],
        "calm": ["calm", "peaceful", "serene", "relaxing", "meditation"],
        "cinematic": ["cinematic", "epic", "drama", "emotional", "orchestral"],
        "electronic": ["electronic", "synth", "lofi", "chill", "downtempo"],
        "uplifting": ["uplifting", "inspiring", "hopeful", "positive", "motivational"],
        "acoustic": ["acoustic", "guitar", "piano", "strings", "instrumental"]
    }
    
    # Create category folders
    for category in categories.keys():
        (base_dir / category).mkdir(exist_ok=True)
    
    # Track statistics
    stats = {category: 0 for category in categories.keys()}
    stats["other"] = 0
    
    # Process each MP3 file
    mp3_files = list(uncategorized_dir.glob("*.mp3"))
    print(f"📊 Found {len(mp3_files)} tracks to organize")
    
    for mp3_file in mp3_files:
        try:
            # Look for corresponding JSON metadata
            json_file = mp3_file.with_suffix('.json')
            
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Get genre and mood
                genre = metadata.get('genre', '').lower()
                mood = metadata.get('mood', '').lower()
                name = metadata.get('name', '').lower()
                
                search_text = f"{genre} {mood} {name}"
                
                # Find matching category
                matched = False
                for category, keywords in categories.items():
                    for keyword in keywords:
                        if keyword in search_text:
                            target_dir = base_dir / category
                            # Move both MP3 and JSON
                            shutil.move(str(mp3_file), str(target_dir / mp3_file.name))
                            shutil.move(str(json_file), str(target_dir / json_file.name))
                            stats[category] += 1
                            matched = True
                            break
                    if matched:
                        break
                
                if not matched:
                    # Move to "other"
                    other_dir = base_dir / "other"
                    other_dir.mkdir(exist_ok=True)
                    shutil.move(str(mp3_file), str(other_dir / mp3_file.name))
                    shutil.move(str(json_file), str(other_dir / json_file.name))
                    stats["other"] += 1
            else:
                # No metadata, move to other
                other_dir = base_dir / "other"
                other_dir.mkdir(exist_ok=True)
                shutil.move(str(mp3_file), str(other_dir / mp3_file.name))
                stats["other"] += 1
                
        except Exception as e:
            print(f"⚠️ Error processing {mp3_file.name}: {e}")
    
    # Print statistics
    print("\n" + "="*60)
    print("ORGANIZATION COMPLETE")
    print("="*60)
    
    total_moved = 0
    for category, count in stats.items():
        if count > 0:
            print(f"{category.upper():15} {count:3} tracks")
            total_moved += count
    
    print("-"*60)
    print(f"{'TOTAL':15} {total_moved:3} tracks")
    
    # Remove empty uncategorized folder
    if uncategorized_dir.exists():
        try:
            uncategorized_dir.rmdir()
            print("🗑️ Removed empty uncategorized folder")
        except:
            print("📁 uncategorized folder not empty")
    
    # Create playlist files
    create_playlists(base_dir)
    
    print("="*60)

def create_playlists(base_dir):
    """Create M3U playlist files for each category"""
    print("\n🎵 Creating playlists...")
    
    for category_dir in base_dir.iterdir():
        if category_dir.is_dir() and category_dir.name != "uncategorized":
            mp3_files = list(category_dir.glob("*.mp3"))
            if mp3_files:
                playlist_file = base_dir / f"{category_dir.name}_playlist.m3u"
                
                with open(playlist_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {category_dir.name.upper()} Playlist\n")
                    f.write(f"# Generated from YouTube Audio Library\n\n")
                    
                    for mp3_file in sorted(mp3_files):
                        f.write(f"{mp3_file.name}\n")
                
                print(f"  ✓ {category_dir.name}: {len(mp3_files)} tracks")

def prepare_stream_folder():
    """Copy organized audio to stream folder"""
    base_dir = Path("youtube_music")
    stream_dir = Path("assets/audio")
    
    # Create stream directory
    stream_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear existing files (optional)
    for existing_file in stream_dir.glob("*.mp3"):
        existing_file.unlink()
    
    print(f"\n📁 Preparing stream folder: {stream_dir}")
    
    total_copied = 0
    for category_dir in base_dir.iterdir():
        if category_dir.is_dir() and category_dir.name != "uncategorized":
            mp3_files = list(category_dir.glob("*.mp3"))
            if mp3_files:
                print(f"  {category_dir.name}: {len(mp3_files)} tracks")
                
                for mp3_file in mp3_files:
                    shutil.copy2(mp3_file, stream_dir / mp3_file.name)
                    total_copied += 1
    
    print(f"\n✅ Copied {total_copied} tracks to {stream_dir}")
    
    # Verify
    actual_files = len(list(stream_dir.glob("*.mp3")))
    print(f"📊 Stream folder now has: {actual_files} tracks")
    
    return total_copied

if __name__ == "__main__":
    print("="*60)
    print("AUDIO ORGANIZER")
    print("="*60)
    
    # Step 1: Organize tracks
    organize_audio()
    
    # Step 2: Prepare for streaming
    prepare_stream_folder()
    
    print("\n🎉 READY TO STREAM!")
    print("Run: python stream_now.py")
    print("="*60)