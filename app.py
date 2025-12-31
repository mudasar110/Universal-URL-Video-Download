

# Here is the fully fixed `app.py`.

### Fixes Applied:
# 1.  **Fixed TikTok Sound Issue:** Updated the download format selector to prioritize videos that **already contain audio** (`best[vcodec!=none][acodec!=none]`). If the audio is separate, it now forces `yt-dlp` to download both video and audio streams and **merge them** using FFmpeg. This ensures the downloaded video has sound.
# 2.  **Fixed Deprecation Warning:** Replaced `use_column_width=True` with `use_container_width=True` for thumbnails and buttons.
# 3.  **Blocked Bad URLs:** Added a hard filter to explicitly reject TikTok homepage links (`tiktok.com/?...`, `tiktok.com/explore`) before the download engine even attempts to run them.

### `app.py`

# ```python
"""
Universal Social Media Video Downloader Pro
Final Year Project - Production Ready Application
Single-file Streamlit application with Audio Fix and Deprecation Updates
"""

import streamlit as st
import yt_dlp
import os
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Page Configuration
st.set_page_config(
    page_title="Universal Video Downloader Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Mobile and Styling
def local_css():
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 10px;
            text-align: center;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .status-box {
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        /* Hide streamlit footer */
        footer {visibility: hidden;}
        
        /* Mobile adjustments */
        @media (max-width: 768px) {
            .stButton button { width: 100%; }
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# Constants
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Platform Regex Patterns
PLATFORM_PATTERNS = {
    'youtube': [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})'
    ],
    'tiktok': [
        r'tiktok\.com\/@[\w\.-]+\/video\/(\d+)',
        r'vm\.tiktok\.com\/(\w+)',
        r'vt\.tiktok\.com\/(\w+)'
    ],
    'instagram': [
        r'instagram\.com\/(?:p|reel|tv)\/([a-zA-Z0-9_-]+)',
    ],
    'facebook': [
        r'facebook\.com\/watch\/\?v=(\d+)',
        r'facebook\.com\/[\w\.-]+\/videos\/(\d+)',
        r'fb\.watch\/(\w+)'
    ],
    'twitter': [
        r'twitter\.com\/[\w\.-]+\/status\/(\d+)',
        r'x\.com\/[\w\.-]+\/status\/(\d+)'
    ],
    'snapchat': [
        r'snapchat\.com\/t\/(\w+)',
        r'snapchat\.com\/add\/[\w\.-]+'
    ]
}

PLATFORM_INFO = {
    'youtube': {'icon': '📺', 'color': '#FF0000', 'name': 'YouTube'},
    'tiktok': {'icon': '🎵', 'color': '#000000', 'name': 'TikTok'},
    'instagram': {'icon': '📷', 'color': '#E4405F', 'name': 'Instagram'},
    'facebook': {'icon': '👥', 'color': '#1877F2', 'name': 'Facebook'},
    'twitter': {'icon': '🐦', 'color': '#1DA1F2', 'name': 'Twitter/X'},
    'snapchat': {'icon': '👻', 'color': '#FFFC00', 'name': 'Snapchat'}
}

# ============================================================================
# UTILITY CLASSES
# ============================================================================

class URLProcessor:
    """Handles URL validation, sanitization, and platform detection"""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False
    
    @staticmethod
    def detect_platform(url: str) -> Optional[str]:
        url_lower = url.lower()
        for platform, patterns in PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return platform
        return None
    
    @staticmethod
    def is_valid_content_url(url: str, platform: str) -> bool:
        """
        Checks if the URL is a valid content URL (video/image) and not just a homepage.
        """
        if not url or not platform:
            return False
            
        url_lower = url.lower()
        
        # --- Strict Check for TikTok ---
        if platform == 'tiktok':
            # Block generic TikTok home/explore pages explicitly
            # Checks for home page ending or 'explore' path
            if '/explore' in url_lower:
                return False
            if url_lower.endswith('tiktok.com/') or url_lower.endswith('tiktok.com'):
                return False
            # It MUST contain one of these specific keywords
            if not ('/video/' in url_lower or 'vm.tiktok' in url_lower or 'vt.tiktok' in url_lower):
                return False
        
        # --- Strict Check for YouTube ---
        if platform == 'youtube':
            if not ('watch?v=' in url_lower or '/shorts/' in url_lower or 'youtu.be/' in url_lower):
                return False

        # Check against Regex Patterns
        if platform in PLATFORM_PATTERNS:
            for pattern in PLATFORM_PATTERNS[platform]:
                if re.search(pattern, url_lower):
                    return True
                    
        return False

    @staticmethod
    def sanitize_url(url: str) -> str:
        if not url:
            return url
        url = ''.join(url.split())
        if url.count('/') > 3:
            url = url.rstrip('/')
        if not url.startswith(('http://', 'https://')):
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://' + url.lstrip('/')
            else:
                url = 'https://' + url
        return url

class FileManager:
    """Manages file operations"""
    
    @staticmethod
    def get_file_size(filepath: str) -> str:
        try:
            size = os.path.getsize(filepath)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.2f} {unit}"
                size /= 1024.0
            return f"{size:.2f} TB"
        except:
            return "Unknown"

