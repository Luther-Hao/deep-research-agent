(() => {
  const form = document.getElementById('research-form');
  const submitBtn = document.getElementById('submit-btn');
  const btnText = document.getElementById('btn-text');
  const btnSpinner = document.getElementById('btn-spinner');
  const stopBtn = document.getElementById('stop-btn');
  const progressSection = document.getElementById('progress-section');
  const messagesContainer = document.getElementById('messages-container');
  const reportSection = document.getElementById('report-section');
  const reportContent = document.getElementById('report-content');
  const copyBtn = document.getElementById('copy-btn');

  let activeReader = null;

  // ── helpers ─────────────────────────────────────────────────────────────────

  function setLoading(on) {
    submitBtn.disabled = on;
    btnText.textContent = on ? '研究中...' : '开始研究';
    btnSpinner.classList.toggle('hidden', !on);
  }

  function showSection(el, visible) {
    el.classList.toggle('hidden', !visible);
  }

  function addMessage(role, content) {
    const card = document.createElement('div');
    card.className = 'message-card';

    const roleEl = document.createElement('div');
    roleEl.className = `message-role role-${role.toLowerCase()}`;
    roleEl.textContent = roleLabel(role);

    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';
    contentEl.textContent = truncate(content, 600);

    card.appendChild(roleEl);
    card.appendChild(contentEl);
    messagesContainer.appendChild(card);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function roleLabel(role) {
    const map = {
      coordinator: '协调器',
      planner:     '规划器',
      researcher:  '研究员',
      reporter:    '报告员',
      coder:       '编码员',
      assistant:   '助手',
      ai:          '助手',
      error:       '错误',
    };
    return map[role.toLowerCase()] || role;
  }

  function truncate(text, max) {
    if (!text) return '';
    return text.length > max ? text.slice(0, max) + '…' : text;
  }

  function renderReport(markdown) {
    reportContent.innerHTML = marked.parse(markdown || '');
    showSection(reportSection, true);
    reportSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function reset() {
    messagesContainer.innerHTML = '';
    reportContent.innerHTML = '';
    showSection(progressSection, false);
    showSection(reportSection, false);
  }

  // ── SSE stream ───────────────────────────────────────────────────────────────

  async function startResearch(payload) {
    reset();
    setLoading(true);
    showSection(progressSection, true);

    try {
      const response = await fetch('/api/research/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const err = await response.text();
        addMessage('error', `HTTP ${response.status}: ${err}`);
        return;
      }

      const reader = response.body.getReader();
      activeReader = reader;
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (raw === '[DONE]') {
            setLoading(false);
            activeReader = null;
            return;
          }

          let event;
          try { event = JSON.parse(raw); } catch { continue; }

          handleEvent(event);
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        addMessage('error', String(err));
      }
    } finally {
      setLoading(false);
      activeReader = null;
    }
  }

  function handleEvent(event) {
    switch (event.type) {
      case 'message':
        addMessage(event.role || 'assistant', event.content || '');
        break;
      case 'final_report':
        renderReport(event.content || '');
        break;
      case 'error':
        addMessage('error', event.message || '未知错误');
        break;
      case 'done':
        setLoading(false);
        break;
    }
  }

  // ── form submit ──────────────────────────────────────────────────────────────

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = document.getElementById('query-input').value.trim();
    if (!query) return;

    const payload = {
      query,
      max_plan_iterations: parseInt(document.getElementById('max-plan-iterations').value, 10) || 1,
      max_step_num: parseInt(document.getElementById('max-step-num').value, 10) || 3,
      enable_background_investigation: document.getElementById('enable-background').checked,
    };

    await startResearch(payload);
  });

  // ── stop ─────────────────────────────────────────────────────────────────────

  stopBtn.addEventListener('click', () => {
    if (activeReader) {
      activeReader.cancel();
      activeReader = null;
    }
    setLoading(false);
    addMessage('assistant', '已手动停止研究。');
  });

  // ── copy report ──────────────────────────────────────────────────────────────

  copyBtn.addEventListener('click', async () => {
    const text = reportContent.innerText;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = '已复制!';
      setTimeout(() => { copyBtn.textContent = '复制报告'; }, 2000);
    } catch {
      copyBtn.textContent = '复制失败';
    }
  });
})();
