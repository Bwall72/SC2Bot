import os
import random
import time

import numpy as np
import sc2
from sc2.ids.ability_id import *
from sc2.ids.unit_typeid import UnitTypeId
from sc2 import Difficulty, Race, maps, position, run_game
from sc2.constants import *
from sc2.data import race_townhalls
from sc2.player import Bot, Computer, Player

has_ling_speed = False
max_extractors = 6
max_drones = 70
speed = False
bot_start = 0

class bot(sc2.BotAI):

    global bot_start
    
    def __init__(self):
        self.pool_first = random.choice(['True', 'False'])
        
    async def on_step(self, iteration):
        # set parameters
        if iteration == 0:
            self.scouts = [self.units(OVERLORD).first]
        self.bases = self.get_bases()
        await self.distribute_workers()
        # build structures
        await self.build_expansion()
        await self.build_pool()
        if iteration % 30 == 0:
            await self.build_extractor()
            await self.build_roach_warren()
            await self.build_lair()
            await self.build_hydraden()
        # build units
        await self.build_overlord()
        if self.supply_left != 0:
            await self.build_drone()
            await self.build_queen()
            await self.build_safety_lings()
            await self.build_roaches()
            await self.build_hydralisks()
        # skills and upgrades
        await self.queen_inject()
        await self.ling_speed()
        await self.hydraden_upgrades()
        # actions
        if iteration % 10 == 0:
            await self.scout()
        await self.attack()
        

    async def build_expansion(self):
        food_used = len(self.units)

        if self.bases[0] == 1 and food_used > 16        and \
           not self.already_pending(HATCHERY)      and \
           self.can_afford(HATCHERY):
            await self.expand_now()

        if self.bases[0] > 1 and (food_used > 30*self.bases[0]) and \
           not self.already_pending(HATCHERY)      and \
           self.can_afford(HATCHERY):
            await self.expand_now()

        if self.bases[0] == 6 and self.minerals > 1000  and \
           food_used > 150:
            await self.expand_now()
    
    async def build_pool(self):
        if self.units(SPAWNINGPOOL).exists or self.already_pending(SPAWNINGPOOL):
            return

        if not self.pool_first and bases < 2:
            return

        if self.can_afford(SPAWNINGPOOL):
            await self.build(SPAWNINGPOOL, near=self.townhalls.first)

    async def build_extractor(self):
        extractors = len(self.units(EXTRACTOR))
        food_used  = len(self.units)
        drone      = None
        geysers    = self.state.vespene_geyser.closer_than(15.0, self.townhalls.random)
        global max_extractors

        if geysers is None or geysers == []:
            return

        if not self.can_afford(EXTRACTOR) or self.already_pending(EXTRACTOR):
            return
        
        if self.bases[0] == 1 and not self.already_pending(HATCHERY):
            return
        elif extractors >= self.bases[0]*2:
            return

        if not self.can_afford(EXTRACTOR):
            return

        # wait for pool and expansion before the first extractor
        if extractors == 0 and (self.bases[0] == 1 or not self.already_pending(HATCHERY)) and \
           not (self.units(SPAWNINGPOOL).exists or self.already_pending(SPAWNINGPOOL)):
            return

        if extractors == 0:
            geyser = geysers[0]
            drone  = self.select_build_worker(geyser.position)
            if not self.units(EXTRACTOR).closer_than(1.0, geyser).exists:
                await self.do(drone.build(EXTRACTOR, geyser))
            #await self.do(drone.build(EXTRACTOR, target))
        elif extractors < max_extractors and extractors < food_used/30:
            """"
            drone = self.workers.random
            target = self.state.vespene_geyser.closest_to(drone.position)
            await self.do(drone.build(EXTRACTOR, target))
            """
            geyser = geysers[0]
            drone  = self.select_build_worker(geyser.position)
            if not self.units(EXTRACTOR).closer_than(1.0, geyser).exists:
                await self.do(drone.build(EXTRACTOR, geyser))
                
    async def build_lair(self):
        if self.units(LAIR).exists or self.already_pending(LAIR):
            return
        if not self.can_afford(LAIR):
            return
        await self.do(self.townhalls.first.build(LAIR))

    async def build_hydraden(self):
        if not self.units(LAIR).ready.exists or self.units(HYDRALISKDEN).exists or self.already_pending(HYDRALISKDEN):
            return
        if not self.can_afford(HYDRALISKDEN):
            return

        await self.build(HYDRALISKDEN, near=self.townhalls.first)
        

    # build warren den at 3:30 when possible
    async def build_roach_warren(self):
        
        if self.units(ROACHWARREN).exists or self.time < 210:
            return

        if not self.can_afford(ROACHWARREN):
            return

        await self.build(ROACHWARREN, near=self.townhalls.first)
        
            
    async def build_drone(self):
        gases          = len(self.units(EXTRACTOR))
        workers        = len(self.units(DRONE))
        workers_needed = ((16*self.bases[0] + 3*gases)) - workers
        food_left      = self.supply_left
        larva_avail    = self.units(LARVA).ready.exists
        can_afford     = self.minerals > 50

        if not (larva_avail and can_afford and workers < max_drones):
            return

        if food_left == 0 or (food_left == 1 and not self.already_pending(OVERLORD)):
            return

        if workers_needed > 0:
            #print('building a drone')
            await self.do(self.units(LARVA).random.train(DRONE))

    async def build_overlord(self):
        food_used     = len(self.units)
        food_left     = self.supply_left
        larva_avail   = self.units(LARVA).exists
        can_afford    = self.can_afford(OVERLORD)
        larvae        = self.units(LARVA)
        num_overlords = len(self.units(OVERLORD))
        
        if not (larva_avail and can_afford) or num_overlords >= 25:
            return

        # less than 50 supply, build ol one at a time
        if food_used < 30 and food_left < 2 and \
           not self.already_pending(OVERLORD):
            larva = larvae.random
            await self.do(larva.train(OVERLORD))
            return
        
        if food_used >= 30 and (food_left < food_used/10):
            larva = larvae.random
            await self.do(larva.train(OVERLORD))
            return

    async def attack(self):
        lings     = self.units(ZERGLING)
        roaches   = self.units(ROACH)
        hydras    = self.units(HYDRALISK)
        mutas     = self.units(MUTALISK)
        ravagers  = self.units(RAVAGER)
        n_ling    = len(lings)
        n_roach   = len(roaches)
        n_hydra   = len(hydras)
        n_muta    = len(mutas)
        n_ravager = len(ravagers)

        army_units  = lings | roaches | hydras | mutas | ravagers
        army_supply = int(0.5*n_ling) + (2*n_roach) + (2*n_hydra) + \
            (2*n_muta) + (3*n_ravager)

        if self.time < 210:
            return

        if self.time < 300 and army_supply > 45:
            for u in army_units.idle:
                await self.do(u.attack(self.select_target()))

        elif army_supply > 70:
            for u in army_units.idle:
                await self.do(u.attack(self.select_target()))

        

    async def build_queen(self):
        queens = len(self.units(QUEEN))
        hatch = self.townhalls.ready.random

        if not self.units(SPAWNINGPOOL).ready.exists:
            return

        if self.supply_left < 2 or queens >= self.bases[0] + 2:
            return

        if self.can_afford(QUEEN) and hatch.noqueue:
            await self.do(hatch.train(QUEEN))

    # make sure there are always atleast 4 zerglings
    # lings build in pairs of two
    async def build_safety_lings(self):
        num_lings = len(self.units(ZERGLING))
        larvae    = self.units(LARVA)

        if not self.units(SPAWNINGPOOL).ready.exists or num_lings > 4:
            return

        for _ in range(0,2):
            if self.minerals >= 50 and len(larvae) > 0 and self.supply_left > 0:
                await self.do(larvae.random.train(ZERGLING))

    async def build_roaches(self):
        larvae      = self.units(LARVA)
        num_roaches = len(self.units(ROACH))
        
        if not self.units(ROACHWARREN).ready.exists:
            return

        if not self.can_afford(ROACH) or len(larvae) == 0 or self.supply_left < 2:
            return

        if self.time < 300:
            if num_roaches < 10:
                await self.do(larvae.random.train(ROACH))
        elif self.bases[0] < 3:
            if num_roaches < 15:
                await self.do(larvae.random.train(ROACH))
        else:
            await self.do(larvae.random.train(ROACH))
                
    async def build_hydralisks(self):
        larvae = self.units(LARVA)
        num_hydras = len(self.units(HYDRALISK))

        if not self.units(HYDRALISKDEN).ready.exists:
            return
        if not self.can_afford(HYDRALISK) or len(larvae) == 0 or self.supply_left < 2:
            return

        if self.time < 420 and num_hydras < 7:
            await self.do(larvae.random.train(HYDRALISK))
        elif self.bases[0] < 4 and num_hydras < 12:
            await self.do(larvae.random.train(HYDRALISK))
        else:
            await self.do(larvae.random.train(HYDRALISK))
            
    async def queen_inject(self):
        for q in self.units(QUEEN).ready.idle:
            abilities = await self.get_available_abilities(q)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.do(q(EFFECT_INJECTLARVA, self.townhalls.closest_to(q.position)))

    # later add way to remake ling speed if it is canceled
    async def ling_speed(self):
        pool = None
        global has_ling_speed
        
        if has_ling_speed:
            return

        if not self.units(SPAWNINGPOOL).ready.exists:
            return
        
        pool = self.units(SPAWNINGPOOL).ready
        if self.vespene >= 100 and self.minerals >= 100:
            await self.do(pool.first(RESEARCH_ZERGLINGMETABOLICBOOST))
            has_ling_speed = True

    async def hydraden_upgrades(self):
        return
        #hydraden = self.units(HYDRALISKDEN)

    # send overlord to scout enemy
    async def scout(self):
                
    def scout_location(self):
        enemy_start_location = self.enemy_start_locations[0]
        x = enemy_start_location[0]
        y = enemy_start_location[1]

        x += ((random.randrange(-20, 20)) / 100) * x
        y += ((random.randrange(-20, 20)) / 100) * y

        if x < 0:
            x = 0
        elif x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]
    
        if y < 0:
            y = 0
        elif y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]

        return position.Point2(position.Pointlike((x,y)))
        
    def get_bases(self):
        hatches = len(self.units(HATCHERY).ready)
        lairs   = len(self.units(LAIR))
        hives   = len(self.units(HIVE))

        return (hatches+lairs+hives, hatches, lairs, hives)

    def select_target(self):
        if self.known_enemy_structures.exists:
            return random.choice(self.known_enemy_structures).position
        return self.enemy_start_locations[0]




run_game(maps.get('RedshiftLE'), [
    Bot(Race.Zerg, bot()),
    Computer(Race.Zerg, Difficulty.Easy)
], realtime=speed)
