from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import random
import os
import sqlite3
import json
from dataclasses import dataclass
from werkzeug.utils import secure_filename
import openai
initial_openai_key = ""
if os.path.exists("thekey.txt"):
    with open("thekey.txt", "r") as f:
        initial_openai_key = f.read().strip()
if not initial_openai_key:
    initial_openai_key = os.getenv("OPENAI_API_KEY", "")

openai.api_key = initial_openai_key
if not openai.api_key:
    print("WARNING: OpenAI API key not configured")
else:
    print("DEBUG: OpenAI API key loaded from environment or file")

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
    "openai_api_key": initial_openai_key,
}
openai.api_key = settings["openai_api_key"]


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
            attack_bonus INTEGER,
            description TEXT
        )
        """
    )
    cur.execute("PRAGMA table_info(templates)")
    cols = [r[1] for r in cur.fetchall()]
    if "description" not in cols:
        cur.execute("ALTER TABLE templates ADD COLUMN description TEXT")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            saved_at TEXT,
            data TEXT
        )
        """
    )
    cur.execute("PRAGMA table_info(sessions)")
    s_cols = [r[1] for r in cur.fetchall()]
    if "name" not in s_cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN name TEXT")
    if "saved_at" not in s_cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN saved_at TEXT")
    if "data" not in s_cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN data TEXT")
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
        settings['openai_api_key'] = request.form.get('openai_api_key', '').strip()
        openai.api_key = settings['openai_api_key']
        with open('thekey.txt', 'w') as f:
            f.write(settings['openai_api_key'])
    return render_template('settings.html', settings=settings)


@app.route('/add_group', methods=['GET'])
def add_group_page():
    conn = sqlite3.connect('saved_info.db')
    cur = conn.cursor()
    cur.execute('SELECT id, name, ac, hp, count, damage_die, damage_bonus, attack_name, attack_bonus, description FROM templates')
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
            'description': r[9],
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
        'INSERT INTO templates (name, ac, hp, count, damage_die, damage_bonus, attack_name, attack_bonus, description) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            data.get('name'),
            int(data.get('ac', 10)),
            int(data.get('hp', 1)),
            int(data.get('count', 1)),
            data.get('damage_die', '1d6'),
            int(data.get('damage_bonus', 0)),
            data.get('attack_name', 'Attack'),
            int(data.get('attack_bonus', 0)),
            data.get('description', ''),
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


@app.route('/delete_template/<int:template_id>', methods=['POST'])
def delete_template(template_id):
    conn = sqlite3.connect('saved_info.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM templates WHERE id=?', (template_id,))
    conn.commit()
    conn.close()
    return ('', 204)

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


def _serialize_groups():
    return [
        {
            'id': g['id'],
            'name': g['name'],
            'ac': g['ac'],
            'description': g.get('description', ''),
            'damage_die': g.get('damage_die', '1d6'),
            'damage_bonus': g.get('damage_bonus', 0),
            'attack_name': g.get('attack_name', 'Attack'),
            'attack_bonus': g.get('attack_bonus', 0),
            'attack_die': g.get('attack_die', '1d20'),
            'icon': g.get('icon', ''),
            'base_hp': g.get('base_hp', 1),
            'npcs': [{'hp': n.hp, 'max_hp': n.max_hp} for n in g.get('npcs', [])],
        }
        for g in npc_groups
    ]


def _deserialize_groups(data):
    return [
        {
            'id': g['id'],
            'name': g['name'],
            'ac': g.get('ac', 10),
            'description': g.get('description', ''),
            'damage_die': g.get('damage_die', '1d6'),
            'damage_bonus': g.get('damage_bonus', 0),
            'attack_name': g.get('attack_name', 'Attack'),
            'attack_bonus': g.get('attack_bonus', 0),
            'attack_die': g.get('attack_die', '1d20'),
            'icon': g.get('icon', ''),
            'base_hp': g.get('base_hp', 1),
            'npcs': [NPC(n['hp'], n.get('max_hp', n['hp'])) for n in g.get('npcs', [])],
        }
        for g in data
    ]


@app.route('/save_session', methods=['POST'])
def save_session():
    conn = sqlite3.connect('saved_info.db')
    cur = conn.cursor()
    session_data = {
        'npc_groups': _serialize_groups(),
        'next_id': next_id,
        'settings': settings,
    }
    name = request.form.get('session_name', '').strip() or 'Unnamed Session'
    saved_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute(
        'INSERT INTO sessions (name, saved_at, data) VALUES (?, ?, ?)',
        (name, saved_at, json.dumps(session_data)),
    )
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/load_session', methods=['GET'])
def load_session_page():
    conn = sqlite3.connect('saved_info.db')
    cur = conn.cursor()
    cur.execute('SELECT id, name, saved_at FROM sessions ORDER BY saved_at DESC')
    rows = cur.fetchall()
    conn.close()
    sessions = [
        {'id': r[0], 'name': r[1], 'saved_at': r[2]} for r in rows
    ]
    return render_template('load_session.html', sessions=sessions)


