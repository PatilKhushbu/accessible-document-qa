import streamlit as st
import streamlit.components.v1 as components
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from pypdf import PdfReader
import os

st.set_page_config(page_title="Accessible Document Assistant", page_icon="🔊", layout="centered")

st.sidebar.title("⚙️ Accessibility Settings")
font_size = st.sidebar.slider("Text size", 16, 40, 20)
theme = st.sidebar.radio("Contrast theme", ["Soft dark (amber)", "Light (black on white)", "Cream"])
st.sidebar.markdown("---")
st.sidebar.markdown("**How to use**")
st.sidebar.markdown("1. Click *Start voice input*\n2. Speak your question\n3. Press Enter\n4. Listen to the answer")

if theme == "Soft dark (amber)":
    bg, fg, accent, inputbg, card = "#0d1117", "#f0d080", "#e8b84b", "#161b22", "#1c2330"
elif theme == "Light (black on white)":
    bg, fg, accent, inputbg, card = "#ffffff", "#1a1a1a", "#0057d9", "#f2f4f6", "#eef2f8"
else:
    bg, fg, accent, inputbg, card = "#fdf6e3", "#3a3a3a", "#b5730a", "#faf3dd", "#f4ecd4"

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg}; }}
    h1,h2,h3,p,label,div,li {{ color: {fg} !important; font-size: {font_size}px !important;
        font-family: 'Segoe UI', system-ui, sans-serif !important; }}
    h1 {{ font-size: {font_size + 18}px !important; font-weight: 800 !important; }}
    .block-container {{ padding-top: 2.5rem !important; max-width: 780px; }}
    .stTextInput input {{
        font-size: {font_size}px !important; background:{inputbg} !important; color:{fg} !important;
        border: 3px solid {accent} !important; padding: 0.7rem !important; border-radius: 10px !important;
    }}
    section[data-testid="stSidebar"] {{ background-color: {card} !important; }}
    .hero {{ background: {card}; border-left: 6px solid {accent}; padding: 1.2rem 1.4rem;
        border-radius: 12px; margin-bottom: 1.4rem; }}
    .answer-card {{ background: {card}; border: 2px solid {accent}; border-radius: 14px;
        padding: 1.4rem 1.6rem; margin-top: 1rem; }}
    .badge {{ display:inline-block; background:{accent}; color:#000; padding:4px 12px;
        border-radius:20px; font-weight:700; font-size:{font_size-4}px; margin:3px 4px 3px 0; }}
</style>
""", unsafe_allow_html=True)

st.markdown("# 🔊 Accessible Document Q&A Assistant")
st.markdown(f"""
<div class="hero">
An AI assistant designed for <b>blind and partially sighted users</b>. Ask questions about a document
by <b>voice</b>, and hear the answer <b>read aloud</b>. Runs fully offline on your own computer.
<br><br>
<span class="badge">🎤 Voice input</span>
<span class="badge">🔈 Reads answers aloud</span>
<span class="badge">🔆 Adjustable contrast</span>
<span class="badge">🔒 Private & offline</span>
</div>
""", unsafe_allow_html=True)

@st.cache_resource
def build_index():
    texts = []
    for filename in os.listdir("data"):
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(os.path.join("data", filename))
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    texts.append(content)
    full_text = "\n".join(texts)
    chunks = [Document(page_content=full_text[i:i + 1200]) for i in range(0, len(full_text), 1000)]
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return Chroma.from_documents(chunks, embeddings)

vectorstore = build_index()
retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
llm = ChatOllama(model="llama3.2")

prompt = ChatPromptTemplate.from_template(
    "Answer the question using only the context below. "
    "If the answer isn't in the context, say you don't know.\n\n"
    "Context:\n{context}\n\nQuestion: {question}"
)

components.html(f"""
<button onclick="startVoice()" style="font-size:{font_size+2}px;background:{accent};color:#000;
    padding:0.9rem 1.8rem;font-weight:bold;border:none;cursor:pointer;border-radius:10px;
    box-shadow:0 3px 8px rgba(0,0,0,0.25);">🎤 Start voice input</button>
<p id="status" style="color:{fg};font-size:{font_size}px;margin-top:14px;font-family:Segoe UI,sans-serif;"></p>
<script>
function startVoice() {{
    const r = new (window.SpeechRecognition||window.webkitSpeechRecognition)();
    r.lang='en-US';
    document.getElementById('status').innerText='🎧 Listening... please speak now.';
    r.onresult=function(e){{
        const text=e.results[0][0].transcript;
        document.getElementById('status').innerText='✓ You said: '+text;
        const box = window.parent.document.querySelector('input[type=text]');
        if (box) {{
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
            setter.call(box, text);
            box.dispatchEvent(new Event('input', {{bubbles:true}}));
        }}
    }};
    r.onerror=function(e){{document.getElementById('status').innerText='⚠️ Voice error: '+e.error;}};
    r.start();
}}
</script>
""", height=150)

question = st.text_input("💬 Your question (press Enter after voice fills it):")

if question:
    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)
    message = prompt.format(context=context, question=question)
    answer = llm.invoke(message).content

    st.markdown(f"""
    <div class="answer-card">
    <p style="color:{accent};font-weight:800;margin:0 0 6px 0;">QUESTION</p>
    <p style="margin:0 0 16px 0;">{question}</p>
    <p style="color:{accent};font-weight:800;margin:0 0 6px 0;">🔈 ANSWER</p>
    <p style="margin:0;">{answer}</p>
    </div>
    """, unsafe_allow_html=True)

    safe = answer.replace("\\", " ").replace("`", " ").replace("\n", " ").replace('"', "'")
    components.html(f"""
    <script>
    const u = new SpeechSynthesisUtterance("{safe}");
    u.rate = 0.95;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
    </script>
    """, height=0)