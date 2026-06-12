import os
from datetime import datetime
from pathlib import Path
import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
if BACKEND_URL:
    if not BACKEND_URL.startswith("http"):
        BACKEND_URL = f"https://{BACKEND_URL}"
    if "onrender.com" in BACKEND_URL and BACKEND_URL.startswith("http://"):
        BACKEND_URL = BACKEND_URL.replace("http://", "https://")
    if BACKEND_URL.endswith("/"):
        BACKEND_URL = BACKEND_URL[:-1]

AGENT_API_KEY = os.getenv("AGENT_API_KEY", "my-secret-key")

AVATAR_PATH = Path(__file__).parent / "avatar.png"
ASSISTANT_AVATAR = str(AVATAR_PATH) if AVATAR_PATH.exists() else "👩‍⚕️"

st.set_page_config(page_title="Long Châu AI Triage", page_icon="💊", layout="centered")

# ---------- Sidebar ----------
with st.sidebar:
    st.title("💊 Long Châu")
    st.caption("AI Middleware Demo — Tư vấn thuốc thông minh")
    st.divider()

    # Backend health check (does not require X-API-Key)
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=3)
        if r.status_code == 200:
            st.success("✅ Backend: online")
        else:
            st.error("⚠️ Backend: lỗi")
    except Exception:
        st.error("❌ Backend: mất kết nối")

    st.divider()
    if st.button("🔄 Cuộc hội thoại mới"):
        st.session_state.history = []
        st.session_state.messages = []
        st.rerun()

    st.caption("Prototype — không thay thế tư vấn y tế chuyên nghiệp.")

# ---------- Session state ----------
if "history" not in st.session_state:
    st.session_state.history = []   # [{role, content}] sent to backend
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content, meta}] for rendering

# ---------- Render history ----------
st.title("💬 Tư vấn thuốc Long Châu")

for msg in st.session_state.messages:
    avatar = ASSISTANT_AVATAR if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        meta = msg.get("meta", {})

        if meta.get("route") == "advisory_handoff":
            if meta.get("safety_gate_triggered"):
                st.caption("⚠️ Câu hỏi cần dược sĩ — được chuyển tự động qua safety gate")
            if meta.get("handoff_summary"):
                with st.expander("📋 Tóm tắt cho dược sĩ"):
                    st.info(meta["handoff_summary"])

        if meta.get("route") == "factual":
            st.caption("ℹ️ Thông tin chung — không thay thế tư vấn chuyên sâu")

        if msg.get("time"):
            st.caption(msg["time"])

# ---------- Chat input ----------
prompt = st.chat_input("Nhập câu hỏi về thuốc...")

if prompt:
    # Render user message immediately
    now = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": prompt, "time": now})
    st.session_state.history.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(now)

    # Call backend
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        with st.spinner("Đang xử lý..."):
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/chat",
                    headers={"X-API-Key": AGENT_API_KEY},
                    json={"message": prompt, "history": st.session_state.history},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()

                route = data.get("route", "")
                # reply_md includes product links as markdown; fallback to reply
                reply = data.get("reply_md") or data.get("reply", "")
                handoff_summary = data.get("handoff_summary")
                safety_triggered = data.get("safety_gate_triggered", False)
                model = data.get("model", "")

                st.markdown(reply)

                if route == "advisory_handoff":
                    if safety_triggered:
                        st.caption("⚠️ Câu hỏi cần dược sĩ — được chuyển tự động qua safety gate")
                    if handoff_summary:
                        with st.expander("📋 Tóm tắt cho dược sĩ"):
                            st.info(handoff_summary)

                if route == "factual":
                    st.caption("ℹ️ Thông tin chung — không thay thế tư vấn chuyên sâu")

                # Save to session
                reply_time = datetime.now().strftime("%H:%M")
                st.caption(reply_time)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply,
                    "time": reply_time,
                    "meta": {
                        "route": route,
                        "handoff_summary": handoff_summary,
                        "safety_gate_triggered": safety_triggered,
                        "model": model,
                    },
                })
                # Use clean reply (no product markdown) in LLM history context
                st.session_state.history.append({"role": "assistant", "content": data.get("reply", reply)})

            except httpx.ConnectError:
                st.error("❌ Mất kết nối backend. Vui lòng thử lại sau.")
            except httpx.TimeoutException:
                st.error("⏱️ Backend phản hồi quá chậm. Vui lòng thử lại.")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    st.error("❌ Lỗi xác thực (401): AGENT_API_KEY không chính xác hoặc chưa khớp giữa Frontend và Backend.")
                elif e.response.status_code == 429:
                    st.error("⏱️ Quá giới hạn lượt yêu cầu (429). Vui lòng đợi 1 phút và thử lại.")
                else:
                    st.error(f"❌ Lỗi máy chủ ({e.response.status_code}): {e.response.text}")
            except Exception as e:
                st.error(f"❌ Lỗi không xác định: {e}")
