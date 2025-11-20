import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import random
import json
import os
import google.generativeai as genai # 新增 AI 工具包

# --- 設定區 ---
st.set_page_config(page_title="我的韓文 App", layout="wide", page_icon="🇰🇷")
st.title("🇰🇷 韓文學習中心 2.0 (AI版)")

# --- 1. 設定 Google Sheet 連線 ---
@st.cache_resource
def init_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    if os.path.exists('google_key.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name('google_key.json', scope)
    else:
        key_dict = json.loads(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    return gspread.authorize(creds)

# --- 2. 設定 Gemini AI ---
# 嘗試設定 AI Key，如果還沒設定 Secrets 就不會崩潰，只是 AI 功能不能用
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        has_ai_key = True
    else:
        has_ai_key = False
except:
    has_ai_key = False

# --- 主程式邏輯 ---
try:
    client = init_connection()
    sheet = client.open("Korean_App_DB").sheet1
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(columns=["單字", "解釋", "詞性", "例句", "類別", "熟悉度"])
except Exception as e:
    st.error(f"資料庫連線錯誤：{e}")
    st.stop()

# --- 介面分頁 ---
tab1, tab2, tab3, tab4 = st.tabs(["📥 新增與列表", "🧠 記憶卡抽考", "🏋️‍♀️ 例句填空", "🤖 AI 智慧備課"])

# ==========================================
# Tab 1: 新增與列表
# ==========================================
with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("✍️ 手動存入")
        with st.form("entry_form"):
            new_word = st.text_input("韓文單字/文法")
            new_meaning = st.text_input("中文解釋")
            new_type = st.selectbox("詞性", ["單字", "文法", "短語"])
            new_sentence = st.text_area("情境例句")
            if st.form_submit_button("💾 存檔"):
                sheet.append_row([new_word, new_meaning, new_type, new_sentence, "一般", 0])
                st.success(f"已儲存：{new_word}")
                st.rerun()

    with col2:
        st.subheader("📚 你的寶庫")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("目前還沒有資料喔！")

# ==========================================
# Tab 2: 記憶卡抽考
# ==========================================
with tab2:
    st.header("🧠 記憶抽考模式")
    if df.empty:
        st.warning("無資料")
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
        
        if st.button("👀 看答案"):
            st.session_state['show_answer'] = True
        
        if st.session_state['show_answer']:
            st.success(f"解釋：{current_word['解釋']}")
            st.info(f"詞性：{current_word['詞性']}")
            st.warning(f"例句：{current_word['例句']}")

# ==========================================
# Tab 3: 例句填空
# ==========================================
with tab3:
    st.header("🏋️‍♀️ 例句克漏字")
    if df.empty:
        st.warning("無資料")
    else:
        df_sentences = df[df['例句'] != ""]
        if df_sentences.empty:
            st.warning("沒例句")
        else:
            if 'cloze_word' not in st.session_state:
                st.session_state['cloze_word'] = df_sentences.sample(1).iloc[0]
            
            if st.button("🔄 換句"):
                st.session_state['cloze_word'] = df_sentences.sample(1).iloc[0]
                st.rerun()

            target = st.session_state['cloze_word']
            cloze = target['例句'].replace(target['單字'], " ______ ")
            st.markdown(f"### {cloze}")
            st.write(f"提示：{target['解釋']}")
            
            ans = st.text_input("答案：")
            if st.button("檢查"):
                if ans.strip() == target['單字']:
                    st.balloons()
                    st.success("答對了！")
                else:
                    st.error(f"錯了，是：{target['單字']}")

# ==========================================
# Tab 4: AI 智慧備課 (全新功能！)
# ==========================================
with tab4:
    st.header("🤖 AI 每日單字生成")
    st.write("點擊按鈕，AI 會幫你生成 5 個實用韓文單字（包含例句），並直接存入資料庫！")
    
    if not has_ai_key:
        st.error("⚠️ 尚未設定 GEMINI_API_KEY。請去 Streamlit Cloud Settings -> Secrets 設定。")
    else:
        # 使用者可以輸入主題
        topic = st.text_input("想學什麼主題？(例如：旅遊、點餐、職場，留空則隨機)", "生活韓語")
        
        if st.button("🔮 開始生成 (約需 5-10 秒)"):
            with st.spinner("AI 老師正在思考中..."):
                try:
                    # 1. 呼叫 Gemini
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"""
                    請給我 5 個與「{topic}」相關的韓文單字。
                    格式必須是純 JSON Array，不要有 markdown 標記。
                    每個物件包含以下欄位：
                    - "word" (韓文單字)
                    - "meaning" (繁體中文解釋)
                    - "type" (詞性)
                    - "sentence" (一句簡單實用的韓文例句)
                    """
                    response = model.generate_content(prompt)
                    
                    # 2. 處理回傳文字 (去除可能的 markdown 符號)
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text[7:-3]
                    
                    words_list = json.loads(text)
                    
                    # 3. 寫入資料庫
                    count = 0
                    for item in words_list:
                        # 檢查是否已經存在 (簡單檢查)
                        if item['word'] not in df['單字'].values:
                            sheet.append_row([
                                item['word'], 
                                item['meaning'], 
                                item['type'], 
                                item['sentence'], 
                                topic, 
                                0
                            ])
                            count += 1
                    
                    st.success(f"🎉 成功新增了 {count} 個單字！快去「列表」查看吧！")
                    st.json(words_list) # 顯示剛剛生成的內容給你看
                    
                except Exception as e:
                    st.error(f"生成失敗，請再試一次。錯誤原因：{e}")