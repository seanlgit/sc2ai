from typing import Dict

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
#from sc2pathlib import MapType
from sharpy.general.extended_power import siege
from sharpy.combat import Action, MoveType, GenericMicro, CombatModel
from sc2.position import Point2
from sc2.unit import Unit
from sc2.constants import (UNIT_COLOSSUS)
from sc2.units import Units

high_priority: Dict[UnitTypeId, int] = {
    # Terran
    UnitTypeId.SIEGETANK: 8,
    UnitTypeId.SIEGETANKSIEGED: 10,  # sieged tanks are much higher priority than unsieged
    UnitTypeId.WIDOWMINE: 8,
    UnitTypeId.WIDOWMINEBURROWED: 10,
    UnitTypeId.MULE: 3,
    UnitTypeId.SCV: 10,  # prioritize scv because they'll continue repairing otherwise
    UnitTypeId.GHOST: 7,
    UnitTypeId.REAPER: 4,
    UnitTypeId.MARAUDER: 4,
    UnitTypeId.MARINE: 3,
    UnitTypeId.CYCLONE: 5,
    UnitTypeId.HELLION: 2,
    UnitTypeId.HELLIONTANK: 3,
    UnitTypeId.THOR: 7,
    UnitTypeId.MEDIVAC: 6,
    UnitTypeId.VIKINGFIGHTER: 5,
    UnitTypeId.VIKINGASSAULT: 5,
    UnitTypeId.LIBERATORAG: 9,
    UnitTypeId.LIBERATOR: 5,
    UnitTypeId.RAVEN: 10,
    UnitTypeId.BATTLECRUISER: 8,
    UnitTypeId.MISSILETURRET: 1,
    UnitTypeId.BUNKER: 2,
    UnitTypeId.BANSHEE: 5,
    # Zerg
    UnitTypeId.DRONE: 4,
    UnitTypeId.ZERGLING: 3,
    UnitTypeId.BANELING: 6,
    UnitTypeId.BANELINGCOCOON: 6,
    UnitTypeId.ULTRALISK: 6,
    UnitTypeId.QUEEN: 5,
    UnitTypeId.ROACH: 6,
    UnitTypeId.RAVAGER: 8,
    UnitTypeId.RAVAGERCOCOON: 8,
    UnitTypeId.HYDRALISK: 7,
    UnitTypeId.HYDRALISKBURROWED: 7,
    UnitTypeId.LURKERMP: 9,
    UnitTypeId.LURKERMPEGG: 9,
    UnitTypeId.LURKERMPBURROWED: 9,
    UnitTypeId.INFESTOR: 10,
    UnitTypeId.BROODLORD: 10,
    UnitTypeId.BROODLORDCOCOON: 10,
    UnitTypeId.MUTALISK: 6,
    UnitTypeId.CORRUPTOR: 8,
    UnitTypeId.INFESTEDTERRAN: 1,
    UnitTypeId.LARVA: -1,
    UnitTypeId.EGG: -1,
    UnitTypeId.LOCUSTMP: -1,
    # Protoss
    UnitTypeId.SENTRY: 8,
    UnitTypeId.PROBE: 4,
    UnitTypeId.HIGHTEMPLAR: 10,
    UnitTypeId.DARKTEMPLAR: 9,
    UnitTypeId.ADEPT: 4,
    UnitTypeId.ZEALOT: 4,
    UnitTypeId.STALKER: 5,
    UnitTypeId.IMMORTAL: 9,
    UnitTypeId.COLOSSUS: 10,
    UnitTypeId.ARCHON: 6,
    UnitTypeId.SHIELDBATTERY: 1,
    UnitTypeId.PHOTONCANNON: 1,
    UnitTypeId.PYLON: 2,
    UnitTypeId.FLEETBEACON: 3,
    UnitTypeId.WARPPRISM: 8,
    UnitTypeId.DISRUPTOR: 7,
    UnitTypeId.VOIDRAY: 6,
    UnitTypeId.TEMPEST: 6,
}

