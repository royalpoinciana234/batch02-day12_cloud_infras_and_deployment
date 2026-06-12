(function () {
  const BACKEND_URL = window.LC_BACKEND_URL || 'http://localhost:8000';
  const AGENT_API_KEY = window.LC_AGENT_API_KEY || 'my-secret-key';
  let history = [];
  let panelOpen = false;

  function injectStyles() {
    const css = `
      .lc-chat-fab {
        position: fixed; bottom: 24px; right: 24px; z-index: 9999;
        background: #006FB6; color: white; border: none; border-radius: 50px;
        padding: 14px 22px; font-size: 15px; font-weight: 700; cursor: pointer;
        box-shadow: 0 4px 20px rgba(0,111,182,0.4);
        display: flex; align-items: center; gap: 8px;
        transition: transform 0.2s, box-shadow 0.2s;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }
      .lc-chat-fab:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(0,111,182,0.5); }
      .lc-chat-fab .lc-chat-fab-dot {
        width: 10px; height: 10px; background: #4CAF50; border-radius: 50%;
        box-shadow: 0 0 0 0 rgba(76,175,80,0.4);
        animation: lc-pulse 2s infinite;
      }
      @keyframes lc-pulse {
        0%   { box-shadow: 0 0 0 0 rgba(76,175,80,0.4); }
        70%  { box-shadow: 0 0 0 8px rgba(76,175,80,0); }
        100% { box-shadow: 0 0 0 0 rgba(76,175,80,0); }
      }

      .lc-chat-panel {
        position: fixed; bottom: 90px; right: 24px; z-index: 9998;
        width: 370px; height: 540px;
        background: white; border-radius: 16px;
        box-shadow: 0 12px 48px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08);
        display: flex; flex-direction: column; overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        transform: scale(0.95) translateY(10px); opacity: 0;
        transition: transform 0.2s ease, opacity 0.2s ease;
        pointer-events: none;
      }
      .lc-chat-panel.lc-open {
        transform: scale(1) translateY(0); opacity: 1; pointer-events: all;
      }

      .lc-chat-header {
        background: linear-gradient(135deg, #006FB6 0%, #0085D2 100%);
        color: white; padding: 16px 18px;
        display: flex; align-items: center; justify-content: space-between;
        flex-shrink: 0;
      }
      .lc-chat-header-left { display: flex; align-items: center; gap: 10px; }
      .lc-chat-header-avatar {
        width: 38px; height: 38px; background: rgba(255,255,255,0.2);
        border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px;
      }
      .lc-chat-header-info .lc-chat-title { font-size: 15px; font-weight: 700; }
      .lc-chat-header-info .lc-chat-status { font-size: 11px; opacity: 0.8; margin-top: 1px; }
      .lc-chat-close {
        background: rgba(255,255,255,0.2); border: none; color: white;
        width: 28px; height: 28px; border-radius: 50%; cursor: pointer;
        font-size: 16px; display: flex; align-items: center; justify-content: center;
        transition: background 0.15s;
      }
      .lc-chat-close:hover { background: rgba(255,255,255,0.35); }

      .lc-chat-messages {
        flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px;
        background: #f8f9fb;
      }
      .lc-chat-messages::-webkit-scrollbar { width: 4px; }
      .lc-chat-messages::-webkit-scrollbar-track { background: transparent; }
      .lc-chat-messages::-webkit-scrollbar-thumb { background: #ddd; border-radius: 2px; }

      .lc-msg { display: flex; max-width: 92%; min-width: 0; gap: 8px; }
      .lc-msg.lc-user { align-self: flex-end; flex-direction: row-reverse; max-width: 82%; }
      .lc-msg.lc-bot { align-self: flex-start; flex-direction: row; width: 92%; }
      .lc-msg.lc-bot .lc-msg-body { position: relative; }
      .lc-msg-avatar {
        width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
        overflow: hidden; margin-top: 2px; background: #e8f4fb;
      }
      .lc-msg-avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
      .lc-msg-body { display: flex; flex-direction: column; flex: 1; min-width: 0; }

      .lc-bubble {
        padding: 10px 14px; border-radius: 16px; font-size: 13.5px; line-height: 1.55;
        word-break: break-word;
      }
      .lc-user .lc-bubble { background: #006FB6; color: white; border-bottom-right-radius: 4px; }
      .lc-bot .lc-bubble { background: white; color: #222; border: 1px solid #e8e8e8; border-bottom-left-radius: 4px; }

      .lc-ts { font-size: 10px; color: #aaa; margin-top: 3px; padding: 0 4px; }

      .lc-disclaimer {
        font-size: 10.5px; color: #999; margin-top: 5px; padding: 5px 8px;
        background: #f0f4f8; border-radius: 6px; line-height: 1.4;
        border-left: 2px solid #006FB6;
      }

      .lc-handoff-card {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFF8E1 100%);
        border: 1.5px solid #FFB74D; border-radius: 12px; padding: 14px;
        margin-top: 4px;
      }
      .lc-handoff-card .lc-handoff-title {
        font-size: 13px; font-weight: 700; color: #E65100; margin-bottom: 8px;
        display: flex; align-items: center; gap: 6px;
      }
      .lc-handoff-card .lc-handoff-pharmacist {
        font-size: 13px; color: #555; margin-bottom: 6px;
      }
      .lc-handoff-card .lc-handoff-pharmacist strong { color: #333; }
      .lc-handoff-card .lc-safety-badge {
        display: inline-flex; align-items: center; gap: 4px;
        background: #FF8C00; color: white; font-size: 10.5px; font-weight: 700;
        padding: 3px 8px; border-radius: 20px; margin-bottom: 8px;
      }
      .lc-handoff-card .lc-handoff-summary {
        font-size: 12px; color: #666; line-height: 1.5; border-top: 1px solid #FFB74D;
        padding-top: 8px; margin-top: 4px;
      }

      .lc-product-links { margin-top: 8px; display: flex; flex-direction: column; gap: 6px; width: 100%; overflow: hidden; }
      .lc-product-link {
        display: flex; align-items: center; gap: 8px; padding: 8px 10px;
        background: #f0f7ff; border: 1px solid #c8e0f4; border-radius: 8px;
        text-decoration: none; color: #006FB6; font-size: 12px;
        transition: background 0.15s; overflow: hidden; min-width: 0;
      }
      .lc-product-link:hover { background: #ddeeff; }
      .lc-product-link .lc-pl-icon { font-size: 18px; flex-shrink: 0; }
      .lc-product-link .lc-pl-info { flex: 1; min-width: 0; overflow: hidden; }
      .lc-product-link .lc-pl-name { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
      .lc-product-link .lc-pl-price { color: #D32F2F; font-size: 11px; margin-top: 1px; }
      .lc-product-link .lc-pl-arrow { flex-shrink: 0; color: #aaa; font-size: 14px; }
      .lc-product-links-title { font-size: 11px; color: #888; margin-top: 8px; margin-bottom: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; }

      .lc-chat-typing {
        display: flex; align-items: center; gap: 4px; padding: 10px 14px;
        background: white; border: 1px solid #e8e8e8; border-radius: 16px;
        border-bottom-left-radius: 4px; align-self: flex-start;
      }
      .lc-typing-dot {
        width: 6px; height: 6px; background: #aaa; border-radius: 50%;
        animation: lc-typing 1.2s infinite;
      }
      .lc-typing-dot:nth-child(2) { animation-delay: 0.2s; }
      .lc-typing-dot:nth-child(3) { animation-delay: 0.4s; }
      @keyframes lc-typing {
        0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
        30% { transform: translateY(-5px); opacity: 1; }
      }

      .lc-chat-footer {
        padding: 12px 14px; background: white; border-top: 1px solid #eee;
        display: flex; gap: 8px; flex-shrink: 0;
      }
      .lc-chat-input {
        flex: 1; padding: 10px 14px; border: 1.5px solid #e0e0e0; border-radius: 24px;
        font-size: 13.5px; outline: none; font-family: inherit;
        transition: border-color 0.15s;
      }
      .lc-chat-input:focus { border-color: #006FB6; }
      .lc-chat-send {
        background: #006FB6; color: white; border: none; border-radius: 50%;
        width: 40px; height: 40px; cursor: pointer; font-size: 16px;
        display: flex; align-items: center; justify-content: center;
        transition: background 0.15s, transform 0.1s; flex-shrink: 0;
      }
      .lc-chat-send:hover { background: #0085D2; transform: scale(1.05); }
      .lc-chat-send:disabled { background: #ccc; cursor: not-allowed; transform: none; }

      .lc-report-trigger {
        position: absolute; top: 4px; right: 4px;
        background: none; border: none; cursor: pointer;
        font-size: 13px; color: #bbb; padding: 2px 5px;
        border-radius: 4px; line-height: 1; z-index: 1;
        opacity: 0; transition: opacity 0.15s, color 0.15s;
      }
      .lc-msg.lc-bot:hover .lc-report-trigger { opacity: 1; }
      .lc-report-trigger:hover { color: #c0392b; background: rgba(0,0,0,0.04); }

      .lc-report-form {
        margin-top: 6px; padding: 8px 10px;
        background: #fff8f0; border: 1px solid #FFB74D; border-radius: 8px;
        display: flex; flex-direction: column; gap: 6px;
      }
      .lc-report-form-label { font-size: 11px; color: #888; font-weight: 600; }
      .lc-report-form textarea {
        width: 100%; box-sizing: border-box;
        border: 1px solid #ddd; border-radius: 6px;
        padding: 6px 8px; font-size: 12.5px; font-family: inherit;
        resize: none; outline: none; line-height: 1.4;
      }
      .lc-report-form textarea:focus { border-color: #FFB74D; }
      .lc-report-form-actions { display: flex; gap: 6px; justify-content: flex-end; }
      .lc-report-form-cancel {
        background: none; border: 1px solid #ddd; border-radius: 6px;
        padding: 4px 10px; font-size: 12px; cursor: pointer; color: #666;
      }
      .lc-report-form-confirm {
        background: #E65100; border: none; border-radius: 6px;
        padding: 4px 10px; font-size: 12px; cursor: pointer;
        color: white; font-weight: 600;
      }
      .lc-report-form-confirm:disabled { background: #ccc; cursor: default; }
      .lc-report-done { font-size: 11.5px; color: #5a9e4f; margin-top: 4px; }
    `;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  function formatTime(date) {
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  }

  function scrollToBottom() {
    const msgs = document.getElementById('lc-chat-messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  function showTyping() {
    const msgs = document.getElementById('lc-chat-messages');
    const el = document.createElement('div');
    el.id = 'lc-typing-indicator';
    el.className = 'lc-msg lc-bot';
    el.style.cssText = 'opacity:0.7;';
    el.innerHTML = `
      <div class="lc-msg-avatar"><img src="./assets/avatar.png" alt="AI" /></div>
      <div class="lc-msg-body">
        <div class="lc-chat-typing">
          <div class="lc-typing-dot"></div>
          <div class="lc-typing-dot"></div>
          <div class="lc-typing-dot"></div>
        </div>
      </div>`;
    msgs.appendChild(el);
    scrollToBottom();
  }

  function hideTyping() {
    const el = document.getElementById('lc-typing-indicator');
    if (el) el.remove();
  }

  function appendUserBubble(text) {
    const msgs = document.getElementById('lc-chat-messages');
    const el = document.createElement('div');
    el.className = 'lc-msg lc-user';
    el.innerHTML = `
      <div class="lc-msg-body" style="align-items:flex-end;">
        <div class="lc-bubble">${escHtml(text)}</div>
        <div class="lc-ts">${formatTime(new Date())}</div>
      </div>`;
    msgs.appendChild(el);
    scrollToBottom();
  }

  function buildProductLinksHtml(products) {
    if (!products || products.length === 0) return '';
    const items = products.map(p => `
      <a class="lc-product-link" href="${escHtml(p.url)}" target="_blank" rel="noopener">
        <span class="lc-pl-icon">💊</span>
        <div class="lc-pl-info">
          <span class="lc-pl-name">${escHtml(p.name)}</span>
          <div class="lc-pl-price">${escHtml(p.price)}</div>
        </div>
        <span class="lc-pl-arrow">→</span>
      </a>`).join('');
    return `<div class="lc-product-links-title">🛒 Sản phẩm tại Long Châu</div><div class="lc-product-links">${items}</div>`;
  }

  function renderMessage(data, userMsg) {
    hideTyping();
    const msgs = document.getElementById('lc-chat-messages');
    const wrapper = document.createElement('div');
    wrapper.className = 'lc-msg lc-bot';

    const route = data.route || 'factual';
    const reply = data.reply || '';
    const model = data.model || '';

    const avatar = `<div class="lc-msg-avatar"><img src="./assets/avatar.png" alt="AI" /></div>`;

    if (route === 'advisory_handoff') {
      const summary = data.handoff_summary || data.summary || '';
      wrapper.innerHTML = `
        ${avatar}
        <div class="lc-msg-body">
          <div class="lc-bubble">${mdToHtml(reply)}</div>
          <div class="lc-handoff-card">
            <div class="lc-handoff-title">🔄 Chuyển tư vấn chuyên sâu</div>
            <div class="lc-safety-badge">⚠️ Câu hỏi cần dược sĩ</div>
            ${summary ? `<div class="lc-handoff-summary">📋 <strong>Tóm tắt:</strong> ${escHtml(summary)}</div>` : ''}
          </div>
          <div class="lc-ts">${formatTime(new Date())}</div>
        </div>
      `;
    } else if (route === 'advisory_gather') {
      wrapper.innerHTML = `
        ${avatar}
        <div class="lc-msg-body">
          <div class="lc-bubble">${mdToHtml(reply)}</div>
          <div class="lc-ts">${formatTime(new Date())}</div>
        </div>
      `;
    } else {
      // factual — reply is clean text; products rendered as native clickable cards
      const productHtml = buildProductLinksHtml(data.products || []);
      wrapper.innerHTML = `
        ${avatar}
        <div class="lc-msg-body">
          <div class="lc-bubble">${mdToHtml(reply)}</div>
          <div class="lc-disclaimer">ℹ️ Thông tin mang tính tham khảo. Tham khảo dược sĩ trước khi dùng thuốc.</div>
          ${productHtml}
          <div class="lc-ts">${formatTime(new Date())}</div>
        </div>
      `;
    }

    msgs.appendChild(wrapper);

    // Hover-reveal report trigger (top-right of message body, visible on hover)
    if (userMsg) {
      const body = wrapper.querySelector('.lc-msg-body');
      if (body) {
        const trigger = document.createElement('button');
        trigger.className = 'lc-report-trigger';
        trigger.title = 'Báo cáo câu trả lời này';
        trigger.textContent = '🚩';
        body.appendChild(trigger);

        trigger.addEventListener('click', () => {
          trigger.style.display = 'none';

          const form = document.createElement('div');
          form.className = 'lc-report-form';
          form.innerHTML = `
            <div class="lc-report-form-label">Mô tả vấn đề (tuỳ chọn):</div>
            <textarea rows="2" placeholder="Câu trả lời sai, thiếu thông tin..."></textarea>
            <div class="lc-report-form-actions">
              <button class="lc-report-form-cancel">Huỷ</button>
              <button class="lc-report-form-confirm">Gửi báo cáo</button>
            </div>
          `;
          const ts = body.querySelector('.lc-ts');
          if (ts) body.insertBefore(form, ts);
          else body.appendChild(form);
          form.querySelector('textarea').focus();

          form.querySelector('.lc-report-form-cancel').addEventListener('click', () => {
            form.remove();
            trigger.style.display = '';
          });

          form.querySelector('.lc-report-form-confirm').addEventListener('click', () => {
            const description = form.querySelector('textarea').value.trim();
            form.querySelector('.lc-report-form-confirm').disabled = true;
            form.innerHTML = '<div class="lc-report-done">✓ Đã ghi nhận. Cảm ơn phản hồi của bạn!</div>';
            fetch(BACKEND_URL + '/report', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_message: userMsg, bot_reply: reply, route, model, description }),
            }).catch(() => {});
          });
        });
      }
    }

    scrollToBottom();
  }

  function renderError(msg) {
    hideTyping();
    const msgs = document.getElementById('lc-chat-messages');
    const el = document.createElement('div');
    el.className = 'lc-msg lc-bot';
    el.innerHTML = `
      <div class="lc-msg-avatar"><img src="./assets/avatar.png" alt="AI" /></div>
      <div class="lc-msg-body">
        <div class="lc-bubble" style="color:#c62828;background:#ffebee;border-color:#ffcdd2;">⚠️ ${escHtml(msg)}</div>
        <div class="lc-ts">${formatTime(new Date())}</div>
      </div>`;
    msgs.appendChild(el);
    scrollToBottom();
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Convert basic markdown to safe HTML: **bold**, *italic*, [text](url), \n → <br>
  function mdToHtml(str) {
    return escHtml(str)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener" style="color:#006FB6;">$1</a>')
      .replace(/\n/g, '<br>');
  }

  async function sendMessage(message) {
    const sendBtn = document.getElementById('lc-chat-send');
    const input = document.getElementById('lc-chat-input');
    if (sendBtn) sendBtn.disabled = true;

    history.push({ role: 'user', content: message });
    appendUserBubble(message);
    showTyping();

    try {
      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': AGENT_API_KEY
        },
        body: JSON.stringify({ message, history }),
      });

      if (!res.ok) throw new Error(`HTTP_${res.status}`);
      const data = await res.json();
      history.push({ role: 'assistant', content: data.reply });
      renderMessage(data, message);
    } catch (err) {
      history.pop(); // revert user message from history on error
      if (err.message && err.message.startsWith('HTTP_')) {
        const status = err.message.split('_')[1];
        if (status === '401') {
          renderError('Lỗi xác thực (401): AGENT_API_KEY không hợp lệ hoặc không khớp giữa frontend và backend.');
        } else if (status === '429') {
          renderError('Quá giới hạn số lượng yêu cầu (429). Vui lòng thử lại sau 1 phút.');
        } else {
          renderError(`Lỗi máy chủ (${status}). Vui lòng thử lại sau.`);
        }
      } else {
        renderError(`Không thể kết nối đến Backend (${BACKEND_URL}). Vui lòng kiểm tra lại cấu hình BACKEND_URL.`);
      }
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (input) input.focus();
    }
  }

  function createFloatButton() {
    const btn = document.createElement('button');
    btn.className = 'lc-chat-fab';
    btn.id = 'lc-chat-fab';
    btn.innerHTML = '<span>💊</span><span>Tư vấn AI</span><div class="lc-chat-fab-dot"></div>';
    btn.addEventListener('click', togglePanel);
    document.body.appendChild(btn);
  }

  function createChatPanel() {
    const panel = document.createElement('div');
    panel.className = 'lc-chat-panel';
    panel.id = 'lc-chat-panel';
    panel.innerHTML = `
      <div class="lc-chat-header">
        <div class="lc-chat-header-left">
          <div class="lc-chat-header-avatar">💊</div>
          <div class="lc-chat-header-info">
            <div class="lc-chat-title">Long Châu AI Tư vấn</div>
            <div class="lc-chat-status">🟢 Trực tuyến • Phản hồi ngay</div>
          </div>
        </div>
        <button class="lc-chat-close" id="lc-chat-close">✕</button>
      </div>
      <div class="lc-chat-messages" id="lc-chat-messages"></div>
      <div class="lc-chat-footer">
        <input class="lc-chat-input" id="lc-chat-input" type="text"
          placeholder="Nhập câu hỏi về thuốc..." autocomplete="off" />
        <button class="lc-chat-send" id="lc-chat-send">➤</button>
      </div>
    `;
    document.body.appendChild(panel);

    document.getElementById('lc-chat-close').addEventListener('click', closePanel);

    const input = document.getElementById('lc-chat-input');
    const sendBtn = document.getElementById('lc-chat-send');

    function submitInput() {
      const msg = input.value.trim();
      if (!msg) return;
      input.value = '';
      sendMessage(msg);
    }

    sendBtn.addEventListener('click', submitInput);

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitInput();
      }
    });

    // Welcome message
    showWelcome();
  }

  function showWelcome() {
    const msgs = document.getElementById('lc-chat-messages');
    const el = document.createElement('div');
    el.className = 'lc-msg lc-bot';
    el.innerHTML = `
      <div class="lc-msg-avatar"><img src="./assets/avatar.png" alt="AI" /></div>
      <div class="lc-msg-body">
        <div class="lc-bubble">
          Xin chào! 👋 Tôi là <strong>Long Châu AI</strong> — trợ lý tư vấn dược phẩm.<br/><br/>
          Tôi có thể giúp bạn:<br/>
          • Thông tin về thuốc và tác dụng<br/>
          • Liều dùng và cách sử dụng<br/>
          • Tương tác thuốc cơ bản<br/>
          • Kết nối dược sĩ khi cần thiết
        </div>
        <div class="lc-ts">${formatTime(new Date())}</div>
      </div>
    `;
    msgs.appendChild(el);
  }

  function openPanel() {
    const panel = document.getElementById('lc-chat-panel');
    if (panel) { panel.classList.add('lc-open'); panelOpen = true; }
    const input = document.getElementById('lc-chat-input');
    if (input) setTimeout(() => input.focus(), 200);
  }

  function closePanel() {
    const panel = document.getElementById('lc-chat-panel');
    if (panel) { panel.classList.remove('lc-open'); panelOpen = false; }
  }

  function togglePanel() {
    panelOpen ? closePanel() : openPanel();
  }

  function init() {
    injectStyles();
    createChatPanel();
    createFloatButton();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
