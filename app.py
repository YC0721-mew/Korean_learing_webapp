import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import random
import json
import os

# --- 設定區 ---
st.set_page_config(page_title="我的韓文 App", layout="wide", page_icon="🇰🇷")
st.title("🇰🇷 韓文學習中心")

# --- 連線函式 (雲端/本地 雙棲版) ---
@st.cache_resource
def init_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 判斷：如果電腦裡有鑰匙檔案，就用檔案 (本地模式 - Codespaces)
    if os.path.exists('google_key.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name('google_key.json', scope)
    
    # 如果沒有檔案，就去讀取雲端的秘密倉庫 (雲端模式 - Streamlit Cloud)
    else:
        # 這裡會去讀取我們剛剛在網頁上設定的 Secrets
        key_dict = json.loads(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    
    client = gspread.authorize(creds)
    return client

# --- 主程式邏輯：連線並下載資料 ---
try:
    client = init_connection()
    sheet = client.open("Korean_App_DB").sheet1
    
    # 讀取全部資料
    data = sheet.get_all_records()
    
    # ★ 關鍵修復：確保 df 這裡被定義，且處理空資料的情況
    if data:
        df = pd.DataFrame(data)
    else:
        # 如果 Google Sheet 是全空的，手動建立一個空的 DataFrame，防止報錯
        df = pd.DataFrame(columns=["單字", "解釋", "詞性", "例句", "類別", "熟悉度"])

except Exception as e:
    st.error(f"連線發生錯誤，請檢查 Secrets 設定或 Google Sheet 名稱。錯誤訊息：{e}")
    st.stop()

# --- 介面分頁 ---
tab1, tab2, tab3 = st.tabs(["📥 新增與列表", "🧠 記憶卡抽考", "🏋️‍♀️ 例句填空"])

# ==========================================
# 功能 1: 新增與列表
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
                # 對應你的 Google Sheet 欄位順序
                new_data = [new_word, new_meaning, new_type, new_sentence, "一般", 0]
                sheet.append_row(new_data)
                st.success(f"已儲存：{new_word}")
                st.rerun()

    with col2:
        st.subheader("📚 你的寶庫")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("目前還沒有資料喔！")

# ==========================================
# 功能 2: 記憶卡抽考
# ==========================================
with tab2:
    st.header("🧠 記憶抽考模式")
    
    if df.empty:
        st.warning("請先去第一頁新增一點單字吧！")
    else:
        if 'quiz_word' not in st.session_state:
            st.session_state['quiz_word'] = df.sample(1).iloc[0]
            st.session_state['show_answer'] = False

        col_a, col_b = st.columns(2)
        if col_a.button("🔄 換一題"):
            st.session_state['quiz_word'] = df.sample(1).iloc[0]
            st.session_state['show_answer'] = False
            st.rerun()

        current_word = st.session_state['quiz_word']
        
        st.divider()
        st.markdown(f"<h1 style='text-align: center; color: #4A90E2;'>{current_word['單字']}</h1>", unsafe_allow_html=True)
        st.write("") 
        
        if st.button("👀 看答案"):
            st.session_state['show_answer'] = True
        
        if st.session_state['show_answer']:
            st.success(f"解釋：{current_word['解釋']}")
            st.info(f"詞性：{current_word['詞性']}")
            if current_word['例句']:
                st.warning(f"例句：{current_word['例句']}")
            else:
                st.caption("這題沒有例句")

# ==========================================
# 功能 3: 例句填空
# ==========================================
with tab3:
    st.header("🏋️‍♀️ 例句克漏字練習")
    
    # 先檢查 df 是否為空，再篩選
    if df.empty:
        st.warning("資料庫是空的，無法練習。")
    else:
        df_sentences = df[df['例句'] != ""]
        
        if df_sentences.empty:
            st.warning("你還沒有輸入任何例句喔！")
        else:
            if 'cloze_word' not in st.session_state:
                st.session_state['cloze_word'] = df_sentences.sample(1).iloc[0]
                st.session_state['check_result'] = None

            if st.button("🔄 換句練習", key="next_sentence"):
                st.session_state['cloze_word'] = df_sentences.sample(1).iloc[0]
                st.session_state['check_result'] = None
                st.rerun()

            target = st.session_state['cloze_word']
            word = target['單字']
            sentence = target['例句']
            
            cloze_sentence = sentence.replace(word, " ______ ")
            
            st.markdown(f"### {cloze_sentence}")
            # 這裡已經修復為正確的欄位名稱 '解釋'
            st.write(f"提示：{target['解釋']}")
            
            user_input = st.text_input("請填入正確韓文：")
            
            if st.button("送出檢查"):
                if user_input.strip() == word:
                    st.balloons()
                    st.success(f"答對了！完整句子：{sentence}")
                else:
                    st.error(f"可惜！正確答案是：{word}")
                    st.text(f"完整句子：{sentence}")