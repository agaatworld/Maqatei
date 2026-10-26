/* Maqati icons: one consistent set of line icons instead of emoji.
   The interface is written with emoji as short names (📝, ✂️, 💼 …); this file draws each one as a real
   icon wherever it appears in the interface. Text people type (titles, notes, transcripts) is left alone. */
(function () {
  const P = {
    folder: '<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
    folders: '<path d="M6.5 8.5a2 2 0 0 1 2-2h3l2 2h5a2 2 0 0 1 2 2v6.5a2 2 0 0 1-2 2h-10a2 2 0 0 1-2-2z"/><path d="M3.5 14.5v-7a2 2 0 0 1 2-2h3"/>',
    text: '<path d="M5 6h14M5 10h14M5 14h9M5 18h6"/>',
    case: '<path d="M4 8.5h16v10a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5z"/><path d="M9 8.5V6a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 6v2.5M4 13h16"/>',
    scissors: '<circle cx="6" cy="7" r="2.5"/><circle cx="6" cy="17" r="2.5"/><path d="M8 8.5 19 17M8 15.5 19 7"/>',
    trash: '<path d="M4.5 7h15M10 7V5h4v2M6.5 7l1 12.5h9l1-12.5M10 11v5M14 11v5"/>',
    film: '<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="M10 9.5v5l4-2.5z" fill="currentColor"/>',
    headphones: '<path d="M4.5 15v-3a7.5 7.5 0 0 1 15 0v3"/><rect x="3.5" y="14" width="4" height="6" rx="1.5"/><rect x="16.5" y="14" width="4" height="6" rx="1.5"/>',
    music: '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    clock: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4.5l3 2"/>',
    hourglass: '<path d="M7 3.5h10M7 20.5h10M8 3.5c0 5 8 5 8 8.5s-8 3.5-8 8.5M16 3.5c0 5-8 5-8 8.5s8 3.5 8 8.5"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    checkc: '<circle cx="12" cy="12" r="8.5"/><path d="M8 12.3l2.8 2.8L16.2 9.6"/>',
    pencil: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    book: '<path d="M5 4.5h10.5a2 2 0 0 1 2 2V20H7a2 2 0 0 1-2-2z"/><path d="M5 18a2 2 0 0 1 2-2h10.5M9 8.5h5"/>',
    pin: '<path d="M12 21s-6.5-5.8-6.5-11a6.5 6.5 0 0 1 13 0c0 5.2-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    doc: '<path d="M7 3.5h7l4 4v13H7z"/><path d="M14 3.5v4h4M9.5 12h6M9.5 15.5h6"/>',
    link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7L11.5 6.8"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1.5-1.5"/>',
    bookmark: '<path d="M7 4h10v16l-5-3.5L7 20z"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>',
    star: '<path d="M12 4l2.4 5 5.4.7-4 3.8 1 5.4L12 16.3 7.2 18.9l1-5.4-4-3.8 5.4-.7z"/>',
    alert: '<path d="M12 4 21 19.5H3z"/><path d="M12 10v4.5M12 17.2v.3"/>',
    start: '<path d="M6 21V4"/><path d="M6 4h11l-2.5 4L17 12H6" fill="currentColor" fill-opacity=".22"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor" fill-opacity=".22"/>',
    library: '<path d="M5 4h4v16H5zM10 4h4v16h-4zM15.5 5.5l3.6-1 3 14.6-3.6.9z"/>',
    bulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    box: '<path d="M4 7.5 12 3.5l8 4v9l-8 4-8-4z"/><path d="M4 7.5l8 4 8-4M12 11.5v9"/>',
    pause: '<rect x="6.5" y="5" width="4" height="14" rx="1.2" fill="currentColor" stroke="none"/><rect x="13.5" y="5" width="4" height="14" rx="1.2" fill="currentColor" stroke="none"/>',
    play: '<path d="M8 5.5v13l11-6.5z" fill="currentColor" stroke="none"/>',
    gear: '<path d="M10.3 3.5h3.4l.5 2.4 1.7 1 2.3-.8 1.7 2.9-1.8 1.6v2l1.8 1.6-1.7 2.9-2.3-.8-1.7 1-.5 2.4h-3.4l-.5-2.4-1.7-1-2.3.8-1.7-2.9 1.8-1.6v-2L4.1 9l1.7-2.9 2.3.8 1.7-1z"/><circle cx="12" cy="12" r="2.8"/>',
    sliders: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
    palette: '<path d="M12 3.5a8.5 8.5 0 1 0 0 17c1.2 0 1.8-.8 1.8-1.7 0-1.3-1.1-1.6-1.1-2.7 0-1 .8-1.6 1.8-1.6h2.2a3.8 3.8 0 0 0 3.8-3.8C20.5 6.6 16.7 3.5 12 3.5z"/><circle cx="7.8" cy="11" r="1.1" fill="currentColor"/><circle cx="10.5" cy="7.5" r="1.1" fill="currentColor"/><circle cx="14.8" cy="7.8" r="1.1" fill="currentColor"/>',
    tag: '<path d="M3.5 12V4.5H11l9 9-7.5 7.5z"/><circle cx="7.5" cy="8.5" r="1.3"/>',
    bell: '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0M12 3.5V5"/>',
    hands: '<path d="M12 20c-4 0-7-2.5-7-6V9.5a1.5 1.5 0 0 1 3 0V13M12 20c4 0 7-2.5 7-6V9.5a1.5 1.5 0 0 0-3 0V13M8 13V6a1.5 1.5 0 0 1 3 0v6M16 13V6a1.5 1.5 0 0 0-3 0v6"/>',
    unlock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 7.6-1.7"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    refresh: '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4.2h-4.2"/>',
    font: '<path d="M4 19 9 5l5 14M5.8 14h6.4M15.5 13.5h4.5M17.7 11v8"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    expand: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    speaker: '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
    list: '<path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4.2" cy="6" r=".9" fill="currentColor"/><circle cx="4.2" cy="12" r=".9" fill="currentColor"/><circle cx="4.2" cy="18" r=".9" fill="currentColor"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1.8"/><rect x="13" y="4" width="7" height="7" rx="1.8"/><rect x="4" y="13" width="7" height="7" rx="1.8"/><rect x="13" y="13" width="7" height="7" rx="1.8"/>',
    moon: '<path d="M19.5 14.5A7.5 7.5 0 0 1 9.5 4.5a7.5 7.5 0 1 0 10 10z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    chat: '<path d="M4.5 5.5h15v10h-9l-4.5 4v-4h-1.5z"/>',
    eye: '<path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
    broom: '<path d="M14 4l6 6M12 10l2 2M5 21l4.5-4.5M9 11l4 4-3.5 5.5L4 15z"/>',
    globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.5 5.4 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.4-3.5-8.5s1-5.9 3.5-8.5z"/>',
    flask: '<path d="M9.5 3.5h5M10.5 3.5v5.5L5 19a1.3 1.3 0 0 0 1.1 1.5h11.8A1.3 1.3 0 0 0 19 19l-5.5-10V3.5M7.5 15h9"/>',
    monitor: '<rect x="3.5" y="4.5" width="17" height="11.5" rx="2"/><path d="M9 20h6M12 16v4"/>',
    cookie: '<path d="M12 3.5a8.5 8.5 0 1 0 8.5 8.7 3 3 0 0 1-3.6-3.3 3 3 0 0 1-3.3-3.6A3 3 0 0 1 12 3.5z"/><circle cx="9" cy="10" r=".9" fill="currentColor"/><circle cx="14" cy="15" r=".9" fill="currentColor"/><circle cx="9" cy="15.5" r=".9" fill="currentColor"/>',
    signal: '<path d="M12 20v-6M8.5 10.5a5 5 0 0 1 7 0M6 8a8.5 8.5 0 0 1 12 0"/><circle cx="12" cy="13.5" r="1.2" fill="currentColor"/>',
    battery: '<rect x="3.5" y="7.5" width="15" height="9" rx="2"/><path d="M21 10.5v3M7 10.5v3M10 10.5v3"/>',
    user: '<circle cx="12" cy="8.5" r="3.8"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    logout: '<path d="M14 4.5h4.5v15H14M10 16l4-4-4-4M14 12H4"/>',
    pulse: '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
    tools: '<path d="M14.5 6.5a3.5 3.5 0 0 0 4.6 4.6l-8.6 8.6a2 2 0 0 1-2.8-2.8l8.6-8.6"/><path d="M14.5 6.5 17 4l3 3-2.5 2.5"/>',
    mosque: '<path d="M4 20.5h16M5.5 20.5V13h13v7.5M7 13a5 5 0 0 1 10 0M12 4v4M10 20.5v-3.5a2 2 0 0 1 4 0v3.5"/>',
    cap: '<path d="M2.5 9 12 5l9.5 4L12 13z"/><path d="M6.5 11v4.5c1.5 1.4 3.4 2 5.5 2s4-.6 5.5-2V11M21.5 9v5"/>',
    heart: '<path d="M12 19.5s-7.5-4.4-7.5-10A4.3 4.3 0 0 1 12 7a4.3 4.3 0 0 1 7.5 2.5c0 5.6-7.5 10-7.5 10z"/>',
    leaf: '<path d="M5 19c0-8 5-13 14.5-13.5C19 15 14 19.5 6.5 19.5"/><path d="M5 19.5 13 11"/>',
    beads: '<circle cx="12" cy="5" r="1.6"/><circle cx="17" cy="7.5" r="1.6"/><circle cx="19" cy="12.5" r="1.6"/><circle cx="7" cy="7.5" r="1.6"/><circle cx="5" cy="12.5" r="1.6"/><path d="M12 15v5.5"/><circle cx="12" cy="13.5" r="1.6"/>',
    kaaba: '<path d="M4 8 12 4.5 20 8v9.5L12 21l-8-3.5z"/><path d="M4 8l8 3.5L20 8M12 11.5V21M4 11l8 3.5 8-3.5"/>',
    sparkle: '<path d="M12 3.5c.6 4.4 2.6 6.9 7 8.5-4.4 1.6-6.4 4.1-7 8.5-.6-4.4-2.6-6.9-7-8.5 4.4-1.6 6.4-4.1 7-8.5z"/>',
    sun2: '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2"/>',
    dl: '<path d="M12 4v11"/><path d="M7 10.5 12 15.5 17 10.5"/><path d="M5 20h14"/>',
    chevR: '<path d="M9 6l6 6-6 6"/>',
    chevL: '<path d="M15 6l-6 6 6 6"/>',
    phone: '<rect x="7" y="3" width="10" height="18" rx="2.5"/><path d="M11 18h2"/>',
    skip: '<path d="M5 6l6 6-6 6M12 6l6 6-6 6"/>',
    dots: '<circle cx="5.5" cy="12" r="1.6" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none"/><circle cx="18.5" cy="12" r="1.6" fill="currentColor" stroke="none"/>',
    dot: '<circle cx="12" cy="12" r="4.5" fill="currentColor" stroke="none"/>',
  };
  const svg = n => `<svg class="ic ic-${n}" viewBox="0 0 24 24" aria-hidden="true">${P[n]}</svg>`;
  window.ICON = svg;

  // emoji (and a few symbols) used by the interface -> icon name
  const EMO = {
    '📁': 'folder', '📂': 'folder', '🗂️': 'folders', '🗂': 'folders', '📝': 'text', '💼': 'case', '✂️': 'scissors', '✂': 'scissors',
    '🗑': 'trash', '🗑️': 'trash', '🎬': 'film', '🎧': 'headphones', '🎵': 'music', '⏱': 'clock', '⏱️': 'clock', '🕒': 'clock',
    '⏳': 'hourglass', '✅': 'checkc', '✓': 'check', '✔': 'check', '✏️': 'pencil', '✏': 'pencil', '📕': 'book', '📘': 'book', '📖': 'book',
    '📌': 'pin', '📍': 'pin', '✕': 'x', '❌': 'x', '✗': 'x', '📄': 'doc', '📃': 'doc', '📋': 'doc', '🔗': 'link', '🔖': 'bookmark',
    '🔎': 'search', '🔍': 'search', '⭐': 'star', '⚠️': 'alert', '⚠': 'alert', '🟢': 'start', '🔴': 'stop', '📚': 'library', '💡': 'bulb',
    '📦': 'box', '⏸': 'pause', '⏸️': 'pause', '▶': 'play', '▶️': 'play', '⚙️': 'gear', '⚙': 'gear', '🎨': 'palette', '🏷️': 'tag', '🏷': 'tag',
    '🤲': 'hands', '🔔': 'bell', '🔓': 'unlock', '🔒': 'lock', '↻': 'refresh', '🔄': 'refresh', '↺': 'refresh', '🔤': 'font', '➕': 'plus', '＋': 'plus',
    '⛶': 'expand', '🔊': 'speaker', '☰': 'list', '▦': 'grid', '🌙': 'moon', '☀️': 'sun', '☀': 'sun', '💬': 'chat', '👁': 'eye', '👁️': 'eye',
    '🧹': 'broom', '🌐': 'globe', '🧪': 'flask', '🖥️': 'monitor', '🖥': 'monitor', '🍪': 'cookie', '🛰️': 'signal', '🛰': 'signal',
    '🔋': 'battery', '👤': 'user', '🚪': 'logout', '🩺': 'pulse', '🧰': 'tools', '🕌': 'mosque', '🎓': 'cap', '🧠': 'bulb', '❤️': 'heart',
    '🌿': 'leaf', '👨‍🏫': 'user', '📿': 'beads', '🕋': 'kaaba', '✨': 'sparkle', '⬇': 'dl', '📱': 'phone', '⏩': 'skip', '☑': 'checkc', '☑️': 'checkc', '⏪': 'skip', '⬇️': 'dl', '🎙️': 'speaker', '📥': 'dl',
  };
  // arrows become chevrons only when they stand alone (a back button), never inside a sentence
  const ALONE = { '→': 'chevR', '←': 'chevL', '‹': 'chevL', '›': 'chevR' };
  const keys = Object.keys(EMO).sort((a, b) => b.length - a.length).map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const RX = new RegExp('(' + keys.join('|') + ')\\uFE0F?', 'g');
  const SKIP = 'textarea,input,select,option,script,style,[dir=auto],[contenteditable],.seg p,.txt,.extext,.hit p,.pe3,.fprev,.expreview,.noico';

  function fix(node) {
    const tx = node.nodeValue;
    if (!tx) return;
    const el = node.parentElement;
    if (!el || el.closest(SKIP)) return;
    const alone = ALONE[tx.trim()];
    if (alone) { const s = document.createElement('span'); s.className = 'icw'; s.innerHTML = svg(alone); el.replaceChild(s, node); return; }
    RX.lastIndex = 0;
    if (!RX.test(tx)) return;
    RX.lastIndex = 0;
    const frag = document.createDocumentFragment();
    let last = 0, m;
    while ((m = RX.exec(tx))) {
      if (m.index > last) frag.appendChild(document.createTextNode(tx.slice(last, m.index)));
      const s = document.createElement('span'); s.className = 'icw'; s.innerHTML = svg(EMO[m[1]] || EMO[m[1] + '️']);
      frag.appendChild(s);
      last = m.index + m[0].length;
    }
    if (last < tx.length) frag.appendChild(document.createTextNode(tx.slice(last)));
    el.replaceChild(frag, node);
  }
  function walk(root) {
    if (root.nodeType === 3) return fix(root);
    if (root.nodeType !== 1) return;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const list = [];
    while (w.nextNode()) list.push(w.currentNode);
    list.forEach(fix);
  }
  window.iconize = walk;
  const mo = new MutationObserver(ms => { for (const m of ms) m.addedNodes.forEach(walk); });
  function start() { walk(document.body); mo.observe(document.body, { childList: true, subtree: true }); }
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
})();
