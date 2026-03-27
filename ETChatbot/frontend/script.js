document.addEventListener('DOMContentLoaded', () => {
  const uploadBtn = document.getElementById('uploadBtn');
  const csvFileInput = document.getElementById('csvFile');
  const uploadStatus = document.getElementById('uploadStatus');
  const holdingsList = document.getElementById('holdingsList');
  const userIdInput = document.getElementById('userId');

  const sendBtn = document.getElementById('sendBtn');
  const queryInput = document.getElementById('queryInput');
  const chatLog = document.getElementById('chatLog');

  // Trigger file selection
  uploadBtn.addEventListener('click', () => {
    csvFileInput.click();
  });

  // Handle CSV Upload
  csvFileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    uploadStatus.textContent = file.name;
    uploadBtn.innerHTML = '<span class="loader"></span> Uploading...';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch(`/portfolio/upload-csv?user_id=${userIdInput.value}`, {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error('Upload failed. Ensure valid CSV with symbol and allocation columns.');
      
      const data = await res.json();
      uploadBtn.innerHTML = 'Uploaded ✓';
      uploadBtn.style.background = '#22c55e';
      
      // Update UI
      renderPortfolio(data.holdings);
      
      // Reset button after delay
      setTimeout(() => {
        uploadBtn.innerHTML = 'Upload CSV';
        uploadBtn.style.background = 'var(--btn-bg)';
      }, 3000);
      
      addMessage('assistant', `Portfolio loaded successfully. You have ${data.holdings.length} holdings evaluated at ${data.total_allocation}% allocation.`);
    } catch (error) {
      alert(error.message);
      uploadBtn.innerHTML = 'Upload CSV';
      uploadStatus.textContent = 'Upload failed';
    }
  });

  function renderPortfolio(holdings) {
    holdingsList.innerHTML = '';
    if (!holdings || holdings.length === 0) {
      holdingsList.innerHTML = '<li class="empty-state">No holdings found in CSV.</li>';
      return;
    }

    holdings.forEach(h => {
      const li = document.createElement('li');
      li.innerHTML = `<strong>${h.symbol}</strong> <span>${h.allocation}%</span>`;
      holdingsList.appendChild(li);
    });
  }

  // Handle Chat Submit
  async function submitChat() {
    const query = queryInput.value.trim();
    if (!query) return;

    // 1. Add User Message
    addMessage('user', query);
    queryInput.value = '';

    // 2. Add Loading Message
    const loadingId = addMessage('assistant', '<span class="loader"></span> Analyzing market data...');

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userIdInput.value,
          query: query
        })
      });

      if (!res.ok) throw new Error('API Error');
      const data = await res.json();

      // Format response
      let htm = `<div class="response-block">
        <p><strong>Verdict:</strong> ${data.verdict}</p>
        <div class="insight-pills">`;
      
      if (data.key_insights && data.key_insights.length > 0) {
        data.key_insights.forEach(a => {
           htm += `<span class="pill">${a}</span>`;
        });
      }
      
      htm += `</div>
        <div class="markdown-body" style="margin-top: 10px; line-height: 1.6; font-size: 0.95rem;">
          ${marked.parse(data.answer)}
        </div>
        <p style="margin-top: 12px; padding: 10px; background: rgba(0, 212, 170, 0.05); border-left: 3px solid var(--accent); border-radius: 4px;"><strong>Portfolio Impact:</strong> ${data.portfolio_impact}</p>
        <div style="margin-top: 12px;"><strong>Citations:</strong><ul style="margin-top: 8px; list-style-type: none; padding-left: 0; display: flex; flex-direction: column; gap: 6px;">`;
      
      if (data.citations && data.citations.length > 0) {
        data.citations.forEach(c => {
          htm += `<li><span class="cite-tag">[${c.doc_id}]</span> ${c.title} (${c.source} - ${c.date})</li>`;
        });
      }
      
      htm += `</ul></div></div>`;

      // Update Loading Message
      updateMessage(loadingId, htm);
      
    } catch (e) {
      updateMessage(loadingId, 'Failed to fetch response. Check backend connection.');
    }
  }

  sendBtn.addEventListener('click', submitChat);
  queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitChat();
    }
  });

  // Ticker Logic
  async function fetchTicker() {
    try {
      const resp = await fetch('/ticker');
      if (resp.ok) {
        const data = await resp.json();
        const tickerEl = document.getElementById('ticker');
        if (data && data.length > 0) {
          let html = '';
          const items = [...data, ...data, ...data]; // duplicate for seamless scrolling
          items.forEach(i => {
            html += `<div class="ticker-item"><span class="t-name">${i.name}</span><span class="t-price">${i.price}</span><span class="t-change ${i.direction}">${i.change}</span></div>`;
          });
          tickerEl.innerHTML = html;
        }
      }
    } catch(e) {
      console.log('Error fetching ticker:', e);
    }
  }

  fetchTicker();
  setInterval(fetchTicker, 60000);

  // UI Helpers
  function addMessage(role, htmlContent) {
    const id = 'msg-' + Date.now() + '-' + Math.floor(Math.random() * 10000);
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;
    wrapper.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'AI';

    const content = document.createElement('div');
    content.className = 'msg-content glass-bubble';
    content.innerHTML = htmlContent;

    if (role === 'user') {
      wrapper.appendChild(content);
      wrapper.appendChild(avatar);
    } else {
      wrapper.appendChild(avatar);
      wrapper.appendChild(content);
    }

    chatLog.appendChild(wrapper);
    chatLog.scrollTop = chatLog.scrollHeight;
    return id;
  }

  function updateMessage(id, htmlContent) {
    const el = document.getElementById(id);
    if (el) {
      const content = el.querySelector('.msg-content');
      content.innerHTML = htmlContent;
      chatLog.scrollTop = chatLog.scrollHeight;
    }
  }
});
