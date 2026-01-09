#!/usr/bin/env python3
"""
YouTube Auto-Stream Bot
Fully automated 12-hour daily stream with Pexels videos and royalty-free audio
Run once and it handles everything automatically
"""

import os
import sys
import json
import random
import time
import signal
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont

# ==================== CONFIGURATION ====================
class Config:
    # User must set these two values
    PEXELS_API_KEY = "5Z0FknDCxRJ7yDfHQRkQEZNto7u2pqBouai4jmruFxs2UhhjoB0uoLZn"  # Get from https://www.pexels.com/api/
    YOUTUBE_STREAM_KEY = "kq21-vcse-cwk7-wu9m-8pu1"  # From YouTube Studio
    
    # Stream settings
    STREAM_DURATION = 43200  # 12 hours in seconds
    AUTO_RESTART_DELAY = 30  # Seconds between restarts if stream fails
    MAX_RESTARTS = 5  # Maximum restart attempts
    
    # File paths
    BASE_DIR = Path(__file__).parent
    ASSETS_DIR = BASE_DIR / "assets"
    TEMP_DIR = BASE_DIR / "temp"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Content settings
    THEMES = [
        {
            "name": "Fireplace",
            "keywords": ["fireplace cozy", "fire burning", "campfire"],
            "colors": ["#FF6B35", "#FFA500", "#8B0000"],
            "hashtags": "#Fireplace #Cozy #Winter #Relax"
        },
        {
            "name": "Rain",
            "keywords": ["rain window", "rainy day", "raindrops"],
            "colors": ["#4682B4", "#87CEEB", "#2F4F4F"],
            "hashtags": "#Rain #Storm #Relaxing #Sleep"
        },
        {
            "name": "Ocean",
            "keywords": ["ocean waves", "beach sunset", "sea waves"],
            "colors": ["#1E90FF", "#00BFFF", "#000080"],
            "hashtags": "#Ocean #Waves #Beach #Meditation"
        },
        {
            "name": "Forest",
            "keywords": ["forest stream", "woods path", "green forest"],
            "colors": ["#228B22", "#32CD32", "#006400"],
            "hashtags": "#Forest #Nature #Green #Calm"
        },
        {
            "name": "Space",
            "keywords": ["galaxy nebula", "stars space", "universe"],
            "colors": ["#4B0082", "#9400D3", "#000000"],
            "hashtags": "#Space #Galaxy #Cosmos #Universe"
        },
        {
            "name": "Coffee Shop",
            "keywords": ["coffee shop", "cafe interior", "coffee"],
            "colors": ["#8B4513", "#D2691E", "#A0522D"],
            "hashtags": "#Coffee #Cafe #Study #Relax"
        },
        {
            "name": "Library",
            "keywords": ["library study", "bookshelves", "quiet library"],
            "colors": ["#8B7355", "#D2B48C", "#A0522D"],
            "hashtags": "#Library #Study #Books #Quiet"
        },
        {
            "name": "Mountain",
            "keywords": ["mountain view", "alpine landscape", "snow mountains"],
            "colors": ["#2E8B57", "#708090", "#4682B4"],
            "hashtags": "#Mountain #Nature #Alpine #Peace"
        }
    ]
    
    @classmethod
    def setup_directories(cls):
        """Create all necessary directories"""
        dirs = [cls.ASSETS_DIR, cls.TEMP_DIR, cls.LOGS_DIR]
        for d in dirs:
            d.mkdir(exist_ok=True)
        
        # Create subdirectories
        (cls.ASSETS_DIR / "audio").mkdir(exist_ok=True)
        (cls.ASSETS_DIR / "fonts").mkdir(exist_ok=True)
        (cls.ASSETS_DIR / "thumbnails").mkdir(exist_ok=True)

# ==================== LOGGING SETUP ====================
def setup_logging():
    """Configure logging system"""
    log_file = Config.LOGS_DIR / f"stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# ==================== CONTENT MANAGER ====================
