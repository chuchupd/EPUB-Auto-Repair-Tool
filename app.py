import streamlit as st
import io
from pathlib import Path
from fix_epub import EPUBRepairer

# --- Page Configuration ---
st.set_page_config(
    page_title="EPUB Auto Repair Tool",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Custom Styling ---
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .upload-container {
        border: 2px dashed #4CAF50;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        background-color: white;
    }
    h1 {
        color: #2c3e50;
        text-align: center;
        font-family: 'Inter', sans-serif;
    }
    .status-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- UI Header ---
st.title("📚 EPUB Auto Repair Tool")
st.markdown("**EPUB 구조 및 XHTML 자동 복구 도구**입니다.")

# --- GitHub & README Section ---
with st.expander("📖 도구 사용 설명 및 정보 (README)"):
    try:
        readme_content = Path("README.md").read_text(encoding="utf-8")
        st.markdown(readme_content)
    except Exception:
        st.warning("README.md 파일을 불러올 수 없습니다.")
    
    st.markdown("---")
    st.markdown("### 🔗 GitHub 저장소")
    st.markdown("[chuchupd/EPUB-Auto-Repair-Tool](https://github.com/chuchupd/EPUB-Auto-Repair-Tool)")

# --- File Uploader ---
uploaded_files = st.file_uploader(
    "복구가 필요한 EPUB 파일을 업로드하세요 (여러 파일 가능)",
    type=["epub"],
    accept_multiple_files=True
)

if uploaded_files:
    st.divider()
    st.subheader(f"🛠️ 복구 대기 중: {len(uploaded_files)}개 파일")
    
    if st.button("모든 파일 복구 시작"):
        repairer = EPUBRepairer()
        results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            try:
                status_text.text(f"처리 중: {uploaded_file.name}...")
                
                # Input buffer from Streamlit
                input_bytes = uploaded_file.getvalue()
                input_buffer = io.BytesIO(input_bytes)
                
                # Repair logic
                output_buffer, changed_count, notes = repairer.process_buffer(input_buffer, uploaded_file.name)
                
                results.append({
                    "name": uploaded_file.name,
                    "buffer": output_buffer,
                    "changed": changed_count,
                    "notes": notes,
                    "success": True
                })
                
            except Exception as e:
                results.append({
                    "name": uploaded_file.name,
                    "error": str(e),
                    "success": False
                })
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_text.text("✅ 모든 작업이 완료되었습니다.")
        st.success(f"{len(results)}개 파일 처리 완료!")
        
        # --- Results Display ---
        st.divider()
        st.subheader("📦 결과 다운로드")
        
        for res in results:
            with st.container():
                if res["success"]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{res['name']}**")
                        st.caption(f"수정된 항목: {res['changed']}개 | 주요 이슈: {', '.join(res['notes'][:3])}...")
                    with col2:
                        st.download_button(
                            label="다운로드",
                            data=res["buffer"].getvalue(),
                            file_name=res["name"],
                            mime="application/epub+zip",
                            key=f"dl_{res['name']}"
                        )
                else:
                    st.error(f"❌ {res['name']} 처리 실패: {res['error']}")
                st.markdown("---")

else:
    st.info("파일을 업로드하면 수리 버튼이 활성화됩니다.")

# --- Footer ---
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #7f8c8d; font-size: 0.8rem;'>
        &copy; 2024 EPUB Auto Repair Tool | Made with ❤️ for Publishers
    </div>
    """,
    unsafe_allow_html=True
)
