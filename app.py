import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import random
import json # 新增這個
import os   # 新增這個

# --- 設定區 ---
st.set_page_config(page_title="我的韓文 App", layout="wide", page_icon="🇰🇷")
st.title("🇰🇷 韓文學習中心")

# --- 連線函式 (雙棲版) ---
@st.cache_resource
def init_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 判斷：如果電腦裡有鑰匙檔案，就用檔案 (本地模式)
    if os.path.exists('google_key.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name('google_key.json', scope)
    
    # 如果沒有檔案，就去讀取雲端的秘密倉庫 (雲端模式)
    else:
        # 這裡我們會把鑰匙內容存在 Streamlit 的 Secrets 裡
        key_dict = json.loads(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    
    client = gspread.authorize(creds)
    return client

# --- 介面分頁 ---
tab1, tab2, tab3 = st.tabs(["📥 新增與列表", "🧠 記憶卡抽考", "🏋️‍♀️ 例句填空"])

# ==========================================
# 功能 1: 新增與列表 (原本的功能)
# ==========================================
with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("✍️ 存入新知識")
        with st.form("entry_form"):
            new_word = st.text_input("韓文單字/文法")
            new_meaning = st.text_input("中文解釋")
            new_type = st.selectbox("詞性", ["單字", "文法", "短語"])
            new_sentence = st.text_area("情境例句 (重要！)")
            submitted = st.form_submit_button("💾 存檔")
            
            if submitted and new_word and new_meaning:
                new_data = [new_word, new_meaning, new_type, new_sentence, "一般", 0]
                sheet.append_row(new_data)
                st.success(f"已儲存：{new_word}")
                st.rerun() # 重新整理頁面

    with col2:
        st.subheader("📚 你的寶庫")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("目前還沒有資料喔！")

# ==========================================
# 功能 2: 記憶卡抽考 (解決痛點 a)
# ==========================================
with tab2:
    st.header("🧠 記憶抽考模式")
    
    if df.empty:
        st.warning("請先去第一頁新增一點單字吧！")
    else:
        # 初始化：如果 Session State 裡還沒有 'quiz_word'，就隨機抓一個
        if 'quiz_word' not in st.session_state:
            st.session_state['quiz_word'] = df.sample(1).iloc[0]
            st.session_state['show_answer'] = False

        # 顯示按鈕區
        col_a, col_b = st.columns(2)
        
        # 下一題按鈕
        if col_a.button("🔄 換一題"):
            st.session_state['quiz_word'] = df.sample(1).iloc[0]
            st.session_state['show_answer'] = False
            st.rerun()

        # 顯示卡片
        current_word = st.session_state['quiz_word']
        
        st.divider()
        # 題目區 (字體放大)
        st.markdown(f"<h1 style='text-align: center; color: #4A90E2;'>{current_word['單字']}</h1>", unsafe_allow_html=True)
        
        st.write("") # 空行
        
        # 互動按鈕：看答案
        if st.button("👀 看答案"):
            st.session_state['show_answer'] = True
        
        # 答案區
        if st.session_state['show_answer']:
            st.success(f"解釋：{current_word['解釋']}")
            st.info(f"詞性：{current_word['詞性']}")
            if current_word['例句']:
                st.warning(f"例句：{current_word['例句']}")
            else:
                st.caption("這題沒有例句，之後記得補上喔！")

# ==========================================
# 功能 3: 例句填空 (解決痛點 c)
# ==========================================
with tab3:
    st.header("🏋️‍♀️ 例句克漏字練習")
    st.caption("系統會把你存的例句挖空，讓你填入正確的韓文。")
    
    # 篩選出有例句的資料
    df_sentences = df[df['例句'] != ""]
    
    if df_sentences.empty:
        st.warning("你還沒有輸入任何例句喔！去第一頁新增單字時，記得填寫「情境例句」。")
    else:
        if 'cloze_word' not in st.session_state:
            st.session_state['cloze_word'] = df_sentences.sample(1).iloc[0]
            st.session_state['check_result'] = None

        # 換題按鈕
        if st.button("🔄 換句練習", key="next_sentence"):
            st.session_state['cloze_word'] = df_sentences.sample(1).iloc[0]
            st.session_state['check_result'] = None
            st.rerun()

        target = st.session_state['cloze_word']
        word = target['單字']
        sentence = target['例句']
        
        # 製作挖空句子 (簡單版：把單字替換成底線)
        cloze_sentence = sentence.replace(word, " ______ ")
        
        st.markdown(f"### {cloze_sentence}")
        st.write(f"提示：{target['解釋']}")
        
        # 使用者輸入
        user_input = st.text_input("請填入正確韓文：")
        
        if st.button("送出檢查"):
            if user_input.strip() == word:
                st.balloons() # 答對會放氣球！
                st.success(f"答對了！完整句子：{sentence}")
            else:
                st.error(f"可惜！正確答案是：{word}")
                st.text(f"完整句子：{sentence}")