#it ignores unlisted units? or seems to prio attacking the  target over being in safetyy..
class MicroStalkers(GenericMicro):
    def __init__(self):
        super().__init__()
        self.prio_dict = high_priority

    def range_over_unit(self, unit, enemies, BUFFER = 0):
        ranges = []
        for e in enemies:
            if e.can_attack_ground and not unit.is_flying:
                e_attack_range = e.ground_range
            elif e.can_attack_air and (unit.is_flying or unit.type_id == UNIT_COLOSSUS):
                e_attack_range = e.air_range
            else:#not counted as an enemy if it can't attack
                continue
            if(e_attack_range == 0):
                continue
            
            total_range = unit.radius + e.radius + e_attack_range + BUFFER
            rou = ((total_range) - unit.distance_to(e))
            ranges.append((rou,  e))

        ranges.sort(key=lambda entry: entry[0], reverse=True)
        return ranges
    
    def should_retreat(self, unit: Unit) -> bool:
        if unit.shield_max + unit.health_max > 0:
            health_percentage = (unit.shield + unit.health) / (unit.shield_max + unit.health_max)
        else:
            health_percentage = 0

        return health_percentage < 0.3 # low hp or unit can't attack
   
    def lock_on_micro(self, unit):
        cyclones = self.enemies_near_by(UnitTypeId.CYCLONE)
        if cyclones:
            closest_cyclone = cyclones.closest_to(unit)

            backstep: Point2 = closest_cyclone.position.towards(unit.position, 16)
            unit_has_blink = self.cd_manager.is_ready(unit.tag, AbilityId.EFFECT_BLINK_STALKER)
            if (unit_has_blink):
                return Action(backstep, False, AbilityId.EFFECT_BLINK_STALKER)
            else:
                backstep = self.pather.find_weak_influence_ground(backstep, 4)
                return Action(backstep, False)

    def unit_solve_combat(self, unit: Unit, current_command: Action) -> Action:
        BUFFER = 0
        unit_has_blink = self.cd_manager.is_ready(unit.tag, AbilityId.EFFECT_BLINK_STALKER)

        if self.is_locked_on(unit):
            self.lock_on_micro(unit)

        if(self.move_type in [MoveType.Assault, MoveType.SearchAndDestroy, MoveType.Push]):
            BUFFER = 0.1
        if(self.move_type in [MoveType.DefensiveRetreat, MoveType.Harass]):
            BUFFER = 1
        if(self.move_type in [MoveType.PanicRetreat]):
            BUFFER = 3

        if (self.move_type == MoveType.PanicRetreat or self.should_retreat(unit)):
            backstep = self.closest_group.center if self.closest_group else unit.position
            backstep = unit.position.towards(backstep, -3)
            if(unit_has_blink):
                backstep = self.pather.find_weak_influence_ground_blink(backstep, 4)
                return Action(backstep, False, AbilityId.EFFECT_BLINK_STALKER)
            backstep = self.pather.find_weak_influence_ground(backstep, 4)
            return Action(backstep, False)

        nearby_enemies = self.enemies_near_by
        enemies = self.range_over_unit(unit,nearby_enemies,BUFFER)

        if(len(enemies) == 0):
            #print("running super")
            return current_command
        
        #if it's SearchAndDestroy,  move forward instead of checking safety
        if (self.move_type == MoveType.SearchAndDestroy):
            if (unit.weapon_ready):
                return current_command
            if (not unit_has_blink):
                return Action(current_command.position, False)
            else: #look for a good area to blink in an area towards the target location
                scan_radius = 4
                scan_point = unit.position.towards(current_command.position, scan_radius)
                blink_point = self.pather.find_weak_influence_ground_blink(scan_point, scan_radius)
                return Action(blink_point, False, AbilityId.EFFECT_BLINK_STALKER)
            

        if (enemies[0][0] > 0 and not unit.weapon_ready):
            if(unit_has_blink):
                blink_point = unit.position.towards(enemies[0][1].position,-8)
                return Action(blink_point, False, AbilityId.EFFECT_BLINK_STALKER)

        distances = [(unit.distance_to(e[1]), e[1]) for e in enemies]
        closest_enemy = min(distances, key=lambda x: x[0])
        enemy_aggressive = closest_enemy[1].is_facing(unit, 0.5)

        unit_widths = unit.radius + closest_enemy[1].radius
        closest_enemy_range = closest_enemy[1].ground_range + unit_widths
        unit_range = unit.ground_range + unit_widths
    
        #if able to attack the closest unit, attack
        if(unit.weapon_ready and unit.target_in_range(closest_enemy[1])):
            return self.focus_fire(unit, current_command, self.prio_dict)
            
     

        #if in danger, move away from unit with most range on it
        if (enemies[0][0] >= 0):
            return Action(unit.position.towards(enemies[0][1],-(enemies[0][0]+BUFFER)), False)
        #if not in danger
        if (unit_range < closest_enemy_range and enemy_aggressive):
            return Action(closest_enemy[1].position.towards(unit, closest_enemy_range+BUFFER), False)
        else:
            return Action(closest_enemy[1].position.towards(unit, unit_range), False)
 
            

    def group_solve_combat(self, units: Units, current_command: Action) -> Action:

        if(self.move_type not in [MoveType.Assault, MoveType.SearchAndDestroy]):
            return current_command
        else:
            if(self.move_type == MoveType.Assault):
                blink_threshold = 5
            if(self.move_type == MoveType.SearchAndDestroy):
                blink_threshold = 1

        all_enemies = self.enemies_near_by
        sorted_prio_targets =  sorted(all_enemies, key=lambda x: self.prio_dict.get(x.type_id, 0), reverse=True)
        prio_targets = [t for t in sorted_prio_targets if self.prio_dict.get(t.type_id,0) > blink_threshold]

        if(len(prio_targets) == 0):
            return current_command
        used_stalkers = []
        for target in prio_targets:
            target_hp = target.health  + target.shield
            stalker_dmg = units[0].calculate_damage_vs_target(target)[0]
            #why it's 0 sometimes, idk
            if(stalker_dmg <= 0):
                continue
            number_to_1shot = int((target_hp // stalker_dmg)+2) #2 cuz warpprism pickups, etc 
            stalkers_in_range = [s for s in units.closer_than(15, target) if s not in used_stalkers]
            #opting to not dive in for lower prio units if a bigger prio is still around
            if(number_to_1shot > len(stalkers_in_range)):
                break
                
            #split into stalkers that need to blink to reach or not   
            nonblink_stalkers, blink_stalkers = [], []
            for s in stalkers_in_range:
                if (s.distance_to(target) <= 6):
                    nonblink_stalkers.append(s)  
                elif(self.cd_manager.is_ready(s.tag, AbilityId.EFFECT_BLINK_STALKER)):
                    blink_stalkers.append(s)

            if(number_to_1shot <= len(nonblink_stalkers)):
                for s in nonblink_stalkers[:number_to_1shot]:
                    #s.attack(target)
                    used_stalkers.append(s)
                             
            elif(number_to_1shot <= len(nonblink_stalkers) + len(blink_stalkers)):
                counter  = 0
                for s in nonblink_stalkers:
                    counter += 1
                    used_stalkers.append(s)
                    #s.attack(target)

                #blink_point = self.pather.find_weak_influence_ground_blink(target.position, 6)
                for s in blink_stalkers:
                    if (counter > number_to_1shot):
                        break
                    blink_distance = s.distance_to(target)-8
                    blink_point = s.position.towards(target.position, blink_distance)      
                    counter += 1
                    used_stalkers.append(s)
                    s(AbilityId.EFFECT_BLINK_STALKER, blink_point) 
                        
        if(current_command == None):
            print("returning none command why")
        return current_command
        #print(f"Blink stalkers: {blink_stalkers}")



''''

 def unit_solve_combat_old(self, unit: Unit, current_command: Action) -> Action:
        if self.cd_manager.is_ready(unit.tag, AbilityId.EFFECT_BLINK_STALKER):
            if self.is_locked_on(unit):
                cyclones = self.enemies_near_by(UnitTypeId.CYCLONE)
                if cyclones:
                    closest_cyclone = cyclones.closest_to(unit)
                    backstep: Point2 = closest_cyclone.position.towards(unit.position, 15)
                    backstep = self.pather.find_weak_influence_ground(backstep, 4)

                    return Action(backstep, False, AbilityId.EFFECT_BLINK_STALKER)

            if self.model == CombatModel.StalkerToSiege and (
                self.move_type == MoveType.Assault or self.move_type == MoveType.SearchAndDestroy
            ):
                siege_units = self.enemies_near_by.of_type(siege)
                if siege_units:
                    target = siege_units.closest_to(unit)
                    if target.distance_to(unit) > 6:
                        return Action(target.position, False, AbilityId.EFFECT_BLINK_STALKER)

            if unit.shield_percentage < 0.05:
                # Blink to safety.

                target_pos = unit.position
                if self.closest_group:
                    target_pos = target_pos.towards(self.closest_group.center, -3)

                target = self.pather.find_weak_influence_ground_blink(target_pos, 6)
                if target.distance_to(unit) > 3:
                    backstep_influence = self.pather.map.current_influence(MapType.Ground, target)
                    current_influence = self.pather.map.current_influence(MapType.Ground, unit.position)
                    if backstep_influence < current_influence:
                        return Action(target, False, AbilityId.EFFECT_BLINK_STALKER)

        return super().unit_solve_combat(unit, current_command)

find_weak_influence_ground_blink(self, target: Point2, radius: float) -> Point2:


async def stalker_kiting(BotAI, loc):
    BUFFER = 0.5

    #get a list of targets that we should blink on
    prio_target_list = [UnitTypeId.SENTRY, UnitTypeId.STALKER, 
                        UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED, UnitTypeId.LIBERATOR, UnitTypeId.MEDIVAC, 
                        UnitTypeId.RAVAGER, UnitTypeId.LURKER]
    targets = BotAI.all_enemy_units
    all_prio_targets = [t for t in targets if t.type_id in prio_target_list]
    prio_targets = sorted(all_prio_targets, key =  lambda x: prio_target_list.index(x.type_id))

    if (prio_targets != []):
        for target in prio_targets:
            target_as_Units = Units([target], BotAI)
            all_stalkers = BotAI.units(UnitTypeId.STALKER)
            all_stalkers = set(all_stalkers) - set(BotAI.used_units)
            all_stalkers = Units(all_stalkers, BotAI)

            #break if there aren't enough stalkers to 1shot the target (6weapon+8blink range)
            if(len(all_stalkers) == 0):
                break
 
            target_hp = target.health  + target.shield
            stalker_dmg = all_stalkers[0].calculate_damage_vs_target(target)[0]
            #why it's 0 sometimes, idk
            if(stalker_dmg <= 0):
                break
            number_to_1shot = int((target_hp // stalker_dmg)+2) #2 cuz warpprism pickups, etc
            stalkers_in_range = all_stalkers.closer_than(14, target) 
            if(number_to_1shot > len(stalkers_in_range)):
                break

            #split into stalkers that need to blink to reach or not   
            nonblink_stalkers, blink_stalkers = [], []
            all_blink_stalkers = set(await get_blink_stalkers(BotAI,stalkers_in_range))
            for s in stalkers_in_range:
                if (s.distance_to(target) <= 6):
                    nonblink_stalkers.append(s)  
                elif(s in all_blink_stalkers):
                    blink_stalkers.append(s)


            if(number_to_1shot <= len(nonblink_stalkers)):
                for s in nonblink_stalkers:
                    s.attack(target)
                    BotAI.used_units.append(s)
                    
            elif(number_to_1shot <= len(nonblink_stalkers) + len(blink_stalkers)):
                counter  = 0
                for s in nonblink_stalkers:
                    BotAI.used_units.append(s)
                    counter += 1

                for s in blink_stalkers:
                    if (counter > number_to_1shot):
                        break
                    blink_distance = s.distance_to(target)-6
                    blink_point = s.position.towards(target.position, blink_distance)
                    s(AbilityId.EFFECT_BLINK_STALKER, blink_point)        
                    BotAI.used_units.append(s)
                    counter += 1
          
    all_enemies = BotAI.enemy_units
    blink_stalkers = await get_blink_stalkers(BotAI)
    for b_stalker in blink_stalkers:
        rou = await range_over_unit(b_stalker, all_enemies)
        if (len(rou) > 0 and rou[0][0] > 0):
            if(not b_stalker.weapon_ready):
                blink_point = b_stalker.position.towards(rou[0][1].position,-8)
                b_stalker(AbilityId.EFFECT_BLINK_STALKER, blink_point)        

    stalkers = BotAI.units(UnitTypeId.STALKER)
    stalkers = set(stalkers) - set(BotAI.used_units)
    stalkers = Units(stalkers, BotAI)
    for s in stalkers:
        healthy = s.shield_health_percentage > 0.7
        if (healthy):
            await ground_kite(BotAI, s, loc, BUFFER)
        else:
            await ground_kite(BotAI, s, BotAI.start_location, BUFFER)
        BotAI.used_units.append(s)     

    return True

    Step(Requirement, Act)
        Act(Callable: ZoneAttack)
            ZoneAttack calls  combat.execute (GroupCombatManager)
                eventually calls DefaultMicroMethods.handle_groups and back to GroupCombatManager.action_to
                this runs group_solve combat
            
        for type_id, type_units in own_unit_cache.items():
            micro: MicroStep = self.unit_micros.get(type_id, self.generic_micro)
            micro.init_group(self.rules, group, type_units, self.enemy_groups, move_type, original_target)
            group_action = micro.group_solve_combat(type_units, Action(target, is_attack))

            for unit in type_units:
                final_action = micro.unit_solve_combat(unit, group_action)
                final_action.to_commmand(unit)

        Sharpy will pass a target and move.type to Group  Solve  combat which passes a comman
        

        group_combat_manager execute() needs to be called. this groups the units up and calls Handle_group_func
        handle_group_func will determine if any changes need to be made, (retreat etc)
        default micro mgr can be rewritten for stalkers, call regroup/attackto/moveto

class MoveType(enum.IntEnum):
    # Look for enemies, even if they are further away.
    SearchAndDestroy = 0
    # Same as attack move
    Assault = 1
    # When attacked from sides, fight back while moving
    Push = 2
    # Shoot while retreating
    DefensiveRetreat = 3
    # Use everything in arsenal to escape the situation
    PanicRetreat = 4
    # Don't fight with buildings and skip enemy army units if possible
    Harass = 5
    # Attempt to regroup with other units.
    ReGroup = 6

    0,1 a-move to target, blink focus attackss
    2,3 a-move to target with more buffer?
    4,5,6 move as fast as possible, no attack

    '''