document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('#gift-search');
  const cards = [...document.querySelectorAll('.gift-card')];
  const filters = [...document.querySelectorAll('[data-filter]')];
  const viewButtons = [...document.querySelectorAll('[data-view]')];
  const grid = document.querySelector('#gift-grid');
  const empty = document.querySelector('#filter-empty');
  const storageKey = 'cadeaulijst-view';
  const defaultView = 'list';
  let currentFilter = 'all';

  function setView(view, persist = true) {
    if (!grid || !['grid', 'list'].includes(view)) return;
    grid.dataset.view = view;
    viewButtons.forEach(button => {
      const active = button.dataset.view === view;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    if (persist) {
      try { localStorage.setItem(storageKey, view); } catch (_) {}
    }
  }

  function sortCards() {
    if (!grid) return;
    [...cards]
      .sort((a, b) => Number(a.dataset.status === 'bought') - Number(b.dataset.status === 'bought'))
      .forEach(card => grid.appendChild(card));
  }

  function applyFilters() {
    const term = (search?.value || '').trim().toLocaleLowerCase('nl');
    let count = 0;
    cards.forEach(card => {
      const show = card.dataset.name.includes(term) && (currentFilter === 'all' || card.dataset.status === currentFilter);
      card.hidden = !show;
      if (show) count += 1;
    });
    if (empty) empty.hidden = count !== 0;
  }

  function startCountdown() {
    const countdown = document.querySelector('[data-countdown-target]');
    if (!countdown) return;
    const target = new Date(countdown.dataset.countdownTarget);
    const days = document.querySelector('#countdown-days');
    const hours = document.querySelector('#countdown-hours');
    const minutes = document.querySelector('#countdown-minutes');
    const seconds = document.querySelector('#countdown-seconds');
    const message = document.querySelector('#countdown-message');

    function updateCountdown() {
      const remaining = Math.max(0, target.getTime() - Date.now());
      const totalSeconds = Math.floor(remaining / 1000);
      const dayValue = Math.floor(totalSeconds / 86400);
      const hourValue = Math.floor((totalSeconds % 86400) / 3600);
      const minuteValue = Math.floor((totalSeconds % 3600) / 60);
      const secondValue = totalSeconds % 60;
      if (days) days.textContent = String(dayValue).padStart(3, '0');
      if (hours) hours.textContent = String(hourValue).padStart(2, '0');
      if (minutes) minutes.textContent = String(minuteValue).padStart(2, '0');
      if (seconds) seconds.textContent = String(secondValue).padStart(2, '0');
      if (remaining === 0 && message) message.textContent = 'Vandaag is Sara jarig!';
      return remaining;
    }

    if (updateCountdown() > 0) {
      const timer = window.setInterval(() => {
        if (updateCountdown() === 0) window.clearInterval(timer);
      }, 1000);
    }
  }

  try {
    const savedView = localStorage.getItem(storageKey);
    setView(savedView === 'grid' || savedView === 'list' ? savedView : defaultView, false);
  } catch (_) {
    setView(defaultView, false);
  }

  startCountdown();
  sortCards();
  applyFilters();

  viewButtons.forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
  search?.addEventListener('input', applyFilters);

  filters.forEach(button => button.addEventListener('click', () => {
    currentFilter = button.dataset.filter;
    filters.forEach(item => {
      const active = item === button;
      item.classList.toggle('active', active);
      item.setAttribute('aria-pressed', String(active));
    });
    applyFilters();
  }));

  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll('.gift-toggle').forEach(input => {
    input.addEventListener('change', async () => {
      const wanted = input.checked;
      const card = input.closest('.gift-card');
      const status = card.querySelector('.status');
      const feedback = document.querySelector('#save-feedback');
      input.disabled = true;
      try {
        const data = new FormData();
        data.set('id', input.dataset.id);
        data.set('checked', String(wanted));
        data.set('csrf_token', input.dataset.csrf);
        const response = await fetch(input.dataset.url, {method: 'POST', body: data, credentials: 'same-origin'});
        if (!response.ok) throw new Error('Opslaan mislukt');
        const result = await response.json();
        card.dataset.status = wanted ? 'bought' : 'available';
        card.classList.toggle('is-bought', wanted);
        status.textContent = wanted ? 'Gekocht' : 'Beschikbaar';
        status.classList.toggle('status-bought', wanted);
        status.classList.toggle('status-available', !wanted);
        const available = document.querySelector('#available-count');
        if (available) available.textContent = result.total - result.boughtCount;
        if (feedback) feedback.textContent = 'Wijziging opgeslagen.';
        sortCards();
        applyFilters();
      } catch (error) {
        input.checked = !wanted;
        if (feedback) feedback.textContent = 'Opslaan mislukt. Ververs de pagina en probeer opnieuw.';
        window.alert('Opslaan mislukt. Ververs de pagina en probeer opnieuw.');
      } finally {
        input.disabled = false;
      }
    });
  });
});