# ============================================================================
# DOWNLOAD MANAGER
# ============================================================================

class DownloadManager:
    """Main download manager using yt-dlp"""
    
    def __init__(self):
        self.downloads_dir = DOWNLOADS_DIR
    
    def get_base_opts(self, quality: str = 'best', extract_audio: bool = False, platform: str = None) -> Dict:
        format_selector = self._get_format_selector(quality, extract_audio, platform)
        
        # Common headers to mimic a real browser
        http_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        }
        
        # Add referer for TikTok
        if platform == 'tiktok':
            http_headers['Referer'] = 'https://www.tiktok.com/'
        
        opts = {
            'format': format_selector,
            'outtmpl': str(self.downloads_dir / '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'noplaylist': True,
            'http_headers': http_headers,
        }
        
        if platform == 'tiktok':
            opts['extractor_args'] = {'tiktok': {'webpage_download': True}}
            # IMPORTANT: Allow merging to ensure audio is included
            if not extract_audio:
                opts['merge_output_format'] = 'mp4'
        
        if extract_audio:
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif platform != 'tiktok':
            opts['merge_output_format'] = 'mp4'
        
        return opts
    
    def _get_format_selector(self, quality: str, extract_audio: bool, platform: str = None) -> str:
        if extract_audio:
            return 'bestaudio/best'
        
        if platform == 'tiktok':
            # FIX FOR SOUND: 
            # 1. Try to find a file that has both video AND audio codecs.
            # 2. If not found, download bestvideo and bestaudio separately and MERGE them.
            quality_map = {
                'best': 'best[vcodec!=none][acodec!=none]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                '1080p': 'best[height<=1080][vcodec!=none][acodec!=none]/bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '720p': 'best[height<=720][vcodec!=none][acodec!=none]/bestvideo[height<=720]+bestaudio/best[height<=720]',
                '480p': 'best[height<=480][vcodec!=none][acodec!=none]/bestvideo[height<=480]+bestaudio/best[height<=480]',
                '360p': 'best[height<=360][vcodec!=none][acodec!=none]/bestvideo[height<=360]+bestaudio/best[height<=360]',
            }
        else:
            quality_map = {
                'best': 'bestvideo[height<=2160]+bestaudio/best',
                '1080p': 'bestvideo[height<=1080]+bestaudio/best',
                '720p': 'bestvideo[height<=720]+bestaudio/best',
                '480p': 'bestvideo[height<=480]+bestaudio/best',
                '360p': 'bestvideo[height<=360]+bestaudio/best',
            }
        
        return quality_map.get(quality, quality_map['best'])
    
    def get_video_info(self, url: str, platform: str = None) -> Optional[Dict]:
        try:
            processor = URLProcessor()
            resolved_url = processor.sanitize_url(url)
            
            opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            http_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
            if platform == 'tiktok':
                opts['extractor_args'] = {'tiktok': {'webpage_download': True}}
                http_headers['Referer'] = 'https://www.tiktok.com/'
            opts['http_headers'] = http_headers
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(resolved_url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                }
        except Exception:
            return None
    
    def download_video(self, url: str, quality: str = 'best', extract_audio: bool = False, 
                       progress_hook=None, platform: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            processor = URLProcessor()
            resolved_url = processor.sanitize_url(url)
            
            # Double check before calling yt-dlp to prevent logs spam
            if not processor.is_valid_content_url(resolved_url, platform):
                 return False, None, "Invalid URL: This is not a specific video link."

            opts = self.get_base_opts(quality, extract_audio, platform)
            if progress_hook:
                opts['progress_hooks'] = [progress_hook]
            
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(resolved_url, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    if extract_audio:
                        filename = filename.rsplit('.', 1)[0] + '.mp3'
                    
                    if os.path.exists(filename):
                        return True, filename, info.get('title', 'Downloaded Video')
                    else:
                        return False, None, "File not found after download"
            
            except yt_dlp.utils.DownloadError as format_error:
                error_msg = str(format_error)
                if "Unable to extract sigi state" in error_msg:
                     return False, None, "TikTok Security Update. Please update 'yt-dlp': 'pip install --upgrade yt-dlp'"
                
                # Generic format fallback
                if "Requested format is not available" in error_msg or "format" in error_msg.lower():
                    st.info("⚠️ Format error. Trying best available fallback...")
                    opts['format'] = 'best/best'
                    # Force basic download
                    if 'merge_output_format' in opts:
                        del opts['merge_output_format']
                    
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(resolved_url, download=True)
                        filename = ydl.prepare_filename(info)
                        if extract_audio:
                            filename = filename.rsplit('.', 1)[0] + '.mp3'
                        if os.path.exists(filename):
                            return True, filename, info.get('title', 'Downloaded Video')
                        else:
                            return False, None, "File not found after download"
                else:
                    raise
                    
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "Unable to extract sigi state" in error_msg:
                 return False, None, "TikTok API Changed. Update yt-dlp: 'pip install --upgrade yt-dlp'"
            elif "Private video" in error_msg or "private" in error_msg.lower():
                return False, None, "This video is private"
            elif "Video unavailable" in error_msg or "unavailable" in error_msg.lower():
                return False, None, "Video unavailable or removed"
            elif "Sign in to confirm your age" in error_msg or "age" in error_msg.lower():
                return False, None, "Age-restricted content"
            else:
                if "Unsupported URL" in error_msg:
                    return False, None, "Unsupported URL. Please ensure you paste a specific video link, not a homepage."
                return False, None, f"Download error: {error_msg}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"

# ============================================================================
# UI RENDERERS
# ============================================================================

def render_header():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.2rem;">🎬 Universal Video Downloader</h1>
        <p style="margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;">Final Year Project - Production Ready</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.markdown("### 📋 Project Info")
        st.info("Production-ready app for downloading videos from multiple platforms.")
        
        st.markdown("---")
        st.markdown("### 📊 Statistics")
        total = len(st.session_state.get('download_history', []))
        st.metric("Downloads", total)
        
        st.markdown("---")
        st.markdown("### 🌐 Platforms")
        for p, info in PLATFORM_INFO.items():
            st.markdown(f"{info['icon']} **{info['name']}**")

def render_download_section(download_manager):
    st.markdown("### 🔗 Download Center")
    
    if 'url_submitted' not in st.session_state:
        st.session_state.url_submitted = ""
    
    # Input Layout
    col1, col2 = st.columns([5, 1])
    
    with col1:
        url_input = st.text_input(
            "Paste Video URL", 
            label_visibility="collapsed",
            placeholder="https://www.tiktok.com/@user/video/...",
            key="url_text_field"
        )
    
    with col2:
        st.markdown("<div style='height: 27px;'></div>", unsafe_allow_html=True)
        submit_btn = st.button("Go", type="primary", use_container_width=True)
    
    processor = URLProcessor()
    platform_detected = None
    sanitized_url = None
    is_valid = True
    
    # Logic to update session state based on user action
    current_url = processor.sanitize_url(url_input) if url_input else ""
    
    if submit_btn:
        if current_url and processor.validate_url(current_url):
            st.session_state.url_submitted = current_url
        else:
            st.error("Please enter a valid URL starting with http/https")
            st.session_state.url_submitted = ""
            
    # Use the stored URL for processing
    target_url = st.session_state.url_submitted
    
    if target_url:
        platform_detected = processor.detect_platform(target_url)
        
        # --- CRITICAL VALIDATION STEP ---
        # 1. If we detected a platform (e.g. TikTok)
        # 2. Check if the URL is actually a valid video URL (not /explore or /home)
        if platform_detected:
            if not processor.is_valid_content_url(target_url, platform_detected):
                is_valid = False
                if platform_detected == 'tiktok':
                    st.error(f"❌ Invalid Link: You pasted a TikTok Homepage or Explore page.")
                    st.info("Please tap **'Share'** on the video in the app, then **'Copy Link'** to get a valid video URL.")
                elif platform_detected == 'youtube':
                    st.error(f"❌ Invalid Link: This is a generic YouTube page.")
                    st.info("Please paste a link to a specific video (contains /watch?v= or /shorts/).")
                else:
                    st.error(f"❌ Invalid Link: Please paste a specific {PLATFORM_INFO.get(platform_detected, {}).get('name', 'content')} link.")
        
        # If platform is not detected at all (e.g., some weird domain), but URL looks valid
        elif not platform_detected:
            st.warning("⚠️ Platform not recognized. URL might not be supported.")
            # We allow the attempt, but warn user
            is_valid = True 

        # --- PROCEED IF VALID ---
        if is_valid and platform_detected:
            if platform_detected in PLATFORM_INFO:
                info = PLATFORM_INFO[platform_detected]
                st.success(f"{info['icon']} **{info['name']}** Detected")

            # Preview
            with st.expander("📺 Video Preview", expanded=False):
                info = download_manager.get_video_info(target_url, platform_detected)
                if info:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if info.get('thumbnail'):
                            # FIX: Use use_container_width instead of use_column_width
                            st.image(info['thumbnail'], use_container_width=True)
                    with col2:
                        st.markdown(f"**Title:** {info.get('title', 'N/A')}")
                        st.markdown(f"**Uploader:** {info.get('uploader', 'N/A')}")
                        duration = info.get('duration', 0)
                        if duration:
                            mins, secs = divmod(duration, 60)
                            st.markdown(f"**Duration:** {int(mins)}:{int(secs):02d}")
                else:
                    st.info("Preview unavailable")

            # Options
            c1, c2 = st.columns(2)
            with c1:
                quality = st.selectbox("Quality", ['best', '1080p', '720p', '480p', '360p'])
            with c2:
                format_type = st.radio("Format", ['Video (MP4)', 'Audio Only (MP3)'], horizontal=True)
                extract_audio = (format_type == 'Audio Only (MP3)')
            
            download_btn = st.button("⬇️ Start Download", type="primary", use_container_width=True)
            
            if download_btn:
                handle_download(target_url, platform_detected, quality, extract_audio, download_manager)

def handle_download(url: str, platform: str, quality: str, extract_audio: bool, download_manager: DownloadManager):
    if st.session_state.get('download_in_progress'):
        st.warning("Download in progress...")
        return
    
    st.session_state.download_in_progress = True
    progress_container = st.container()
    
    try:
        def my_hook(d):
            if d['status'] == 'downloading':
                with progress_container:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        percent = (downloaded / total) * 100
                        my_bar = st.progress(0)
                        my_bar.progress(percent / 100)
                        speed = d.get('speed', 0)
                        speed_str = f"{speed / (1024*1024):.2f} MB/s" if speed else "Calculating..."
                        st.text(f"Downloading: {percent:.1f}% - {speed_str}")
            elif d['status'] == 'finished':
                with progress_container:
                    st.success("Download finished! Processing...")

        success, filepath, message = download_manager.download_video(
            url, quality, extract_audio, my_hook, platform
        )
        
        progress_container.empty()
        
        if success and filepath:
            history_item = {
                'url': url,
                'platform': platform,
                'title': message,
                'filepath': filepath,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            if 'download_history' not in st.session_state:
                st.session_state.download_history = []
            st.session_state.download_history.append(history_item)
            
            st.success(f"✅ Success: {message}")
            st.balloons()
            
            with open(filepath, 'rb') as f:
                st.download_button(
                    label="⬇️ Save to Device",
                    data=f.read(),
                    file_name=os.path.basename(filepath),
                    mime='video/mp4' if not extract_audio else 'audio/mpeg',
                    use_container_width=True # FIX: Updated here as well
                )
        else:
            st.error(f"❌ {message}")
            
    except Exception as e:
        st.error(f"❌ Critical Error: {str(e)}")
    finally:
        st.session_state.download_in_progress = False

def render_history():
    st.markdown("---")
    st.markdown("### 📜 History")
    history = st.session_state.get('download_history', [])
    if not history:
        st.info("No downloads.")
        return
    
    for item in reversed(history[-5:]):
        with st.container():
            cols = st.columns([4, 2, 2, 1])
            platform = item.get('platform', 'unknown')
            icon = PLATFORM_INFO.get(platform, {}).get('icon', '🎬')
            
            with cols[0]:
                st.markdown(f"{icon} **{item.get('title', 'Unknown')}**")
            with cols[1]:
                st.markdown(f"📅 {item.get('date', '')}")
            with cols[2]:
                fpath = item.get('filepath', '')
                if fpath and os.path.exists(fpath):
                    st.markdown(f"💾 {FileManager.get_file_size(fpath)}")
                else:
                    st.markdown("💾 Missing")
            with cols[3]:
                if st.button("🗑️", key=f"del_{fpath}", use_container_width=True):
                    st.session_state.download_history = [
                        h for h in st.session_state.download_history if h.get('filepath') != fpath
                    ]
                    if os.path.exists(fpath):
                        os.remove(fpath)
                    st.rerun()
            st.divider()

# ============================================================================
# MAIN
# ============================================================================

def main():
    if 'download_history' not in st.session_state:
        st.session_state.download_history = []
    if 'download_in_progress' not in st.session_state:
        st.session_state.download_in_progress = False

    render_header()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        render_sidebar()
    
    with col2:
        download_manager = DownloadManager()
        render_download_section(download_manager)
        render_history()

if __name__ == "__main__":
    main()
