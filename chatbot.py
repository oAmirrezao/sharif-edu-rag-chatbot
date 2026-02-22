# chatbot.py — نسخه نهایی
import pickle
import numpy as np
import faiss
import gradio as gr
from sentence_transformers import SentenceTransformer
from groq import Groq

# ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = "--"
LLM_MODEL    = "qwen-qwq-32b"
EMBED_MODEL  = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
INDEX_FILE   = "faiss.index"
META_FILE    = "chunks_meta.pkl"
TOP_K        = 7
# ─────────────────────────────────────────────────────────────────

print("📥 Embedding model (CPU)...")
embed_model = SentenceTransformer(EMBED_MODEL, device='cpu')

print("📂 FAISS index...")
index = faiss.read_index(INDEX_FILE)
with open(META_FILE, 'rb') as f:
    chunks = pickle.load(f)

print("🔗 اتصال به Groq API...")
client = Groq(api_key=GROQ_API_KEY)
print(f"✅ آماده! (مدل: {LLM_MODEL})")


# ─────────────────────────────────────────────────────────────────
def retrieve(question: str, top_k: int = TOP_K) -> list:
    q_emb = embed_model.encode(
        [question], normalize_embeddings=True
    ).astype(np.float32)
    scores, idxs = index.search(q_emb, top_k)
    return [
        {"chunk": chunks[i], "score": float(s)}
        for s, i in zip(scores[0], idxs[0]) if i < len(chunks)
    ]


def build_context(retrieved: list) -> str:
    parts = []
    for item in retrieved:
        c = item['chunk']
        ref = c['regulation_name']
        if c.get('article_number'):
            ref += f"، {c['article_number']}"
        parts.append(f"[{ref}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def answer(question: str) -> tuple:
    if not question.strip():
        return "سوال وارد نشده است.", ""

    retrieved = retrieve(question)
    context   = build_context(retrieved)

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "شما دستیار آموزشی دانشگاه صنعتی شریف هستید.\n"
                        "قوانین پاسخ‌دهی:\n"
                        "۱. فقط بر اساس متون ارائه‌شده پاسخ دهید.\n"
                        "۲. شماره ماده، بند یا تبصره را حتماً ذکر کنید.\n"
                        "۳. هیچ قانون یا تفسیری خارج از متن نسازید.\n"
                        "۴. اگر پاسخ در متون نبود بنویسید: «در آیین‌نامه موجود مطلبی یافت نشد. نیاز به استعلام از آموزش دارد.»\n"
                        "۵. پاسخ کوتاه، دقیق و مستند باشد."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"متون آیین‌نامه:\n\n{context}\n\n"
                        f"{'─'*40}\n\n"
                        f"سوال دانشجو: {question}\n\n"
                        f"پاسخ (با ذکر شماره ماده/بند):"
                    )
                }
            ],
            max_tokens=800,
            temperature=0.1,
        )
        ans = response.choices[0].message.content.strip()
    except Exception as e:
        ans = f"❌ خطا در API: {str(e)}"

    src = "### 📚 منابع بازیابی‌شده\n"
    for i, item in enumerate(retrieved, 1):
        c = item['chunk']
        src += f"\n**{i}.** {c['regulation_name']}"
        if c.get('article_number'):
            src += f" — {c['article_number']}"
        src += f" *(score: {item['score']:.3f})*\n"
        src += f"> {c['text'][:120]}...\n"

    return ans, src


# ─────────────────────────────────────────────────────────────────
def chat(question: str, history: list) -> tuple:
    if not question.strip():
        return history or [], history or [], "*منابع اینجا نمایش داده می‌شوند.*", ""
    ans, src = answer(question)
    history = history or []
    history.append({"role": "user",      "content": question})
    history.append({"role": "assistant", "content": ans})
    return history, history, src, ""


# ─────────────────────────────────────────────────────────────────
with gr.Blocks(title="چت‌بات شریف") as demo:
    gr.Markdown("# 🎓 چت‌بات راهنمای آموزشی دانشگاه صنعتی شریف")
    gr.Markdown(f"*مدل: {LLM_MODEL} via Groq API*")

    with gr.Row():
        with gr.Column(scale=2):
            chatbot_ui = gr.Chatbot(
                height=480,
                type="messages"
            )
            with gr.Row():
                q_input = gr.Textbox(
                    placeholder="سوال خود را اینجا بنویسید...",
                    label="",
                    scale=4
                )
                send_btn = gr.Button("ارسال", variant="primary", scale=1)
            clear_btn = gr.Button("🗑 پاک کردن")

        with gr.Column(scale=1):
            sources_md = gr.Markdown("*منابع اینجا نمایش داده می‌شوند.*")

    gr.Examples(
        label="نمونه سوالات",
        examples=[
            "حداکثر سنوات مجاز تحصیل در دوره کارشناسی چقدر است؟",
            "شرایط مرخصی تحصیلی چیست؟",
            "در صورت غیبت در امتحان پایان‌ترم چه نمره‌ای ثبت می‌شود؟",
            "آیا می‌توانم بیش از ۲۴ واحد انتخاب کنم؟",
            "شرایط انتقال به شریف چیست؟",
            "شرایط دوره کوآپ چیست؟",
            "معدل لازم برای جلوگیری از مشروطی چقدر است؟",
        ],
        inputs=q_input
    )

    state = gr.State([])
    send_btn.click(chat, [q_input, state], [chatbot_ui, state, sources_md, q_input])
    q_input.submit(chat, [q_input, state], [chatbot_ui, state, sources_md, q_input])
    clear_btn.click(
        lambda: ([], [], "*منابع اینجا نمایش داده می‌شوند.*"),
        outputs=[chatbot_ui, state, sources_md]
    )

if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)
