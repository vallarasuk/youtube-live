#!/usr/bin/env python3
"""
stream_now.py - Start 12-hour YouTube stream immediately
"""

import os
import sys
import json
import random
import time
import signal
from pathlib import Path
import subprocess
from datetime import datetime
import requests

# ==================== CONFIG ====================
PEXELS_API_KEY = "5Z0FknDCxRJ7yDfHQRkQEZNto7u2pqBouai4jmruFxs2UhhjoB0uoLZn"
YOUTUBE_STREAM_KEY = "kq21-vcse-cwk7-wu9m-8pu1"
STREAM_DURATION = 300  # 5 minutes for testing (change to 43200 for 12 hours)

# Directories
BASE_DIR = Path(__file__).parent
AUDIO_DIR = BASE_DIR / "assets" / "audio"
TEMP_DIR = BASE_DIR / "temp"
LOG_FILE = BASE_DIR / "stream.log"

# ==================== STREAM CLASS ====================
class YouTubeStreamer:
    def __init__(self):
        # Setup directories
        TEMP_DIR.mkdir(exist_ok=True)
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        
        # Find audio files
        self.audio_files = list(AUDIO_DIR.glob("*.mp3"))
        if not self.audio_files:
            print("❌ No audio files found in assets/audio/")
            sys.exit(1)
        
        print(f"🎵 Loaded {len(self.audio_files)} audio tracks")
        
        # Video themes
        self.video_themes = [
            "fireplace", "ocean waves", "rain window", "forest stream",
            "galaxy space", "coffee shop", "snow falling", "waterfall"
        ]
        
        self.stream_process = None
        self.start_time = None
    
    def log(self, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        # Also save to log file
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")
    
    def create_playlist(self):
        """Create random audio playlist"""
        # Use all available audio files
        playlist_file = TEMP_DIR / "playlist.txt"
        
        with open(playlist_file, 'w', encoding='utf-8') as f:
            for audio_file in self.audio_files:
                f.write(f"file '{audio_file.absolute()}'\n")
        
        self.log(f"📋 Created playlist with {len(self.audio_files)} tracks")
        return playlist_file
    
    def get_video(self):
        """Get video for streaming - SIMPLIFIED VERSION"""
        try:
            # Try Pexels API
            theme = random.choice(self.video_themes)
            url = f"https://api.pexels.com/videos/search?query={theme}&per_page=1"
            
            headers = {"Authorization": PEXELS_API_KEY}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('videos'):
                    video = data['videos'][0]
                    # Get the first video file
                    video_file = video['video_files'][0]
                    
                    # Download video
                    video_path = TEMP_DIR / "video.mp4"
                    
                    self.log(f"⬇️ Downloading video: {theme}")
                    video_response = requests.get(video_file['link'], stream=True)
                    
                    with open(video_path, 'wb') as f:
                        for chunk in video_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    if video_path.exists() and video_path.stat().st_size > 0:
                        self.log(f"✅ Downloaded: {theme}")
                        return video_path
                    
        except Exception as e:
            self.log(f"⚠️ Video download: {str(e)[:50]}")
        
        # Fallback: Use test pattern
        return self.create_test_video()
    
    def create_test_video(self):
        """Create a test pattern video"""
        video_path = TEMP_DIR / "test_video.mp4"
        
        # Create 30-second test pattern
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=duration=30:size=1280x720:rate=30",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-t", "30",
            "-y",  # Overwrite
            str(video_path)
        ]
        
        try:
            self.log("🎨 Creating test pattern video...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if video_path.exists():
                file_size = video_path.stat().st_size / (1024 * 1024)
                self.log(f"✅ Created test video ({file_size:.1f} MB)")
                return video_path
        except Exception as e:
            self.log(f"❌ Test video failed: {e}")
        
        return None
    
    def build_stream_command(self, video_file, playlist_file):
        """Build FFmpeg streaming command"""
        return [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-i", str(video_file),
            "-f", "concat",
            "-safe", "0",
            "-i", str(playlist_file),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-maxrate", "1500k",
            "-bufsize", "3000k",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_STREAM_KEY}"
        ]
    
    def start(self):
        """Start the stream"""
        try:
            self.log("="*60)
            self.log("🎬 STARTING YOUTUBE LIVE STREAM")
            self.log("="*60)
            
            # Get video
            video_file = self.get_video()
            if not video_file or not video_file.exists():
                self.log("❌ Could not get video")
                return False
            
            # Create audio playlist
            playlist_file = self.create_playlist()
            
            # Build command
            command = self.build_stream_command(video_file, playlist_file)
            
            # Display info
            self.log(f"📺 Video: {video_file.name}")
            self.log(f"🎵 Audio: {len(self.audio_files)} tracks")
            self.log(f"⏰ Duration: {STREAM_DURATION//60} minutes")
            self.log(f"🔑 Stream key: {YOUTUBE_STREAM_KEY[:8]}...")
            
            self.log("\n🚀 Starting stream in 5 seconds...")
            for i in range(5, 0, -1):
                print(f"Starting in {i}...", end='\r')
                time.sleep(1)
            print("Starting NOW! " + " "*20)
            
            # Start FFmpeg process
            self.stream_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.start_time = datetime.now()
            self.log(f"✅ Stream started at {self.start_time}")
            self.log("📢 IMPORTANT: Go to YouTube Studio and click 'GO LIVE'")
            self.log("="*60)
            
            # Monitor stream
            self.monitor()
            
            return True
            
        except Exception as e:
            self.log(f"❌ Stream error: {e}")
            return False
    
    def monitor(self):
        """Monitor stream for duration"""
        try:
            while self.stream_process and self.stream_process.poll() is None:
                elapsed = (datetime.now() - self.start_time).seconds
                
                # Check duration
                if elapsed >= STREAM_DURATION:
                    self.log("⏰ Time limit reached. Stopping...")
                    self.stop()
                    break
                
                # Periodic logging
                if elapsed % 60 == 0:  # Every minute
                    minutes = elapsed // 60
                    self.log(f"⏱️ Running: {minutes} minutes")
                
                # Read FFmpeg output occasionally
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.log("\n🛑 Keyboard interrupt received")
            self.stop()
        except Exception as e:
            self.log(f"⚠️ Monitor error: {e}")
    
    def stop(self):
        """Stop the stream"""
        if self.stream_process and self.stream_process.poll() is None:
            self.log("🛑 Stopping stream...")
            self.stream_process.terminate()
            self.stream_process.wait()
            self.log("✅ Stream stopped")
    
    def cleanup(self):
        """Clean temporary files"""
        try:
            if TEMP_DIR.exists():
                import shutil
                shutil.rmtree(TEMP_DIR)
                self.log("🧹 Cleaned temp files")
        except:
            pass

