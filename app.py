from flask import Flask, render_template, request, redirect, url_for, jsonify
import random
import os
import sqlite3
from dataclasses import dataclass
from werkzeug.utils import secure_filename
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# In-memory store for npc groups.  Each group contains a list of NPC
# instances which track their own hit points.
npc_groups = []  # list of dicts
next_id = 1
settings = {
    "dm_view_health_bar": True,
    "player_view_health_bar": True,
}


def init_db():
    conn = sqlite3.connect("saved_info.db")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            ac INTEGER,
            hp INTEGER,
            count INTEGER,
            damage_die TEXT,
            damage_bonus INTEGER,
            attack_name TEXT,
            attack_bonus INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


@dataclass
class NPC:
    hp: int
    max_hp: int


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    # Calculate total HP for each group before rendering
    for g in npc_groups:
        g["total_hp"] = sum(n.hp for n in g.get("npcs", []))
        g["count"] = len(g.get("npcs", []))
    return render_template("index.html", groups=npc_groups, settings=settings)


@app.route('/player_view', methods=['GET'])
def player_view():
    for g in npc_groups:
        g["count"] = len(g.get("npcs", []))
    return render_template('player_view.html', groups=npc_groups, settings=settings)


@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    if request.method == 'POST':
        settings['dm_view_health_bar'] = 'dm_view_health_bar' in request.form
        settings['player_view_health_bar'] = 'player_view_health_bar' in request.form
    return render_template('settings.html', settings=settings)


@app.route('/add_group', methods=['GET'])
def add_group_page():
    conn = sqlite3.connect('saved_info.db')
    cur = conn.cursor()
    cur.execute('SELECT id, name, ac, hp, count, damage_die, damage_bonus, attack_name, attack_bonus FROM templates')
    rows = cur.fetchall()
    conn.close()
    templates = [
        {
            'id': r[0],
            'name': r[1],
            'ac': r[2],
            'hp': r[3],
            'count': r[4],
            'damage_die': r[5],
            'damage_bonus': r[6],
            'attack_name': r[7],
            'attack_bonus': r[8],
        }
        for r in rows
    ]
    return render_template('add_group.html', templates=templates)

@app.route('/add_group', methods=['POST'])
def add_group():
    global next_id
    data = request.form
    base_hp = int(data.get("hp", 1))
    count = int(data.get("count", 1))
    group = {
        "id": next_id,
        "name": data.get("name", "Darkrider"),
        "ac": int(data.get("ac", 10)),
        "description": data.get("description", ""),
        "damage_die": data.get("damage_die", "1d6"),
        "damage_bonus": int(data.get("damage_bonus", 0)),
        "attack_name": data.get("attack_name", "Attack"),
        "attack_bonus": int(data.get("attack_bonus", 0)),
        "attack_die": "1d20",
        "icon": data.get("name", "default_icon") + ".png",
        "base_hp": base_hp,
        "npcs": [NPC(base_hp, base_hp) for _ in range(count)],
    }
    npc_groups.append(group)
    next_id += 1
    return redirect(url_for('index'))


@app.route('/save_template', methods=['POST'])
def save_template():
    data = request.form
    conn = sqlite3.connect('saved_info.db')
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO templates (name, ac, hp, count, damage_die, damage_bonus, attack_name, attack_bonus) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            data.get('name'),
            int(data.get('ac', 10)),
            int(data.get('hp', 1)),
            int(data.get('count', 1)),
            data.get('damage_die', '1d6'),
            int(data.get('damage_bonus', 0)),
            data.get('attack_name', 'Attack'),
            int(data.get('attack_bonus', 0)),
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for('add_group_page'))

@app.route('/delete_group/<int:group_id>', methods=['POST'])
def delete_group(group_id):
    global npc_groups
    npc_groups = [g for g in npc_groups if g['id'] != group_id]
    return redirect(url_for('index'))

@app.route('/upload_icon/<int:group_id>', methods=['POST'])
def upload_icon(group_id):
    file = request.files.get('icon')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        for g in npc_groups:
            if g['id'] == group_id:
                g['icon'] = filename
    return redirect(url_for('index'))

@app.route("/damage/<int:group_id>", methods=["POST"])
def damage(group_id):
    dmg = int(request.form.get("damage", 0))
    group = next((g for g in npc_groups if g["id"] == group_id), None)
    if group and group.get("npcs"):
        # Target the NPC with the lowest remaining HP
        target = min(group["npcs"], key=lambda n: n.hp)
        target.hp -= dmg
        if target.hp <= 0:
            group["npcs"].remove(target)
    return redirect(url_for("index"))

@app.route("/attack/<int:group_id>", methods=["POST"])
def attack(group_id):
    target_ac = int(request.form.get("target_ac", 10))
    group = next((g for g in npc_groups if g["id"] == group_id), None)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    reach = "reach" in request.form
    attack_limit = 10 if reach else 3

    use_ai = "ai" in request.form

    hits = 0
    misses = 0
    total_damage = 0
    logs = []
    attack_die_count, attack_die_size = map(
        int, group.get("attack_die", "1d20").lower().split("d")
    )
    dmg_die_count, dmg_die_size = map(
        int, group["damage_die"].lower().split("d")
    )
    for idx, _ in enumerate(group.get("npcs", [])[:attack_limit], start=1):
        attack_rolls = [random.randint(1, attack_die_size) for _ in range(attack_die_count)]
        roll_total = sum(attack_rolls)
        attack_total = roll_total + group.get("attack_bonus", 0)
        logs.append(
            f"{group['name']}{idx} rolls to attack: {group['attack_die']}+{group.get('attack_bonus', 0)} = "
            f"{' + '.join(str(r) for r in attack_rolls)} + {group.get('attack_bonus', 0)} = {attack_total} to hit"
        )
        logs.append(f"Player AC is {target_ac}")
        if attack_total >= target_ac:
            logs.append(f"{attack_total}>={target_ac} so that's a hit!")
            dmg_rolls = [random.randint(1, dmg_die_size) for _ in range(dmg_die_count)]
            dmg_total = sum(dmg_rolls) + group.get("damage_bonus", 0)
            logs.append(
                f"{group['name']}{idx} rolls for damage: {group['damage_die']} = "
                f"{' + '.join(str(r) for r in dmg_rolls)} + {group.get('damage_bonus', 0)} = {dmg_total} damage"
            )
            hits += 1
            total_damage += dmg_total
        else:
            logs.append(f"{attack_total}<{target_ac} so that's a miss!")
            misses += 1
    response = {"hits": hits, "damage": total_damage, "logs": logs}

    if use_ai:
        prompt = (
            "Create a short second-person narrative describing the attack upon the player. "
            f"NPC description: {group.get('description', '')}. "
            f"Enemies remaining: {len(group.get('npcs', []))}. "
            f"Hits on the player: {hits}. Misses on the player: {misses}."
        )
        try:
            chat_resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
            )
            narration = chat_resp.choices[0].message.content.strip()
            response["narration"] = narration
        except Exception:
            pass

    return jsonify(response)

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True)
