document.getElementById('add-group-btn').addEventListener('click', (e) => {
  e.preventDefault();
  window.location.href = '/add_group';
});

function addLog(text) {
  const logBox = document.getElementById('log');
  if (!logBox) return;
  const div = document.createElement('div');
  if (/^Narration:/i.test(text)) {
    div.classList.add('log-narration');
  } else if (/roll/i.test(text)) {
    div.classList.add('log-roll');
  } else if (/player/i.test(text)) {
    div.classList.add('log-player');
  } else {
    div.classList.add('log-npc');
  }
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

        // Always show damage summary in the log
        addLog(`${groupName} ${attackName}: ${data.hits} hits for a total of ${data.damage} damage`);

        // Include any AI generated narration as a separate entry
        if (data.narration) {
          addLog(`Narration: ${data.narration}`);
        }

        if (Array.isArray(data.logs)) {
          data.logs.forEach(l => addLog(l));
        }
      });
  });
});

// Handle mob damage without page reload
document.querySelectorAll('.damage-form').forEach(form => {
  form.addEventListener('submit', e => {
    e.preventDefault();
    const fd = new FormData(form);
    fetch(form.action, { method: 'POST', body: fd })
      .then(res => res.json())
      .then(data => {
        const group = form.closest('.group');
        if (!group) return;
        // Update stats line
        const statsSpan = group.querySelector('.stats-row span');
        if (statsSpan) {
          statsSpan.textContent = `Total Group HP: ${data.total_hp} Enemies Remaining: ${data.count}`;
        }
        const cells = group.querySelectorAll('.grid .cell');
        // Update each cell's HP label and bar
        data.npc_hps.forEach((hp, idx) => {
          const cell = cells[idx];
          if (!cell) return;
          const hpLabel = cell.querySelector('.hp-label');
          if (hpLabel) hpLabel.textContent = hp;
          const bar = cell.querySelector('.hp-bar');
          if (bar) {
            const max = parseInt(cell.dataset.maxHp || hp, 10) || 1;
            const pct = Math.floor((hp / max) * 100);
            bar.className = 'hp-bar ' + (pct >= 76 ? 'green' : pct >= 50 ? 'yellow' : pct >= 25 ? 'orange' : 'red');
          }
        });
        // Remove dead cells
        for (let i = data.npc_hps.length; i < cells.length; i++) {
          cells[i].remove();
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
