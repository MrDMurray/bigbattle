document.getElementById('add-group-btn').addEventListener('click', () => {
  const name = prompt('NPC Name', 'Darkrider');
  const ac = prompt('AC', '10');
  const hp = prompt('HP', '10');
  const count = prompt('Count (max 25)', '5');
  const damage_die = prompt('Damage Die (e.g., 1d6)', '1d6');
  const damage_bonus = prompt('Damage Bonus', '0');
  if (name && ac && hp && count) {
    const form = document.createElement('form');
    form.method = 'POST'; form.action = '/add_group';
    [ ['name', name], ['ac', ac], ['hp', hp], ['count', count], ['damage_die', damage_die], ['damage_bonus', damage_bonus] ]
      .forEach(([k,v]) => { let inp = document.createElement('input'); inp.type='hidden'; inp.name=k; inp.value=v; form.appendChild(inp); });
    document.body.appendChild(form);
    form.submit();
  }
});

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
    fetch(form.action, { method: 'POST', body: new FormData(form) })
      .then(res => res.json())
      .then(data => {
        alert(`${data.hits} hits, ${data.damage} total damage`);
      });
  });
});
