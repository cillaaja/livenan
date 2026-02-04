import sys
import subprocess
import threading
import os
import re
import streamlit.components.v1 as components

# Fungsi untuk menginstal library jika belum ada
def install_package(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Pastikan library penting terinstall
install_package("streamlit")
install_package("gdown")

import streamlit as st
import gdown

def download_from_gdrive(url):
    """Mengunduh file dari Google Drive menggunakan gdown"""
    try:
        # Template nama file sementara
        output = "gdrive_video.mp4"
        # gdown bisa menangani berbagai format URL Google Drive
        file_path = gdown.download(url, output, quiet=False, fuzzy=True)
        return file_path
    except Exception as e:
        st.error(f"Gagal mengunduh dari Google Drive: {e}")
        return None

def run_ffmpeg(video_path, stream_key, is_shorts, log_callback):
    """Menjalankan proses ffmpeg untuk streaming ke YouTube"""
    output_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale_filter = "scale=720:1280" if is_shorts else "scale=1280:720"

    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-fflags", "+genpts",
        "-re",
        "-i", video_path,
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "zerolatency",
        "-b:v", "2500k",
        "-maxrate", "2500k",
        "-bufsize", "5000k",
        "-g", "60",
        "-keyint_min", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-f", "flv",
        "-flvflags", "no_duration_filesize",
        "-use_wallclock_as_timestamps", "1",
        output_url
    ]

    log_callback(f"Menjalankan: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_callback(line.strip())
        process.wait()
    except Exception as e:
        log_callback(f"Error: {e}")
    finally:
        log_callback("Streaming selesai atau dihentikan.")

def main():
    st.set_page_config(page_title="Streaming YouTube Live", page_icon="🎥", layout="wide")

    # Konfigurasi Upload
    st.markdown("""
        <style>
        .main {
            background-color: #f5f7f9;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🎥 Live Streaming YouTube (G-Drive Support)")

    # Iklan Sponsor
    show_ads = st.checkbox("Tampilkan Iklan", value=False)
    if show_ads:
        components.html(
            """
            <div style="background:#fff;padding:10px;border-radius:10px;text-align:center;border:1px solid #ddd">
                <script type='text/javascript' src='//pl26562103.profitableratecpm.com/28/f9/95/28f9954a1d5bbf4924abe123c76a68d2.js'></script>
                <p style="color:#888;font-size:12px">Iklan Sponsor</p>
            </div>
            """, height=200
        )

    # --- INPUT SELECTION ---
    st.subheader("1. Pilih Sumber Video")
    source_option = st.radio("Metode Input:", ["Google Drive Link", "Upload Manual", "Pilih File Server"])

    video_path = None

    if source_option == "Google Drive Link":
        gdrive_url = st.text_input("Masukkan URL Google Drive (Pastikan Akses: Anyone with link/Publik)", 
                                  placeholder="https://drive.google.com/file/d/xxxx/view?usp=sharing")
        if gdrive_url:
            if st.button("Unduh dari G-Drive"):
                with st.spinner("Sedang mengunduh video dari Google Drive..."):
                    downloaded_file = download_from_gdrive(gdrive_url)
                    if downloaded_file:
                        st.success(f"✅ Berhasil mengunduh: {downloaded_file}")
                        video_path = downloaded_file
    
    elif source_option == "Upload Manual":
        uploaded_file = st.file_uploader("Upload video (mp4/flv)", type=['mp4', 'flv'])
        if uploaded_file:
            video_path = uploaded_file.name
            with open(video_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("✅ File berhasil diunggah!")

    else:
        video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.flv'))]
        if video_files:
            video_path = st.selectbox("Pilih video yang ada di server:", video_files)
        else:
            st.info("Tidak ada file video di server.")

    # --- CONFIGURATION ---
    st.subheader("2. Konfigurasi Streaming")
    col1, col2 = st.columns(2)
    
    with col1:
        stream_key = st.text_input("🔑 YouTube Stream Key", type="password")
    with col2:
        is_shorts = st.checkbox("Mode Shorts (Portrait 720x1280)")

    # --- LOGS & ACTION ---
    log_placeholder = st.empty()
    
    if 'logs' not in st.session_state:
        st.session_state['logs'] = []

    def log_callback(msg):
        st.session_state['logs'].append(msg)
        # Menampilkan 15 baris terakhir
        log_display = "\n".join(st.session_state['logs'][-15:])
        log_placeholder.code(log_display)

    col_btn1, col_btn2 = st.columns(2)

    if col_btn1.button("🚀 MULAI STREAMING", use_container_width=True):
        if not video_path:
            st.error("❌ Pilih atau unduh video terlebih dahulu!")
        elif not stream_key:
            st.error("❌ Stream Key tidak boleh kosong!")
        else:
            if not os.path.exists(video_path):
                st.error(f"❌ File {video_path} tidak ditemukan!")
            else:
                st.session_state['logs'] = ["Memulai sesi streaming..."]
                thread = threading.Thread(
                    target=run_ffmpeg,
                    args=(video_path, stream_key, is_shorts, log_callback),
                    daemon=True
                )
                thread.start()
                st.success("✅ Proses FFmpeg dijalankan di background!")

    if col_btn2.button("🛑 STOP STREAMING", use_container_width=True, type="primary"):
        os.system("pkill ffmpeg")
        st.warning("⚠️ Perintah penghentian dikirim ke FFmpeg.")

    # Tampilkan log yang sudah ada
    if st.session_state['logs']:
        log_placeholder.code("\n".join(st.session_state['logs'][-15:]))

if __name__ == '__main__':
    main()