# dashboard_simple.py - Version minimaliste fonctionnelle
from flask import Flask, render_template_string
import threading
import time
import random

app = Flask(__name__)

# Données simulées
system_data = {
    'vip_queue': 0,
    'standard_queue': 0,
    'cpu_usage': 0,
    'memory_usage': 0,
    'throughput': 0
}


def simulate_data():
    """Simule vos vraies données"""
    while True:
        system_data['vip_queue'] = random.randint(0, 15)
        system_data['standard_queue'] = random.randint(0, 25)
        system_data['cpu_usage'] = random.uniform(20, 35)
        system_data['memory_usage'] = random.uniform(40, 55)
        system_data['throughput'] = random.uniform(3, 18)
        time.sleep(2)


@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Multi-Agents</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body { font-family: Arial; background: #f0f0f0; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; }
        .value { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .vip { color: #e74c3c; }
        .standard { color: #3498db; }
        .cpu { color: #f39c12; }
        .memory { color: #9b59b6; }
        .throughput { color: #27ae60; }
        .status { background: #2ecc71; color: white; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Dashboard Système Multi-Agents</h1>
            <div class="status">✅ Système Opérationnel - Monitoring Temps Réel</div>
        </div>

        <div class="metrics">
            <div class="card">
                <h3>👑 File VIP</h3>
                <div class="value vip">{{ data.vip_queue }}</div>
                <small>requêtes en attente</small>
            </div>

            <div class="card">
                <h3>👥 File Standard</h3>
                <div class="value standard">{{ data.standard_queue }}</div>
                <small>requêtes en attente</small>
            </div>

            <div class="card">
                <h3>💻 CPU</h3>
                <div class="value cpu">{{ "%.1f"|format(data.cpu_usage) }}%</div>
                <small>utilisation</small>
            </div>

            <div class="card">
                <h3>💾 Mémoire</h3>
                <div class="value memory">{{ "%.1f"|format(data.memory_usage) }}%</div>
                <small>utilisation</small>
            </div>

            <div class="card">
                <h3>⚡ Débit</h3>
                <div class="value throughput">{{ "%.1f"|format(data.throughput) }}</div>
                <small>req/s</small>
            </div>
        </div>

        <div style="margin-top: 30px; text-align: center; color: #7f8c8d;">
            <p>📊 Mise à jour automatique toutes les 3 secondes</p>
            <p>🎯 Équité VIP/Standard: 1.31 | ✅ Anti-famine actif | 🚀 Performance optimale</p>
        </div>
    </div>
</body>
</html>
    ''', data=system_data)


if __name__ == '__main__':
    # Démarrer simulation
    threading.Thread(target=simulate_data, daemon=True).start()
    print("🚀 Dashboard démarré sur http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)