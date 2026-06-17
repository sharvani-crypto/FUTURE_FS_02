/**
 * Client Lead Management CRM — script.js
 * Handles: search/filter, flash dismiss, sidebar toggle,
 *          AJAX status updates, note adding, delete modal
 */

document.addEventListener('DOMContentLoaded', () => {

  // ── Flash message auto-dismiss ──────────────────────────────
  document.querySelectorAll('.flash').forEach(flash => {
    // Auto-dismiss after 4 seconds
    setTimeout(() => dismissFlash(flash), 4000);
  });

  document.querySelectorAll('.flash-close').forEach(btn => {
    btn.addEventListener('click', () => dismissFlash(btn.closest('.flash')));
  });

  function dismissFlash(el) {
    if (!el) return;
    el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    el.style.opacity = '0';
    el.style.transform = 'translateX(30px)';
    setTimeout(() => el.remove(), 350);
  }

  // ── Sidebar toggle (mobile) ─────────────────────────────────
  const menuToggle = document.getElementById('menuToggle');
  const sidebar    = document.querySelector('.sidebar');
  const overlay    = document.getElementById('sidebarOverlay');

  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      overlay && overlay.classList.toggle('active');
    });

    overlay && overlay.addEventListener('click', closeSidebar);
  }

  function closeSidebar() {
    sidebar && sidebar.classList.remove('open');
    overlay && overlay.classList.remove('active');
  }

  // ── Live search + filter on dashboard table ─────────────────
  const searchInput  = document.getElementById('searchInput');
  const statusFilter = document.getElementById('statusFilter');
  const tableBody    = document.getElementById('leadsTableBody');
  const emptyMsg     = document.getElementById('emptyTableMsg');

  if (searchInput || statusFilter) {
    [searchInput, statusFilter].forEach(el => {
      if (el) el.addEventListener('input', filterLeads);
    });
  }

  function filterLeads() {
    if (!tableBody) return;

    const query  = (searchInput  ? searchInput.value.toLowerCase()  : '');
    const status = (statusFilter ? statusFilter.value.toLowerCase() : '');
    const rows   = tableBody.querySelectorAll('tr.lead-row');
    let   visible = 0;

    rows.forEach(row => {
      const rowText   = row.textContent.toLowerCase();
      const rowStatus = (row.dataset.status || '').toLowerCase();

      const matchesSearch = !query  || rowText.includes(query);
      const matchesStatus = !status || rowStatus === status;

      if (matchesSearch && matchesStatus) {
        row.style.display = '';
        visible++;
      } else {
        row.style.display = 'none';
      }
    });

    // Show/hide empty message
    if (emptyMsg) {
      emptyMsg.style.display = visible === 0 ? '' : 'none';
    }
  }

  // ── AJAX: Update lead status from lead detail page ──────────
  const statusForm = document.getElementById('statusUpdateForm');
  if (statusForm) {
    statusForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form    = e.target;
      const url     = form.action;
      const body    = new FormData(form);
      const btn     = form.querySelector('[type="submit"]');
      const badge   = document.getElementById('currentStatusBadge');

      btn.disabled = true;
      btn.textContent = 'Saving…';

      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          body
        });
        const data = await res.json();

        if (data.success) {
          // Update badge without reload
          if (badge) {
            badge.textContent = data.status;
            badge.className   = 'badge ' + statusBadgeClass(data.status);
          }
          showToast('Status updated to "' + data.status + '"', 'success');
        } else {
          showToast('Failed to update status.', 'error');
        }
      } catch {
        showToast('Something went wrong.', 'error');
      }

      btn.disabled = false;
      btn.textContent = 'Save Status';
    });
  }

  // ── AJAX: Add note from lead detail page ───────────────────
  const noteForm = document.getElementById('noteForm');
  if (noteForm) {
    noteForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form      = e.target;
      const url       = form.action;
      const body      = new FormData(form);
      const btn       = form.querySelector('[type="submit"]');
      const textarea  = form.querySelector('textarea');
      const timeline  = document.getElementById('notesTimeline');
      const emptyNote = document.getElementById('notesEmpty');

      if (!textarea.value.trim()) {
        showToast('Note cannot be empty.', 'error');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Adding…';

      try {
        const res  = await fetch(url, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          body
        });
        const data = await res.json();

        if (data.success) {
          const note = data.note;
          // Prepend new note to timeline
          const noteEl = buildNoteElement(note);
          if (timeline) {
            timeline.insertBefore(noteEl, timeline.firstChild);
          }
          // Hide empty state
          if (emptyNote) emptyNote.style.display = 'none';
          textarea.value = '';
          showToast('Note added.', 'success');
        } else {
          showToast('Failed to add note.', 'error');
        }
      } catch {
        showToast('Something went wrong.', 'error');
      }

      btn.disabled = false;
      btn.textContent = 'Add Note';
    });
  }

  function buildNoteElement(note) {
    const div = document.createElement('div');
    div.className = 'note-item';
    const ts = new Date(note.timestamp).toLocaleString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
    div.innerHTML = `
      <div class="note-dot"><i class="fa-solid fa-pen-nib"></i></div>
      <div class="note-content">
        <p class="note-text">${escapeHtml(note.note)}</p>
        <p class="note-time"><i class="fa-regular fa-clock"></i> ${ts}</p>
      </div>`;
    return div;
  }

  // ── Delete confirmation modal ───────────────────────────────
  const deleteModal   = document.getElementById('deleteModal');
  const confirmDelete = document.getElementById('confirmDelete');
  const cancelDelete  = document.getElementById('cancelDelete');
  let   deleteForm    = null;

  document.querySelectorAll('.btn-delete-lead').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      deleteForm = btn.closest('form');
      if (deleteModal) deleteModal.classList.add('active');
    });
  });

  cancelDelete && cancelDelete.addEventListener('click', () => {
    deleteModal.classList.remove('active');
    deleteForm = null;
  });

  confirmDelete && confirmDelete.addEventListener('click', () => {
    if (deleteForm) deleteForm.submit();
  });

  deleteModal && deleteModal.addEventListener('click', (e) => {
    if (e.target === deleteModal) {
      deleteModal.classList.remove('active');
      deleteForm = null;
    }
  });

  // ── Topbar date ─────────────────────────────────────────────
  const dateEl = document.getElementById('topbarDate');
  if (dateEl) {
    const now = new Date();
    dateEl.textContent = now.toLocaleDateString('en-IN', {
      weekday: 'short', day: 'numeric', month: 'short', year: 'numeric'
    });
  }

  // ── Highlight active nav link ───────────────────────────────
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-item a').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // ── Animated number counters (stats) ───────────────────────
  document.querySelectorAll('.stat-value[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10);
    animateCount(el, 0, target, 700);
  });

  function animateCount(el, from, to, duration) {
    const start = performance.now();
    const update = (time) => {
      const elapsed  = time - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease     = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      el.textContent = Math.round(from + (to - from) * ease);
      if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  }

  // ── Toast notification ──────────────────────────────────────
  function showToast(message, type = 'info') {
    let container = document.querySelector('.flash-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'flash-container';
      document.body.appendChild(container);
    }

    const iconMap = {
      success: 'fa-circle-check',
      error:   'fa-circle-xmark',
      warning: 'fa-triangle-exclamation',
      info:    'fa-circle-info'
    };

    const toast = document.createElement('div');
    toast.className = `flash flash-${type}`;
    toast.innerHTML = `
      <i class="fa-solid ${iconMap[type] || iconMap.info}"></i>
      <span class="flash-text">${escapeHtml(message)}</span>
      <button class="flash-close"><i class="fa-solid fa-xmark"></i></button>`;

    toast.querySelector('.flash-close').addEventListener('click', () => dismissFlash(toast));
    container.appendChild(toast);
    setTimeout(() => dismissFlash(toast), 4000);
  }

  function dismissFlash(el) {
    if (!el) return;
    el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    el.style.opacity  = '0';
    el.style.transform = 'translateX(30px)';
    setTimeout(() => el && el.remove(), 350);
  }

  // ── Helpers ─────────────────────────────────────────────────
  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function statusBadgeClass(status) {
    const map = {
      'Contacted':  'badge-contacted',
      'Follow-up':  'badge-follow-up',
      'Qualified':  'badge-qualified',
      'Closed/Won': 'badge-closed-won',
    };
    return map[status] || 'badge-new';
  }

  // ── Public contact form — show success overlay ──────────────
  const contactForm    = document.getElementById('contactForm');
  const successOverlay = document.getElementById('formSuccess');

  if (contactForm && successOverlay) {
    // Check if URL has ?submitted=1 (after redirect from Flask)
    if (window.location.search.includes('submitted=1')) {
      contactForm.style.display   = 'none';
      successOverlay.style.display = 'block';
    }
  }

  // ── Login form: show spinner on submit ──────────────────────
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
      const btn = loginForm.querySelector('[type="submit"]');
      if (btn) {
        btn.disabled     = true;
        btn.innerHTML    = '<i class="fa-solid fa-circle-notch fa-spin"></i> Logging in…';
      }
    });
  }

  // ── Keyboard: close modal on Escape ─────────────────────────
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (deleteModal && deleteModal.classList.contains('active')) {
        deleteModal.classList.remove('active');
        deleteForm = null;
      }
      closeSidebar();
    }
  });

});