# ==================== MAIN ====================
if __name__ == "__main__":
    # Signal handler
    def handle_signal(signum, frame):
        print(f"\n🛑 Signal {signum} received")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Check FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg is ready")
        else:
            print("❌ FFmpeg not working")
            sys.exit(1)
    except FileNotFoundError:
        print("❌ FFmpeg not installed!")
        print("Install: brew install ffmpeg  # Mac")
        print("         sudo apt install ffmpeg  # Ubuntu")
        sys.exit(1)
    
    # Check audio
    audio_files = list(AUDIO_DIR.glob("*.mp3"))
    if not audio_files:
        print("❌ No audio files. Run: python organize_audio.py")
        sys.exit(1)
    
    print(f"\n🎵 Audio ready: {len(audio_files)} tracks")
    print("🎥 Video: Will download from Pexels")
    print(f"⏰ Test duration: {STREAM_DURATION//60} minutes")
    print("\n" + "="*60)
    
    # Start stream
    streamer = YouTubeStreamer()
    
    try:
        success = streamer.start()
        if success:
            print("\n✨ Stream completed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        streamer.cleanup()
        
        # Show log file location
        if LOG_FILE.exists():
            print(f"\n📄 Log saved: {LOG_FILE}")
        
        print("\n" + "="*60)
        print("NEXT STEP: Go to YouTube Studio")
        print("1. Open https://studio.youtube.com")
        print("2. Click 'Go Live'")
        print("3. Click 'Stream' tab")
        print("4. Click 'GO LIVE' button")
        print("="*60)