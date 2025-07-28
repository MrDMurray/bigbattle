document.getElementById('add-group-btn').addEventListener('click', (e) => {
  e.preventDefault();
  window.location.href = '/add_group';
});

function addLog(text) {
  const logBox = document.getElementById('log');
  if (!logBox) return;
  const div = document.createElement('div');
  div.textContent = text;
  logBox.appendChild(div);
  logBox.scrollTop = logBox.scrollHeight;
  while (logBox.children.length > 50) {
    logBox.removeChild(logBox.firstChild);
  }
}

// Delete handlers
document.querySelectorAll('.delete-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const id = btn.dataset.id;
    fetch(`/delete_group/${id}`, { method: 'POST' })
      .then(() => window.location.reload());
  });
});

// AJAX attack handling
document.querySelectorAll('.attack-form').forEach(form => {
  form.addEventListener('submit', e => {
    e.preventDefault();
    const fd = new FormData(form);
    const acSpan = form.parentElement.querySelector('.player-ac .ac-value');
    if (acSpan) {
      fd.append('target_ac', parseInt(acSpan.textContent, 10));
    }
    fetch(form.action, { method: 'POST', body: fd })
      .then(res => res.json())
      .then(data => {
        const container = form.closest('.info');
        const result = container ? container.querySelector('.attack-result') : null;
        if (result) {
          result.textContent = `${data.hits} hits for a total of ${data.damage} damage`;
        }
        const groupName = form.dataset.groupName || 'Group';
        const attackName = form.dataset.attackName || 'Attack';
        addLog(`${groupName} ${attackName}: ${data.hits} hits for a total of ${data.damage} damage`);
        if (Array.isArray(data.logs)) {
          data.logs.forEach(l => addLog(l));
        }
      });
  });
});

// Player AC adjustment
document.querySelectorAll('.ac-inc').forEach(btn => {
  btn.addEventListener('click', () => {
    const span = btn.parentElement.querySelector('.ac-value');
    span.textContent = parseInt(span.textContent, 10) + 1;
  });
});

document.querySelectorAll('.ac-dec').forEach(btn => {
  btn.addEventListener('click', () => {
    const span = btn.parentElement.querySelector('.ac-value');
    span.textContent = Math.max(0, parseInt(span.textContent, 10) - 1);
  });
});

// Auto upload icon when file chosen
document.querySelectorAll('.upload-form input[type="file"]').forEach(input => {
  input.addEventListener('change', () => {
    if (input.files.length > 0) {
      input.closest('form').submit();
    }
  });
});

// Quick dice rolls
document.querySelectorAll('#dice-buttons .dice-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const sides = parseInt(btn.dataset.die, 10);
    const roll = Math.floor(Math.random() * sides) + 1;
    const original = btn.textContent;
    btn.textContent = roll;
    addLog(`d${sides} roll: ${roll}`);
    setTimeout(() => {
      btn.textContent = original;
    }, 10000);
  });
});
