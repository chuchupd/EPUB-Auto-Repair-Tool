import streamlit as st
import io
from pathlib import Path
from modules.repairer import EPUBRepairer
from modules.converter import TXTToEPUBConverter

# --- Page Configuration ---
st.set_page_config(
    page_title="EPUB Master",
    page_icon="💎",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Custom Styling (Black & Green Master Theme) ---
st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0E1117;
        color: #E0E0E0;
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at top right, #1a2a24, #0E1117);
    }

    /* Titles & Headers */
    h1 {
        color: #00FFA3 !important;
        font-weight: 900 !important;
        text-align: center;
        letter-spacing: -1px;
        margin-bottom: 0.5rem !important;
    }
    
    .slogan {
        text-align: center;
        color: #7F8C8D;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Custom Selection Cards */
    .nav-container {
        display: flex;
        gap: 20px;
        justify-content: center;
        padding: 20px 0;
    }
    
    .nav-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(0, 255, 163, 0.2);
        border-bottom: none; /* Join with button */
        border-radius: 15px 15px 0 0;
        padding: 40px 20px;
        width: 100%;
        text-align: center;
        transition: all 0.4s ease;
        backdrop-filter: blur(10px);
        min-height: 250px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .nav-card:hover {
        border-color: #00FFA3;
        background: rgba(0, 255, 163, 0.05);
    }
    
    /* Eliminate Streamlit's default gap between elements */
    [data-testid="stVerticalBlock"] > div:has(.nav-card) + div {
        margin-top: -1rem !important;
    }
    
    .icon {
        font-size: 3.5rem;
        margin-bottom: 20px;
        filter: drop-shadow(0 0 10px rgba(0, 255, 163, 0.3));
    }
    
    .card-title {
        color: #00FFA3;
        font-size: 1.6rem;
        font-weight: 800;
        margin-bottom: 12px;
        letter-spacing: -0.5px;
    }
    
    .card-desc {
        color: #A0A0A0;
        font-size: 0.95rem;
        line-height: 1.5;
        max-width: 240px;
    }

    /* Streamlit Component Overrides */
    .stButton>button {
        background-color: rgba(255, 255, 255, 0.03) !important;
        color: #00FFA3 !important;
        border: 1px solid rgba(0, 255, 163, 0.2) !important;
        border-top: none !important; /* Join with card */
        font-weight: bold !important;
        border-radius: 0 0 15px 15px !important;
        height: 4rem !important;
        transition: 0.3s !important;
        width: 100%;
        font-size: 1.1rem !important;
    }
    
    .stButton>button:hover {
        background-color: #00FFA3 !important;
        color: #0E1117 !important;
        border-color: #00FFA3 !important;
        box-shadow: 0 10px 20px rgba(0, 255, 163, 0.2) !important;
    }

    /* Dark Mode Inputs */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #1A1C23 !important;
        color: #EEE !important;
        border: 1px solid #333 !important;
    }
    
    .stDivider {
        border-top: 1px solid #333 !important;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: #1A1C23 !important;
        border: 1px solid #333 !important;
        border-radius: 5px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = 'Home'

def set_mode(mode):
    st.session_state.app_mode = mode

# --- UI Header ---
if st.session_state.app_mode == 'Home':
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1>💎 EPUB Master</h1>", unsafe_allow_html=True)
    st.markdown("<p class='slogan'>The Ultimate Solution for EPUB Generation & Repair</p>", unsafe_allow_html=True)
else:
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("⬅ Home"):
            set_mode('Home')
            st.rerun()
    with col_title:
        st.markdown(f"<h1>💎 EPUB Master</h1>", unsafe_allow_html=True)

st.sidebar.caption("v2.1 (Master Edit Active)")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠 Navigation")
if st.sidebar.button("🏠 Home Screen"):
    set_mode('Home')
    st.rerun()
if st.sidebar.button("✍️ Generate EPUB"):
    set_mode('Convert')
    st.rerun()
if st.sidebar.button("🛠 Repair EPUB"):
    set_mode('Repair')
    st.rerun()

# --- Content Logic ---
if st.session_state.app_mode == 'Home':
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Custom HTML for fancy selection cards (since buttons can't easily contain rich HTML in standard st.button)
    # We use Streamlit columns with buttons inside for functionality, but style them as cards.
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="nav-card">
            <div class="icon">✍️</div>
            <div class="card-title">Generate EPUB</div>
            <div class="card-desc">TXT 파일을 고품질 정식 EPUB으로 즉시 변환합니다.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start Generating", key="go_convert", use_container_width=True):
            set_mode('Convert')
            st.rerun()

    with col2:
        st.markdown("""
        <div class="nav-card">
            <div class="icon">🛠</div>
            <div class="card-title">Repair EPUB</div>
            <div class="card-desc">손상되거나 검증에 실패한 EPUB 파일을 자동 복구합니다.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start Repairing", key="go_repair", use_container_width=True):
            set_mode('Repair')
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("📖 Information & Documentation"):
        try:
            readme = Path("README.md").read_text(encoding="utf-8")
            st.markdown(readme)
        except:
            st.warning("README not found")

elif st.session_state.app_mode == 'Repair':
    st.subheader("🛠 EPUB Auto Repair")
    st.info("복구가 필요한 EPUB 파일을 업로드하세요. 오류를 분석하여 최신 규격으로 자동 교정합니다.")
    
    uploaded_files = st.file_uploader(
        "Upload EPUB files",
        type=["epub"],
        accept_multiple_files=True,
        key="repair_uploader"
    )

    if uploaded_files:
        if st.button("Start Repairing All", key="start_repair"):
            repairer = EPUBRepairer()
            results = []
            progress_bar = st.progress(0)
            
            for idx, uploaded_file in enumerate(uploaded_files):
                try:
                    input_buffer = io.BytesIO(uploaded_file.getvalue())
                    output_buffer, changed_count, notes = repairer.process_buffer(input_buffer, uploaded_file.name)
                    results.append({
                        "name": uploaded_file.name,
                        "buffer": output_buffer,
                        "changed": changed_count,
                        "notes": notes,
                        "success": True
                    })
                except Exception as e:
                    results.append({"name": uploaded_file.name, "error": str(e), "success": False})
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
            st.success(f"{len(results)} files processed successfully.")
            
            for res in results:
                with st.container():
                    if res["success"]:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{res['name']}**")
                            st.caption(f"Changes: {res['changed']} | Issues: {', '.join(res['notes'][:3])}...")
                        with col2:
                            st.download_button("Download", res["buffer"].getvalue(), res["name"], "application/epub+zip", key=f"dl_{res['name']}")
                    else:
                        st.error(f"❌ {res['name']} failed: {res['error']}")
                    st.divider()

elif st.session_state.app_mode == 'Convert':
    st.subheader("✍️ TXT to EPUB Conversion")
    st.info("TXT 파일을 업로드하면 도서 정보를 분석하고 규격에 맞는 고품질 EPUB을 생성합니다.")
    
    txt_file = st.file_uploader("Upload TXT file", type=["txt"], key="txt_uploader")
    
    if txt_file:
        converter = TXTToEPUBConverter()
        txt_bytes = txt_file.getvalue()
        text = ""
        for enc in ["utf-8", "cp949", "euc-kr", "utf-16"]:
            try:
                text = txt_bytes.decode(enc)
                break
            except: continue
        if not text: text = txt_bytes.decode("utf-8", errors="replace")

        auto_meta = converter.extract_metadata(text)
        
        if "meta" not in st.session_state or st.session_state.get("last_txt") != txt_file.name:
            st.session_state.meta = {
                "title": auto_meta.get("title", ""),
                "author": auto_meta.get("author", ""),
                "description": "",
                "publisher": "",
                "cover_url": None
            }
            st.session_state.last_txt = txt_file.name
        
        st.divider()
        col_meta, col_cover = st.columns([2, 1])
        
        with col_meta:
            title = st.text_input("Title", value=st.session_state.meta["title"])
            author = st.text_input("Author", value=st.session_state.meta["author"])
            if st.session_state.meta.get("description"):
                with st.expander("Description"): st.write(st.session_state.meta["description"])

        with col_cover:
            cover_opt = st.radio("Cover Option", ["Auto Search", "Custom Upload", "No Cover"])
            cover_bytes = None
            if cover_opt == "Auto Search":
                if st.button("Search Online"):
                    with st.spinner("Searching..."):
                        search_res = converter.search_cover(title, author)
                        if search_res and search_res.get("cover_url"):
                            st.session_state.meta.update(search_res)
                            st.rerun()
                if st.session_state.meta["cover_url"]:
                    st.image(st.session_state.meta["cover_url"], width=120)
            elif cover_opt == "Custom Upload":
                custom_cover = st.file_uploader("Image (JPG/PNG)", type=["jpg", "jpeg", "png"])
                if custom_cover:
                    cover_bytes = custom_cover.read()
                    st.image(cover_bytes, width=120)

        if st.button("🚀 Convert to EPUB"):
            with st.spinner("Creating EPUB..."):
                try:
                    final_meta = {
                        "title": title, "author": author,
                        "description": st.session_state.meta.get("description", ""),
                        "publisher": st.session_state.meta.get("publisher", "")
                    }
                    c_url = st.session_state.meta.get("cover_url") if cover_opt == "Auto Search" else None
                    c_bytes = cover_bytes if cover_opt == "Custom Upload" else None
                    
                    epub_buf = converter.to_epub(text, final_meta, cover_url=c_url, cover_bytes=c_bytes)
                    st.session_state.epub_result = {"buffer": epub_buf.getvalue(), "filename": f"{title}.epub"}
                    st.success("🎉 Conversion Success!")
                except Exception as e:
                    st.error(f"Error: {e}")

        if "epub_result" in st.session_state:
            res = st.session_state.epub_result
            st.download_button("📦 Download Result", res["buffer"], res["filename"], "application/epub+zip")

# --- Footer ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style='text-align: center; color: #444; font-size: 0.8rem; border-top: 1px solid #222; padding-top: 20px;'>
        🛡️ <b>EPUB Master v2.1</b> | Made by chris | <a href='https://github.com/chuchupd/EPUB-Auto-Repair-Tool' target='_blank' style='color: #00FFA3; text-decoration: none;'>GitHub</a>
    </div>
    """,
    unsafe_allow_html=True
)
