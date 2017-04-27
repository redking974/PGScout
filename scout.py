import logging
import time
from Queue import Queue
from threading import Thread

from flask import Flask, request, jsonify

from pgscout.ScoutAccount import ScoutAccount
from pgscout.ScoutJob import ScoutJob
from pgscout.cache import get_cached_encounter, cache_encounter
from pgscout.config import cfg_get
from pgscout.utils import get_pokemon_name

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(threadName)16s][%(module)14s][%(levelname)8s] %(message)s')

log = logging.getLogger(__name__)

# Silence some loggers
logging.getLogger('pgoapi.pgoapi').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__, static_folder='icons', static_url_path='')

scouts = []
jobs = Queue()

# ===========================================================================


@app.route("/iv", methods=['GET'])
def get_iv():
    # Check cache once in a non-blocking way
    encounter_id = request.args["encounter_id"]
    pokemon_id = request.args["pokemon_id"]
    pokemon_name = get_pokemon_name(pokemon_id)
    result = get_cached_encounter(encounter_id)
    if result:
        log.info(
            u"Returning cached result: level {} {} with CP {}.".format(result['level'], pokemon_name, result['cp']))
        return jsonify(result)

    # Create a ScoutJob
    spawn_point_id = request.args["spawn_point_id"]
    lat = request.args["latitude"]
    lng = request.args["longitude"]
    job = ScoutJob(pokemon_id, encounter_id, spawn_point_id, lat, lng)

    # Enqueue and wait for job to be processed
    jobs.put(job)
    while not job.processed:
        time.sleep(1)

    # Cache successful jobs and return result
    if job.result['success']:
        cache_encounter(encounter_id, job.result)
    return jsonify(job.result)


def run_webserver():
    app.run(threaded=True, port=cfg_get('port'))


# ===========================================================================

log.info("PGScout starting up.")

with open(cfg_get('accounts_file'), 'r') as f:
    for num, line in enumerate(f, 1):
        fields = line.split(",")
        fields = map(str.strip, fields)
        scout = ScoutAccount(fields[0], fields[1], fields[2], jobs)
        scouts.append(scout)
        t = Thread(target=scout.run, name="s_{}".format(scout.username))
        t.daemon = True
        t.start()

# Launch the webserver
t = Thread(target=run_webserver, name='webserver')
t.daemon = True
t.start()

while True:
    time.sleep(1)