const form = document.getElementById('group-form');
const loadBtn = document.getElementById('load-template-btn');
const saveBtn = document.getElementById('save-template-btn');
const deleteBtn = document.getElementById('delete-template-btn');
const select = document.getElementById('template-select');

if (loadBtn && select && form) {
  loadBtn.addEventListener('click', () => {
    const opt = select.options[select.selectedIndex];
    if (!opt || !opt.dataset.name) return;
    form.elements['name'].value = opt.dataset.name;
    form.elements['ac'].value = opt.dataset.ac;
    form.elements['hp'].value = opt.dataset.hp;
    form.elements['count'].value = opt.dataset.count;
    form.elements['damage_die'].value = opt.dataset.damage_die;
    form.elements['damage_bonus'].value = opt.dataset.damage_bonus;
    form.elements['attack_name'].value = opt.dataset.attack_name;
    form.elements['attack_bonus'].value = opt.dataset.attack_bonus;
    form.elements['description'].value = opt.dataset.description || '';
  });
}

if (saveBtn && form) {
  saveBtn.addEventListener('click', () => {
    const fd = new FormData(form);
    fetch('/save_template', { method: 'POST', body: fd })
      .then(() => window.location.reload());
  });
}

if (deleteBtn && select) {
  deleteBtn.addEventListener('click', () => {
    const opt = select.options[select.selectedIndex];
    if (!opt || !opt.value) return;
    if (!confirm('Delete this template?')) return;
    fetch(`/delete_template/${opt.value}`, { method: 'POST' })
      .then(() => window.location.reload());
  });
}
