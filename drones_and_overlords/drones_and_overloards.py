import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer, Player
from sc2.constants import *
from sc2.data import race_townhalls
import random

pool_first = random.choice(['True', 'False'])

class drones_and_overlords(sc2.BotAI):

    
    # main loop 
    async def on_step(self, iteration):
        await self.distribute_workers()
        await self.build_drone()
        await self.build_overlord()
        await self.build_pool()
        await self.build_queen()
        await self.queen_inject()
        await self.build_expansion()
        await self.build_gas()
        
    async def build_drone(self):
        bases = len(self.units(HATCHERY)) + len(self.units(LAIR)) + len(self.units(HIVE)) 
        gases = len(self.units(EXTRACTOR))
        workers = len(self.units(DRONE))
        workers_needed = ((16*bases + 3*gases)) - workers
        food_left = self.supply_left
        larva_avail = self.units(LARVA).exists
        can_afford = self.can_afford(DRONE)

        if not (larva_avail and can_afford):
            return

        if food_left == 0 or (food_left == 1 and not self.already_pending(OVERLORD)):
            #print('not enough supply')
            return

        if workers_needed > 0:
            #print('building a drone')
            await self.do(self.units(LARVA).random.train(DRONE))

    async def build_overlord(self):
        food_used = len(self.units)
        food_left = self.supply_left
        larva_avail = self.units(LARVA).exists
        can_afford = self.can_afford(OVERLORD)
        larvae = self.units(LARVA)
        
        if not (larva_avail and can_afford):
            return

        # less than 50 supply, build ol one at a time
        if food_used < 30 and food_left < 2 and \
           not self.already_pending(OVERLORD):
            await self.do(larvae.random.train(OVERLORD))
            return
        
        if food_used >= 30 and (food_left < food_used/10):
            await self.do(larvae.random.train(OVERLORD))
            return

    async def build_pool(self):
        expansions = self.num_bases()
        bases = expansions[0]

        if self.units(SPAWNINGPOOL).exists or self.already_pending(SPAWNINGPOOL):
            return

        if not pool_first and bases < 2:
            return

        if self.can_afford(SPAWNINGPOOL):
            await self.build(SPAWNINGPOOL, near=self.townhalls.first)
            print("Pool")

    async def build_queen(self):
        expansions = self.num_bases()
        bases = expansions[0]
        queens = len(self.units(QUEEN))
        hatch = self.townhalls.random

        if not self.units(SPAWNINGPOOL).ready.exists:
            return

        if self.supply_left < 2 or queens >= bases + 2:
            return

        if self.can_afford(QUEEN) and hatch.noqueue:
            await self.do(hatch.train(QUEEN))

    async def build_expansion(self):
        expansions = self.num_bases()
        bases = expansions[0]
        food_used = len(self.units)

        if bases == 1 and food_used > 16 and \
           not self.already_pending(HATCHERY) and \
           self.can_afford(HATCHERY):
            print("Expanding")
            await self.expand_now()

        if bases > 1 and (food_used > 30*bases) and \
           not self.already_pending(HATCHERY) and \
           self.can_afford(HATCHERY):
            print("Expanding")
            await self.expand_now()

        if bases == 6 and self.minerals > 1000 and \
           food_used > 150:
            print("Expanding")
            await self.expand_now()
            

    async def build_gas(self):
        expansions = self.num_bases()
        bases = expansions[0]
        extractors = self.units(EXTRACTOR).amount
        food_used = len(self.units)
        drone = None
        geyser = None
        
        if (bases == 1 and not self.already_pending(HATCHERY)):
            return
        elif extractors >= bases*2:
            return

        if not self.can_afford(EXTRACTOR) or self.minerals < 85:
            return

        if extractors == 0 and \
           not self.already_pending(EXTRACTOR) and self.can_afford(EXTRACTOR):
            drone = self.workers.random
            geyser = self.state.vespene_geyser.closest_to(drone.position)
            err = await self.do(drone.build(EXTRACTOR, geyser))
            print("gas")
        elif extractors == 0:
            return

        
        # build one for every 25 supply, up to 6
        if not self.already_pending(EXTRACTOR) and \
           extractors >= 1 and extractors <= 6 and extractors < food_used/25:
            drone = self.workers.random
            geyser = self.state.vespene_geyser.closest_to(drone.position)
            err = await self.do(drone.build(EXTRACTOR, geyser))
            print("gas")

    async def queen_inject(self):
        expansions = self.num_bases()
        bases = expansions[0]

        for q in self.units(QUEEN).idle:
            abilities = await self.get_available_abilities(q)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.do(q(EFFECT_INJECTLARVA, self.townhalls.closest_to(q.position)))
        
                
                

    def num_bases(self):
        hatches = len(self.units(HATCHERY))
        lairs   = len(self.units(LAIR))
        hives   = len(self.units(HIVE))
    
        return (hatches+lairs+hives, hatches, lairs, hives)
        

print(pool_first)

run_game(maps.get('RedshiftLE'), [
    Bot(Race.Zerg, drones_and_overlords()),
    Computer(Race.Zerg, Difficulty.Easy)
], realtime=False)


        
