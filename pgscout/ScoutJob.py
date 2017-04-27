from pgscout.utils import get_pokemon_name


class ScoutJob(object):
    def __init__(self, pokemon_id, encounter_id, spawn_point_id, lat, lng):
        self.pokemon_id = pokemon_id
        self.pokemon_name = get_pokemon_name(pokemon_id)
        self.encounter_id = encounter_id
        self.spawn_point_id = spawn_point_id
        self.lat = lat
        self.lng = lng
        self.processed = False
        self.result = {}