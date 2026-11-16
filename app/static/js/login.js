/* Login page: copy buttons and "use this account" for the public demo accounts. No external libraries. */
(function () {
  function fallbackCopy(text) {
    const t = document.createElement('textarea'); t.value = text; t.setAttribute('readonly', '');
    t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select();
    let ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(t); return ok;
  }
  function flash(btn, ok) {
    const old = btn.dataset.label || btn.textContent; btn.dataset.label = old;
    btn.textContent = ok ? 'Copiado ✓' : 'Copia manual'; btn.classList.toggle('ok', ok);
    setTimeout(() => { btn.textContent = old; btn.classList.remove('ok'); }, 1600);
  }
  document.querySelectorAll('button.copy').forEach(btn => btn.addEventListener('click', () => {
    const text = btn.dataset.copy;
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => flash(btn, true), () => flash(btn, fallbackCopy(text)));
    } else { flash(btn, fallbackCopy(text)); }
  }));
  const email = document.getElementById('email'), pwd = document.getElementById('password');
  document.querySelectorAll('.use-acc').forEach(btn => btn.addEventListener('click', () => {
    const card = btn.closest('.demo-acc'); if (!card || !email || !pwd) return;
    email.value = card.dataset.email; pwd.value = card.dataset.password;
    document.querySelectorAll('.demo-acc').forEach(c => c.classList.remove('used')); card.classList.add('used');
    const submit = document.querySelector('#login-form [type=submit]'); if (submit) submit.focus();
  }));
})();