class ContentManager:
    def __init__(self, logger):
        self.logger = logger
        self.today_theme = None
        self.video_file = None
        self.audio_files = []
        
    def select_daily_theme(self):
        """Select and return today's theme"""
        # Use day of year to ensure variety
        day_of_year = datetime.now().timetuple().tm_yday
        self.today_theme = Config.THEMES[day_of_year % len(Config.THEMES)]
        
        self.logger.info(f"Selected theme: {self.today_theme['name']}")
        return self.today_theme
    
    def download_video_from_pexels(self):
        """Download a video from Pexels based on today's theme"""
        if Config.PEXELS_API_KEY == "YOUR_PEXELS_API_KEY":
            self.logger.error("PEXELS_API_KEY not set! Please update in Config class.")
            return False
        
        keyword = random.choice(self.today_theme["keywords"])
        url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=5&orientation=landscape"
        
        headers = {"Authorization": Config.PEXELS_API_KEY}
        
        try:
            self.logger.info(f"Searching Pexels for: {keyword}")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('videos'):
                    # Select a video with good quality
                    video = data['videos'][0]
                    
                    # Find HD video file
                    video_files = [v for v in video['video_files'] 
                                  if v['quality'] in ['hd', 'sd'] and v['width'] >= 1280]
                    
                    if not video_files:
                        video_files = video['video_files']
                    
                    video_file = video_files[0]
                    video_url = video_file['link']
                    
                    # Download video
                    self.logger.info(f"Downloading video: {video['id']}")
                    video_response = requests.get(video_url, stream=True, timeout=60)
                    
                    self.video_file = Config.TEMP_DIR / f"video_{datetime.now().strftime('%Y%m%d')}.mp4"
                    
                    with open(self.video_file, 'wb') as f:
                        for chunk in video_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    self.logger.info(f"Video downloaded: {self.video_file}")
                    
                    # Save attribution
                    attribution = f"Video by {video['user']['name']} from Pexels"
                    with open(Config.TEMP_DIR / "attribution.txt", "w") as f:
                        f.write(attribution)
                    
                    return True
            
            self.logger.warning(f"Failed to get video from Pexels. Status: {response.status_code}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error downloading video: {e}")
            return False
    
    def find_audio_files(self):
        """Find all audio files in assets/audio directory"""
        audio_dir = Config.ASSETS_DIR / "audio"
        
        if not audio_dir.exists():
            self.logger.error("Audio directory not found! Please add MP3 files to assets/audio/")
            return False
        
        self.audio_files = list(audio_dir.glob("*.mp3"))
        
        if not self.audio_files:
            self.logger.error("No MP3 files found in assets/audio/")
            self.logger.info("Please download royalty-free music from YouTube Audio Library")
            return False
        
        self.logger.info(f"Found {len(self.audio_files)} audio files")
        return True
    
    def create_audio_playlist(self):
        """Create a shuffled playlist of audio files"""
        if not self.audio_files:
            self.logger.error("No audio files available")
            return None
        
        # Shuffle audio files for variety
        random.shuffle(self.audio_files)
        
        # Create playlist file for FFmpeg
        playlist_file = Config.TEMP_DIR / "playlist.txt"
        
        with open(playlist_file, "w", encoding="utf-8") as f:
            for audio_file in self.audio_files:
                # Convert to absolute path with forward slashes
                abs_path = audio_file.resolve()
                f.write(f"file '{abs_path}'\n")
        
        self.logger.info(f"Created playlist with {len(self.audio_files)} tracks")
        return playlist_file
    
    def generate_thumbnail(self):
        """Generate a custom thumbnail for the stream"""
        try:
            # Create a simple thumbnail with today's theme
            width, height = 1280, 720
            thumbnail = Image.new('RGB', (width, height), color='black')
            draw = ImageDraw.Draw(thumbnail)
            
            # Add gradient background
            for i in range(height):
                r = int(30 + (i / height) * 50)
                g = int(30 + (i / height) * 50)
                b = int(50 + (i / height) * 100)
                draw.line([(0, i), (width, i)], fill=(r, g, b))
            
            # Try to load a font
            try:
                # Try system fonts first
                font_paths = [
                    "C:/Windows/Fonts/arial.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    str(Config.ASSETS_DIR / "fonts" / "arial.ttf")
                ]
                
                font = None
                for fp in font_paths:
                    if os.path.exists(fp):
                        font = ImageFont.truetype(fp, 60)
                        break
                
                if font is None:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Add title
            title = f"{self.today_theme['name']} Ambience"
            title_bbox = draw.textbbox((0, 0), title, font=font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (width - title_width) // 2
            draw.text((title_x, 200), title, fill="white", font=font)
            
            # Add subtitle
            subtitle = "24/7 Live Stream • Study • Sleep • Focus"
            subtitle_font = ImageFont.truetype(font.path, 30) if hasattr(font, 'path') else font
            subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (width - subtitle_width) // 2
            draw.text((subtitle_x, 300), subtitle, fill="#CCCCCC", font=subtitle_font)
            
            # Add duration
            duration = "12-Hour Session"
            duration_y = 400
            draw.text((width//2 - 150, duration_y), duration, fill="#FFD700", font=subtitle_font)
            
            # Save thumbnail
            thumbnail_file = Config.TEMP_DIR / "thumbnail.jpg"
            thumbnail.save(thumbnail_file, "JPEG", quality=95)
            
            self.logger.info(f"Generated thumbnail: {thumbnail_file}")
            return thumbnail_file
            
        except Exception as e:
            self.logger.error(f"Error generating thumbnail: {e}")
            return None
    
    def generate_stream_description(self):
        """Generate YouTube stream description"""
        description = f"""🔴 LIVE NOW: {self.today_theme['name']} Ambience • 12-Hour Stream

Perfect for:
• Studying & Learning
• Working & Coding
• Sleeping & Relaxing
• Meditation & Yoga
• Reading & Writing

🎯 Today's Theme: {self.today_theme['name']}
⏰ Duration: 12 Hours
🎵 Audio: Royalty-Free Ambient Music
📺 Video: Loop from Pexels

Tips for best experience:
1. Use headphones for immersive sound
2. Adjust volume to your comfort level
3. Try Pomodoro technique (25min work / 5min break)
4. Stay hydrated during long sessions!

This stream is 100% automated using Python.
All audio is royalty-free from YouTube Audio Library.
All videos are from Pexels (royalty-free).

{self.today_theme['hashtags']}
#LiveStream #Ambient #StudyWithMe #FocusMusic #BackgroundNoise #Relaxation #WhiteNoise #NoCopyright #Python #Automation

Current Date: {datetime.now().strftime('%Y-%m-%d')}
Stream Started: {datetime.now().strftime('%H:%M UTC')}
"""
        
        # Add attribution if available
        attribution_file = Config.TEMP_DIR / "attribution.txt"
        if attribution_file.exists():
            with open(attribution_file, "r") as f:
                description += f"\n\n{f.read()}"
        
        # Save description to file
        desc_file = Config.TEMP_DIR / "description.txt"
        with open(desc_file, "w", encoding="utf-8") as f:
            f.write(description)
        
        self.logger.info("Generated stream description")
        return description

# ==================== STREAM MANAGER ====================
class StreamManager:
    def __init__(self, logger, content_manager):
        self.logger = logger
        self.content = content_manager
        self.stream_process = None
        self.start_time = None
        self.restart_count = 0
        
    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.logger.info("FFmpeg is available")
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            self.logger.error("FFmpeg not found! Please install FFmpeg:")
            self.logger.error("Windows: Download from https://ffmpeg.org/download.html")
            self.logger.error("Mac: brew install ffmpeg")
            self.logger.error("Linux: sudo apt install ffmpeg")
            return False
        
        return False
    
    def build_ffmpeg_command(self, video_file, playlist_file):
        """Build the FFmpeg command for streaming"""
        if Config.YOUTUBE_STREAM_KEY == "YOUR_YOUTUBE_STREAM_KEY":
            self.logger.error("YOUTUBE_STREAM_KEY not set! Please update in Config class.")
            return None
        
        # Basic FFmpeg command for YouTube streaming
        command = [
            "ffmpeg",
            "-re",  # Read input at native frame rate
            "-stream_loop", "-1",  # Loop video infinitely
            "-i", str(video_file),  # Input video
            "-f", "concat",  # Audio playlist format
            "-safe", "0",
            "-i", str(playlist_file),  # Audio playlist
            "-map", "0:v:0",  # Use video from first input
            "-map", "1:a:0",  # Use audio from second input
            "-c:v", "libx264",  # Video codec
            "-preset", "veryfast",  # Fast encoding preset
            "-tune", "stillimage",  # Optimized for static images
            "-crf", "23",  # Quality (23 is good for streaming)
            "-maxrate", "2500k",  # Maximum bitrate
            "-bufsize", "5000k",  # Buffer size
            "-pix_fmt", "yuv420p",  # Pixel format for compatibility
            "-g", "60",  # Keyframe interval
            "-c:a", "aac",  # Audio codec
            "-b:a", "128k",  # Audio bitrate
            "-ar", "44100",  # Audio sample rate
            "-ac", "2",  # Stereo audio
            "-f", "flv",  # Output format
            f"rtmp://a.rtmp.youtube.com/live2/{Config.YOUTUBE_STREAM_KEY}"
        ]
        
        return command
    
    def start_stream(self):
        """Start the streaming process"""
        # Get video and audio
        if not self.content.video_file or not self.content.video_file.exists():
            self.logger.error("Video file not available")
            return False
        
        playlist_file = self.content.create_audio_playlist()
        if not playlist_file:
            self.logger.error("Audio playlist not available")
            return False
        
        # Build FFmpeg command
        command = self.build_ffmpeg_command(self.content.video_file, playlist_file)
        if not command:
            return False
        
        self.logger.info("Starting stream...")
        self.logger.info(f"Command: {' '.join(command[:8])}...")
        
        try:
            # Start FFmpeg process
            self.stream_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.start_time = datetime.now()
            self.logger.info(f"Stream started at {self.start_time}")
            
            # Monitor stream output
            self.monitor_stream()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start stream: {e}")
            return False
    
    def monitor_stream(self):
        """Monitor the stream process and handle output"""
        stream_duration = 0
        
        while self.stream_process and self.stream_process.poll() is None:
            # Read output line by line
            for line in iter(self.stream_process.stdout.readline, ''):
                if line.strip():
                    # Log important FFmpeg messages
                    if "frame=" in line and "fps=" in line:
                        # Log progress every minute
                        current_time = datetime.now()
                        if hasattr(self, 'last_log_time'):
                            if (current_time - self.last_log_time).seconds >= 60:
                                self.logger.info(f"Streaming... {line.strip()[:100]}")
                                self.last_log_time = current_time
                        else:
                            self.last_log_time = current_time
                    
                    # Check for errors
                    if "error" in line.lower() or "failed" in line.lower():
                        self.logger.warning(f"FFmpeg warning: {line.strip()}")
            
            # Check duration
            stream_duration = (datetime.now() - self.start_time).seconds
            if stream_duration >= Config.STREAM_DURATION:
                self.logger.info(f"Reached 12-hour duration. Stopping stream.")
                self.stop_stream()
                break
            
            # Check if process died
            if self.stream_process.poll() is not None:
                self.logger.warning(f"Stream process died unexpectedly. Exit code: {self.stream_process.poll()}")
                break
            
            time.sleep(1)
    
    def stop_stream(self):
        """Stop the streaming process gracefully"""
        if self.stream_process and self.stream_process.poll() is None:
            self.logger.info("Stopping stream...")
            
            # Send Ctrl+C equivalent
            self.stream_process.terminate()
            
            # Wait for process to end
            try:
                self.stream_process.wait(timeout=10)
                self.logger.info("Stream stopped gracefully")
            except subprocess.TimeoutExpired:
                self.logger.warning("Force killing stream process...")
                self.stream_process.kill()
                self.stream_process.wait()
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if Config.TEMP_DIR.exists():
                # Keep today's files for debugging, remove older
                for item in Config.TEMP_DIR.iterdir():
                    if item.is_file():
                        # Don't delete files from today
                        if "attribution.txt" in item.name:
                            continue  # Keep attribution
                        item.unlink()
                
                self.logger.info("Cleaned up temporary files")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

# ==================== MAIN APPLICATION ====================
class YouTubeAutoStream:
    def __init__(self):
        # Setup
        Config.setup_directories()
        self.logger = setup_logging()
        self.content = ContentManager(self.logger)
        self.stream = StreamManager(self.logger, self.content)
        
        # Signal handling
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}. Shutting down...")
        self.running = False
        self.stream.stop_stream()
    
    def check_prerequisites(self):
        """Check all prerequisites before starting"""
        self.logger.info("=" * 60)
        self.logger.info("YouTube Auto-Stream Bot")
        self.logger.info(f"Start Time: {datetime.now()}")
        self.logger.info("=" * 60)
        
        # Check API keys
        if Config.PEXELS_API_KEY == "YOUR_PEXELS_API_KEY":
            self.logger.error("ERROR: PEXELS_API_KEY not configured!")
            self.logger.info("Get API key from: https://www.pexels.com/api/")
            return False
        
        if Config.YOUTUBE_STREAM_KEY == "YOUR_YOUTUBE_STREAM_KEY":
            self.logger.error("ERROR: YOUTUBE_STREAM_KEY not configured!")
            self.logger.info("Get stream key from YouTube Studio -> Go Live")
            return False
        
        # Check FFmpeg
        if not self.stream.check_ffmpeg():
            return False
        
        # Check audio files
        if not self.content.find_audio_files():
            self.logger.warning("Continuing without audio files. Stream will have no audio.")
        
        self.logger.info("All prerequisites checked successfully")
        return True
    
    def run(self):
        """Main execution flow"""
        if not self.check_prerequisites():
            self.logger.error("Prerequisites check failed. Exiting.")
            return
        
        try:
            # Step 1: Select daily theme
            theme = self.content.select_daily_theme()
            
            # Step 2: Download video
            self.logger.info("Downloading video from Pexels...")
            if not self.content.download_video_from_pexels():
                self.logger.error("Failed to download video. Exiting.")
                return
            
            # Step 3: Generate thumbnail
            self.logger.info("Generating thumbnail...")
            thumbnail = self.content.generate_thumbnail()
            if thumbnail:
                self.logger.info(f"Thumbnail ready: {thumbnail}")
            
            # Step 4: Generate description
            description = self.content.generate_stream_description()
            self.logger.info("Description generated")
            
            # Step 5: Display stream info
            self.display_stream_info(theme, description)
            
            # Step 6: Start countdown
            self.countdown(10)
            
            # Step 7: Start stream
            self.logger.info("🚀 Starting 12-hour stream...")
            stream_started = self.stream.start_stream()
            
            if stream_started:
                self.logger.info("✅ Stream completed successfully")
            else:
                self.logger.error("❌ Stream failed to start")
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
        
        finally:
            # Step 8: Cleanup
            self.logger.info("Performing cleanup...")
            self.stream.cleanup()
            
            # Save log summary
            self.save_summary()
            
            self.logger.info("=" * 60)
            self.logger.info("YouTube Auto-Stream Bot - Finished")
            self.logger.info(f"End Time: {datetime.now()}")
            self.logger.info("=" * 60)
    
    def display_stream_info(self, theme, description):
        """Display stream information"""
        print("\n" + "=" * 60)
        print("🎬 TODAY'S STREAM INFO")
        print("=" * 60)
        print(f"Theme: {theme['name']}")
        print(f"Colors: {', '.join(theme['colors'])}")
        print(f"Hashtags: {theme['hashtags']}")
        print(f"Duration: 12 hours")
        print(f"Start Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"End Time: {(datetime.now() + timedelta(seconds=Config.STREAM_DURATION)).strftime('%H:%M:%S')}")
        print("\n📝 Description Preview:")
        print("-" * 40)
        print(description[:500] + "..." if len(description) > 500 else description)
        print("-" * 40)
        print("\n📍 Files Generated:")
        print(f"Video: {self.content.video_file}")
        print(f"Thumbnail: {Config.TEMP_DIR / 'thumbnail.jpg'}")
        print(f"Description: {Config.TEMP_DIR / 'description.txt'}")
        print("=" * 60 + "\n")
    
    def countdown(self, seconds):
        """Display countdown before starting"""
        self.logger.info(f"Starting in {seconds} seconds...")
        for i in range(seconds, 0, -1):
            print(f"Starting in {i}...", end='\r')
            time.sleep(1)
        print("Starting NOW!" + " " * 20)
    
    def save_summary(self):
        """Save a summary of today's stream"""
        summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "theme": self.content.today_theme["name"] if self.content.today_theme else "Unknown",
            "start_time": self.stream.start_time.isoformat() if self.stream.start_time else None,
            "end_time": datetime.now().isoformat(),
            "duration_minutes": Config.STREAM_DURATION / 60,
            "video_file": str(self.content.video_file) if self.content.video_file else None,
            "audio_tracks": len(self.content.audio_files) if self.content.audio_files else 0
        }
        
        summary_file = Config.LOGS_DIR / f"summary_{datetime.now().strftime('%Y%m%d')}.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Summary saved to: {summary_file}")

# ==================== QUICK SETUP SCRIPT ====================
def quick_setup():
    """Quick setup for first-time users"""
    print("=" * 60)
    print("YouTube Auto-Stream Bot - Quick Setup")
    print("=" * 60)
    
    # Create directories
    Config.setup_directories()
    
    # Check FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg is installed")
    except:
        print("❌ FFmpeg not found!")
        print("Please install FFmpeg:")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        print("  Mac: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
        return False
    
    # Create sample audio directory structure
    audio_dir = Config.ASSETS_DIR / "audio"
    audio_dir.mkdir(exist_ok=True)
    
    # Create README file
    readme = """# YouTube Auto-Stream Bot

## Setup Instructions:

1. Get a Pexels API key:
   - Go to https://www.pexels.com/api/
   - Sign up and create an API key
   - Update PEXELS_API_KEY in the script

2. Get YouTube Stream Key:
   - Go to YouTube Studio
   - Click "Go Live"
   - Get your stream key
   - Update YOUTUBE_STREAM_KEY in the script

3. Add Audio Files:
   - Download royalty-free music from YouTube Audio Library
   - Save MP3 files to: assets/audio/
   - Need at least 5-10 tracks for variety

4. Run the bot:
   python auto_stream.py

## Daily Schedule:
- Automatically downloads new video from Pexels
- Generates custom thumbnail
- Creates stream description
- Streams for exactly 12 hours
- Cleans up temporary files

## Requirements:
- Python 3.8+
- FFmpeg installed
- Pexels API key
- YouTube channel with streaming enabled
"""
    
    with open(Config.BASE_DIR / "README.txt", "w") as f:
        f.write(readme)
    
    print("\n✅ Setup completed!")
    print(f"📁 Project structure created in: {Config.BASE_DIR}")
    print("\nNext steps:")
    print("1. Update PEXELS_API_KEY and YOUTUBE_STREAM_KEY in the script")
    print("2. Add MP3 files to: assets/audio/")
    print("3. Run: python auto_stream.py")
    print("=" * 60)
    
    return True

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    print("YouTube Auto-Stream Bot")
    print("Version 1.0 - Fully Automated")
    print("=" * 50)
    
    # Check if setup is needed
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        quick_setup()
    else:
        # Run the main application
        app = YouTubeAutoStream()
        app.run()