from flask import Flask, render_template, request, redirect, url_for, jsonify
import random, os
from werkzeug.utils import secure_filename

print("hello world")

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory store for npc groups
npc_groups = []  # list of dicts: {id, name, ac, hp, damage_die, damage_bonus, count, icon}
next_id = 1


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', groups=npc_groups)

@app.route('/add_group', methods=['POST'])
def add_group():
    global next_id
    data = request.form
    group = {
        'id': next_id,
        'name': data.get('name', 'Darkrider'),
        'ac': int(data.get('ac', 10)),
        'hp': int(data.get('hp', 1)),
        'damage_die': data.get('damage_die', '1d6'),
        'damage_bonus': int(data.get('damage_bonus', 0)),
        'count': int(data.get('count', 1)),
        'icon': data.get('name', 'default_icon') + '.png'
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

@app.route('/attack/<int:group_id>', methods=['POST'])
def attack(group_id):
    target_ac = int(request.form.get('target_ac', 10))
    group = next((g for g in npc_groups if g['id'] == group_id), None)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    hits = 0
    total_damage = 0
    for _ in range(group['count']):
        roll = random.randint(1, 20)
        attack_total = roll + (group['damage_bonus'])
        if attack_total >= target_ac:
            hits += 1
            die_count, die_size = map(int, group['damage_die'].lower().split('d'))
            dmg = sum(random.randint(1, die_size) for _ in range(die_count)) + group['damage_bonus']
            total_damage += dmg
    return jsonify({'hits': hits, 'damage': total_damage})

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)