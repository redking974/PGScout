PGScout is a webservice that takes coordinates and encounter ID of a Pokémon in Pokémon GO and returns their stats like individual values, CP and level.

As a bonus feature PGScout also **pulls the moveset rating A to F from [GamePress](https://pokemongo.gamepress.gg)**. So you will instantly know whether your Pokémon has an optimal moveset for attack and/or defense. See [Vaporeon on GamePress](https://pokemongo.gamepress.gg/pokemon/134#movesets) for an example of moveset ratings.

# Support PGScout [![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/slop)
If you like PGScout, you use it for a live map or whatever and feel the urgent need to thank me, just drop me a few **level 30+ accounts** or buy me a **PokeHash key**. Seriously, that would be so awesome! :-D You can find me on various Pokémon related Discords as "sLoPPydrive".

# Requirements
PGScout cannot work on itself. You need the following things:
* One or more Pokémon GO accounts (level 25+ for reliable IV stats, level 30+ for reliable CP/level values). See [Reddit discussion](https://www.reddit.com/r/pokemongodev/comments/66m89y/interesting_news_iv_and_moveset_differ_depending/) here.
* A [Bossland PokeHash Key](https://talk.pogodev.org/d/51-api-hashing-service-by-pokefarmer)

# How it works
An incoming web-request to PGScout will create a job that is being put in a queue. All configured accounts will attach to this queue, pull jobs, perform the corresponding encounters and attach the found information back to the job, marking the job as completed. The incoming web-request waits for the job to be completed and returns the result JSON encoded to the requesting client.

# Configuration
Just copy `config.json.sample` to `config.json` and fill in the information:

* `port`: On which port the webservice will listen (default: 4242)
* `hash_key`: Your Bossland PokeHash Key which is needed to perform any Pokémon GO related requests
* `accounts_file`: A file containing PTC or Google accounts for Pokémon GO in [RocketMap](https://github.com/RocketMap/RocketMap) format: `auth-service,username,password`

Don't forget to run `pip install -r requirements.txt` at least once before actually starting PGScout with `python pgscout.py`.

# Requests
PGScout accepts **HTTP GET** requests at `http://<your host>:<port>/iv` and needs these parameters:

* `pokemon_id`: The Pokédex number of the Pokémon
* `encounter_id`: Encounter ID (Base64 encoded) provided by map scanner
* `spawn_point_id`: ID of spawn point provided by map scanner
* `latitude`
* `longitude`

An example **request** looks like this:
```
http://localhost:4242/iv?pokemon_id=70&encounter_id=MTY4MjU4OTY4Njg2MjExOTUwNA%3D%3D&spawn_point_id=47bf32c2c4d&latitude=51.124696678951&longitude=6.89885987319504
```

The **response** is JSON formatted and looks like this:
```javascript
{
  "success": true,
  "encountered_time": 1493285932.471804,
  "gender": 2,
  "height": 0.8362829685211182,
  "weight": 4.311457633972168,
  "iv_percent": 55.55555555555556,
  "iv_attack": 15,
  "iv_defense": 5,
  "iv_stamina": 5,
  "move_1": 271,
  "move_2": 118,
  "rating_attack": "A",
  "rating_defense": "-",
  "cp": 659,
  "level": 17,
  "catch_prob_1": 0.27512598037719727,
  "catch_prob_2": 0.3828456401824951,
  "catch_prob_3": 0.47455763816833496,
  "scout_level": 30
}
```

Most fields of the response should be self-explanatory.
* `encountered_time`: The timestamp when the scout account made the encounter.
* `rating_attack` and `rating_defense`: The moveset rating according to [GamePress](https://pokemongo.gamepress.gg) for attack and defense. If the moveset has no rating the field will contain a dash: "-"
* `level`: The Pokémon level which is being represented by the arc in the Pokémon details in the game. Wild Pokémon will have a level that is limited by the trainer level but not larger than 30, so a trainer with level 17 may find Pokémon from level 1 to 17 but a level 34 trainer may only find Pokémon from level 1 to 30. So 30 is the absolute maximum for wild Pokémon. *(Note that Pokémon being hatched from eggs have an upper limit of level 20.)*
* `catch_prob_1` to `catch_prob_3`: These are the catch probabilities for a regular Pokéball (1), a Great Ball (2) and an Ultra Ball (3). The higher the number the higher the chance to catch the Pokémon with the corresponding ball for a regular hit. Maximum is 1.0 which corresponds to 100% catch probability, so you **will** catch the Pokémon however you hit it.
* `scout_level`: The trainer level of the scout account being used.

# Reliability
PGScout detects your scout account trainer level and therefore knows which values are reliable and sets the others to `null`. Reliable means that the value is the same for all other trainers of the same or higher level.
 
If your trainer level is **below 25**, only `gender`, `height` and `weight` are reliable.

If your trainer level is **at least 25**, the IV values and moves are also reliable.

If your trainer level is **at least 30**, also CP, Pokemon level and catch probabilities are reliable.

# Errors
If PGScout encounters an error, the response will look something like this:
```javascript
{
  "success": false,
  "error": "Pokemon already despawned."
}
```
