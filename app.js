function createNpcElement(name, maxHealth) {
    const npc = document.createElement('div');
    npc.className = 'npc';
    npc.dataset.health = maxHealth;
    npc.dataset.maxHealth = maxHealth;

    const title = document.createElement('div');
    title.textContent = name;
    npc.appendChild(title);

    const bar = document.createElement('div');
    bar.className = 'health-bar';

    const barInner = document.createElement('div');
    barInner.className = 'health-bar-inner';
    bar.appendChild(barInner);

    npc.appendChild(bar);

    return npc;
}

function updateHealthBars() {
    document.querySelectorAll('.npc').forEach(npc => {
        const max = parseInt(npc.dataset.maxHealth, 10);
        const current = parseInt(npc.dataset.health, 10);
        const percentage = Math.max(0, current) / max * 100;
        npc.querySelector('.health-bar-inner').style.width = percentage + '%';
    });
}

function addNpcGroup() {
    const name = document.getElementById('npc-name').value.trim();
    const count = parseInt(document.getElementById('npc-count').value, 10) || 1;
    const maxHealth = parseInt(document.getElementById('npc-health').value, 10) || 1;
    if (!name) return;

    const grid = document.getElementById('npc-grid');
    for (let i = 0; i < count; i++) {
        const npc = createNpcElement(name, maxHealth);
        grid.appendChild(npc);
    }
    updateHealthBars();
}

function init() {
    document.getElementById('add-npc').addEventListener('click', addNpcGroup);
    updateHealthBars();
}

document.addEventListener('DOMContentLoaded', init);
