from flask import Flask, render_template, request, redirect, url_for, jsonify
import random
import os
from dataclasses import dataclass
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# In-memory store for npc groups.  Each group contains a list of NPC
# instances which track their own hit points.
npc_groups = []  # list of dicts
next_id = 1


@dataclass
class NPC:
    hp: int


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    # Calculate total HP for each group before rendering
    for g in npc_groups:
        g["total_hp"] = sum(n.hp for n in g.get("npcs", []))
        g["count"] = len(g.get("npcs", []))
    return render_template("index.html", groups=npc_groups)


@app.route('/add_group', methods=['GET'])
def add_group_page():
    return render_template('add_group.html')

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
        "damage_die": data.get("damage_die", "1d6"),
        "damage_bonus": int(data.get("damage_bonus", 0)),
        "icon": data.get("name", "default_icon") + ".png",
        "npcs": [NPC(base_hp) for _ in range(count)],
    }
    npc_groups.append(group)
    next_id += 1
    return redirect(url_for('index'))

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

    hits = 0
    total_damage = 0
    for _ in range(len(group.get("npcs", []))):
        roll = random.randint(1, 20)
        attack_total = roll + group["damage_bonus"]
        if attack_total >= target_ac:
            hits += 1
            die_count, die_size = map(int, group["damage_die"].lower().split("d"))
            dmg = (
                sum(random.randint(1, die_size) for _ in range(die_count))
                + group["damage_bonus"]
            )
            total_damage += dmg
    return jsonify({"hits": hits, "damage": total_damage})

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)