@app.route('/load_session/<int:session_id>', methods=['POST'])
def load_session(session_id):
    global npc_groups, next_id
    conn = sqlite3.connect('saved_info.db')
    cur = conn.cursor()
    cur.execute('SELECT data FROM sessions WHERE id=?', (session_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        data = json.loads(row[0])
        npc_groups = _deserialize_groups(data.get('npc_groups', []))
        next_id = data.get('next_id', 1)
        settings.update(data.get('settings', {}))
    return redirect(url_for('index'))


@app.route('/clear_session', methods=['POST'])
def clear_session():
    global npc_groups, next_id
    npc_groups = []
    next_id = 1
    return redirect(url_for('index'))

@app.route("/damage/<int:group_id>", methods=["POST"])
def damage(group_id):
    dmg = int(request.form.get("damage", 0))
    targets_raw = request.form.get("targets", "")
    group = next((g for g in npc_groups if g["id"] == group_id), None)
    if group and group.get("npcs"):
        if targets_raw:
            indices = sorted(
                {
                    int(i)
                    for i in targets_raw.split(",")
                    if i.strip().isdigit()
                },
                reverse=True,
            )
            for idx in indices:
                if 0 <= idx < len(group["npcs"]):
                    npc = group["npcs"][idx]
                    npc.hp -= dmg
                    if npc.hp <= 0:
                        del group["npcs"][idx]
        else:
            # Target the NPC with the lowest remaining HP
            target = min(group["npcs"], key=lambda n: n.hp)
            target.hp -= dmg
            if target.hp <= 0:
                group["npcs"].remove(target)
    total_hp = sum(n.hp for n in group.get("npcs", [])) if group else 0
    count = len(group.get("npcs", [])) if group else 0
    npc_hps = [n.hp for n in group.get("npcs", [])] if group else []
    return jsonify({"total_hp": total_hp, "count": count, "npc_hps": npc_hps})

@app.route("/attack/<int:group_id>", methods=["POST"])
def attack(group_id):
    target_ac = int(request.form.get("target_ac", 10))
    group = next((g for g in npc_groups if g["id"] == group_id), None)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    reach = "reach" in request.form
    attack_limit = 10 if reach else 3

    use_ai = "ai" in request.form
    advantage = "advantage" in request.form
    disadvantage = "disadvantage" in request.form
    if advantage and disadvantage:
        advantage = disadvantage = False

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
        first_rolls = [random.randint(1, attack_die_size) for _ in range(attack_die_count)]
        first_total = sum(first_rolls)
        chosen_total = first_total
        desc = ""
        if advantage or disadvantage:
            second_rolls = [random.randint(1, attack_die_size) for _ in range(attack_die_count)]
            second_total = sum(second_rolls)
            if advantage:
                chosen_total = max(first_total, second_total)
                desc = "with advantage"
            else:
                chosen_total = min(first_total, second_total)
                desc = "with disadvantage"
            logs.append(
                f"{group['name']}{idx} rolls to attack {desc}: {first_total} and {second_total}"
            )
            logs.append(
                f"Using {'highest' if advantage else 'lowest'} roll {chosen_total}"
            )
            attack_total = chosen_total + group.get("attack_bonus", 0)
            logs.append(
                f"{chosen_total} + {group.get('attack_bonus', 0)} = {attack_total} to hit"
            )
        else:
            logs.append(
                f"{group['name']}{idx} rolls to attack: {group['attack_die']}+{group.get('attack_bonus', 0)} = "
                f"{' + '.join(str(r) for r in first_rolls)} + {group.get('attack_bonus', 0)} = {first_total + group.get('attack_bonus', 0)} to hit"
            )
            attack_total = chosen_total + group.get("attack_bonus", 0)
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
        openai.api_key = settings.get("openai_api_key", "")
        prompt = (
            "Create a short second-person description, describing an attack upon the player for a DnD mob battle app that describes a simple attack roll in an epic way. The location is in the middle of a huge battle and the player has been fighting multiple enemies in the chaos. There is no need to describe the setting, only describe the attack itself. This particular attack has the following features:"
            f"NPC description: {group.get('description', '')}. "
            f"Enemies remaining: {len(group.get('npcs', []))}. "
            f"Hits on the player: {hits}. Misses on the player: {misses}."
            f"Keep the narration to 50 words or less and make sure to describe the damage each hit does to the player's body as well as each miss either deflected or dodged"
        )
        print(f"DEBUG: OpenAI prompt: {prompt}")
        try:
            chat_resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            narration = chat_resp.choices[0].message.content.strip()
            response["narration"] = narration
            print(f"DEBUG: OpenAI narration: {narration}")
        except Exception as e:
            print(f"ERROR calling OpenAI API: {e}")

    print(f"DEBUG: attack response: {response}")
    return jsonify(response)

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True)
