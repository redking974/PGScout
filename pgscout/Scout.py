import logging
import sys
import time
from base64 import b64decode

from pgoapi import PGoApi
from pgoapi.exceptions import AuthException

from pgscout import request_pause
from pgscout.config import cfg_get
from pgscout.moveset_grades import get_moveset_grades
from pgscout.utils import jitter_location, TooManyLoginAttempts, has_captcha, calc_pokemon_level, \
    get_player_level, calc_iv

log = logging.getLogger(__name__)


class Scout(object):
    def __init__(self, auth, username, password, job_queue):
        self.auth = auth
        self.username = username
        self.password = password
        self.job_queue = job_queue

        self.last_request = None

        # instantiate pgoapi
        self.api = PGoApi()
        self.api.activate_hash_server(cfg_get('hash_key'))

    def run(self):
        log.info("Scout account {} waiting for jobs...".format(self.username))
        while True:
            job = self.job_queue.get()
            try:
                job.result = self.scout_by_encounter_id(job)
            except:
                job.result = self.scout_error(repr(sys.exc_info()))
            job.processed = True

    def needs_rest_for(self):
        if not self.last_request:
            return -sys.maxint - 1
        return request_pause - (time.time() - self.last_request)

    def scout_by_encounter_id(self, job):
        log.info(u"Scouting a {} at {}, {} with account {}".format(job.pokemon_name, job.lat, job.lng, self.username))
        step_location = jitter_location([job.lat, job.lng, 42])

        self.api.set_position(*step_location)
        self.check_login()

        response = self.encounter_request(job.encounter_id, job.spawn_point_id, job.lat,
                                          job.lng)

        return self.parse_encounter_response(response, job.pokemon_id, job.pokemon_name)

    def parse_encounter_response(self, response, pokemon_id, pokemon_name):
        if response is None:
            return self.scout_error("Encounter response is None.")

        if has_captcha(response):
            return self.scout_error("Scout account captcha'd.")

        encounter = response.get('responses', {}).get('ENCOUNTER', {})

        if encounter.get('status', None) == 3:
            return self.scout_error("Pokemon already despawned.")

        if 'wild_pokemon' not in encounter:
            return self.scout_error("No wild pokemon info found.")

        scout_level = get_player_level(response)
        reliable_iv = scout_level >= 25
        reliable_cp = scout_level >= 30

        pokemon_info = encounter['wild_pokemon']['pokemon_data']
        cp = pokemon_info['cp']
        pokemon_level = calc_pokemon_level(pokemon_info['cp_multiplier'])
        probs = encounter['capture_probability']['capture_probability']

        at = pokemon_info.get('individual_attack', 0)
        df = pokemon_info.get('individual_defense', 0)
        st = pokemon_info.get('individual_stamina', 0)
        iv = calc_iv(at, df, st)
        moveset_grades = get_moveset_grades(pokemon_id, pokemon_name, pokemon_info['move_1'], pokemon_info['move_2'])

        response = {
            'success': True,
            'height': pokemon_info['height_m'],
            'weight': pokemon_info['weight_kg'],
            'gender': pokemon_info['pokemon_display']['gender'],
            'iv_percent': iv if reliable_iv else None,
            'iv_attack': at if reliable_iv else None,
            'iv_defense': df if reliable_iv else None,
            'iv_stamina': st if reliable_iv else None,
            'move_1': pokemon_info['move_1'] if reliable_iv else None,
            'move_2': pokemon_info['move_2'] if reliable_iv else None,
            'rating_attack': moveset_grades['offense'] if reliable_iv else None,
            'rating_defense': moveset_grades['defense'] if reliable_iv else None,
            'cp': cp if reliable_cp else None,
            'level': pokemon_level if reliable_cp else None,
            'catch_prob_1': probs[0] if reliable_cp else None,
            'catch_prob_2': probs[1] if reliable_cp else None,
            'catch_prob_3': probs[2] if reliable_cp else None,
            'scout_level': scout_level,
            'encountered_time': time.time()
        }
        log.info(u"Found a {:.1f}% lvl {} {} with {} CP (scout level {}).".format(iv, pokemon_level,
                                                                                  pokemon_name, cp, scout_level))
        return response

    def check_login(self):
        # Logged in? Enough time left? Cool!
        if self.api._auth_provider and self.api._auth_provider._ticket_expire:
            remaining_time = self.api._auth_provider._ticket_expire / 1000 - time.time()
            if remaining_time > 60:
                log.debug(
                    'Credentials remain valid for another %f seconds.',
                    remaining_time)
                return

        # Try to login. Repeat a few times, but don't get stuck here.
        num_tries = 0
        # One initial try + login_retries.
        while num_tries < 3:
            try:
                self.api.set_authentication(
                    provider=self.auth,
                    username=self.username,
                    password=self.password)
                break
            except AuthException:
                num_tries += 1
                log.error(
                    ('Failed to login to Pokemon Go with account %s. ' +
                     'Trying again in %g seconds.'),
                    self.username, 6)
                time.sleep(6)

        if num_tries >= 3:
            log.error(
                ('Failed to login to Pokemon Go with account %s in ' +
                 '%d tries. Giving up.'),
                self.username, num_tries)
            raise TooManyLoginAttempts('Exceeded login attempts.')

        log.debug('Login for account %s successful. Waiting another 20 seconds.', self.username)
        time.sleep(20)

    def encounter_request(self, encounter_id, spawn_point_id, latitude, longitude):
        req = self.api.create_request()
        req.encounter(
            encounter_id=long(b64decode(encounter_id)),
            spawn_point_id=spawn_point_id,
            player_latitude=float(latitude),
            player_longitude=float(longitude))
        return self.perform_request(req)

    def perform_request(self, req, delay=12):
        req.check_challenge()
        req.get_hatched_eggs()
        req.get_inventory()
        req.check_awarded_badges()
        req.download_settings()
        req.get_buddy_walked()
        d = float(delay)
        if self.last_request and time.time() - self.last_request < d:
            time.sleep(d - (time.time() - self.last_request))
        response = req.call()
        self.last_request = time.time()
        return response

    def scout_error(self, error_msg):
        log.error("Scout {} encountered error: {}".format(self.username, error_msg))
        return {
            'success': False,
            'error': error_msg
        }
