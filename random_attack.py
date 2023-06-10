from enum import Enum
from typing import Optional
import random

from sharpy.interfaces import IGatherPointSolver, IZoneManager, IEnemyUnitsManager, IGameAnalyzer
from sharpy.managers.extensions import GameAnalyzer
from sharpy.plans.acts import ActBase
from sharpy.managers.extensions.game_states.advantage import (
    at_least_small_disadvantage,
    at_least_small_advantage,
    at_least_clear_advantage,
    at_least_clear_disadvantage,
)
from sharpy.general.zone import Zone
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

from sharpy.managers.core.roles import UnitTask
from sharpy.combat import MoveType
from sharpy.general.extended_power import ExtendedPower
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sharpy.managers.core import *
    from sharpy.knowledges import Knowledge


ENEMY_TOTAL_POWER_MULTIPLIER = 1.2

RETREAT_TIME = 20

RETREAT_STOP_DISTANCE = 5
RETREAT_STOP_DISTANCE_SQUARED = RETREAT_STOP_DISTANCE * RETREAT_STOP_DISTANCE


class AttackStatus(Enum):
    NotActive = 0
    GatheringForAttack = 1  # Not in use yet
    Attacking = 2
    MovingToExpansion = 3  # NYI, moving to hold enemy expansion
    ProtectingExpansion = 4  # NYI, holding enemy expansion and preventing enemy expansions
    Retreat = 10  # Prefers to escape without fighting
    Withdraw = 11  # Fights any enemies while escaping


class PlanRandomAttack(ActBase):
    gather_point_solver: IGatherPointSolver
    zone_manager: IZoneManager
    enemy_units_manager: IEnemyUnitsManager
    game_analyzer: Optional[IGameAnalyzer]
    pather: "PathingManager"

    DISTANCE_TO_INCLUDE = 18
    DISTANCE2_TO_INCLUDE = 18 * 18
    RETREAT_POWER_PERCENTAGE = 0.8

    move_type = MoveType.Assault
    last_time = 0

    def __init__(self, start_attack_power: float = 20):
        assert isinstance(start_attack_power, float) or isinstance(start_attack_power, int)
        super().__init__()
        self.retreat_multiplier = PlanRandomAttack.RETREAT_POWER_PERCENTAGE
        self.attack_retreat_started: Optional[float] = None

        self.start_attack_power = start_attack_power
        self.attack_on_advantage = True
        self.status = AttackStatus.NotActive
        self.move_type = MoveType.Assault
        


    async def start(self, knowledge: "Knowledge"):
        await super().start(knowledge)
        self.unit_values = knowledge.unit_values
        self.pather = self.knowledge.pathing_manager
        self.game_analyzer = self.knowledge.get_manager(IGameAnalyzer)
        if self.game_analyzer is None:
            self.print(f"IGameAnalyzer not found, turning attack_on_advantage off.")
            self.attack_on_advantage = False
        self.gather_point_solver = knowledge.get_required_manager(IGatherPointSolver)
        self.zone_manager = knowledge.get_required_manager(IZoneManager)
        self.enemy_units_manager = knowledge.get_required_manager(IEnemyUnitsManager)

    async def execute(self) -> bool:
        target = self._get_target()

        if target is None:
            # Enemy known bases destroyed.
            self.status = AttackStatus.NotActive
            return True

        unit: Unit
        if self.status == AttackStatus.Attacking:
            self.handle_attack(target)

        elif self.attack_retreat_started is not None:
            attacking_units = self.roles.attacking_units
            self.roles.refresh_tasks(attacking_units)

            for unit in attacking_units:
                pos: Point2 = unit.position
                at_gather_point = pos.distance_to(self.gather_point_solver.gather_point) < RETREAT_STOP_DISTANCE_SQUARED
                if at_gather_point:
                    # self.print(f"Unit {unit.type_id} {unit.tag} has reached gather point. Stopping retreat.")
                    self.roles.clear_task(unit)
                elif self.status == AttackStatus.Withdraw:
                    self.combat.add_unit(unit)
                else:
                    self.combat.add_unit(unit)

            self.combat.execute(self.gather_point_solver.gather_point, MoveType.DefensiveRetreat)

            if self.attack_retreat_started + RETREAT_TIME < self.ai.time:
                # Stop retreat next turn
                self._stop_retreat()
        else:
            self.roles.attack_ended()
            attackers = Units([], self.ai)
            for unit in self.roles.free_units:
                if self.unit_values.should_attack(unit):
                    attackers.append(unit)

            own_power = self.unit_values.calc_total_power(attackers)

            if self._should_attack(own_power):
                self._start_attack(own_power, attackers)

        return False  # Blocks!

    async def debug_actions(self):
        if self.status == AttackStatus.NotActive:
            return

        if self.status == AttackStatus.Retreat:
            attacking_status = moving_status = "retreating"
        elif self.status == AttackStatus.Withdraw:
            attacking_status = moving_status = "withdrawing"
        elif self.status == AttackStatus.Attacking:
            moving_status = "moving"
            attacking_status = "attacking"
        elif self.status == AttackStatus.ProtectingExpansion:
            moving_status = "moving"
            attacking_status = "preventing"
        else:
            attacking_status = moving_status = "unknown attack task"

        for unit in self.roles.units(UnitTask.Moving):
            self.client.debug_text_world(moving_status, unit.position3d)
        for unit in self.roles.units(UnitTask.Attacking):
            self.client.debug_text_world(attacking_status, unit.position3d)


    def handle_attack(self, target):
        already_attacking: Units = self.roles.units(UnitTask.Attacking)
        if not already_attacking.exists:
            self.print("No attacking units, starting retreat")
            # All attacking units have been destroyed.
            self._start_retreat(AttackStatus.Retreat)
            return True

        center = already_attacking.center
        front_runner = already_attacking.closest_to(target)

        for unit in already_attacking:
            # Only units in group are included to current combat force
            self.combat.add_unit(unit)

        self.roles.refresh_tasks(already_attacking)

        for unit in self.roles.free_units:
            if self.unit_values.should_attack(unit):
                if not self.roles.is_in_role(UnitTask.Attacking, unit) and (
                    unit.distance_to(center) > 20 or unit.distance_to(front_runner) > 20
                ):
                    self.roles.set_task(UnitTask.Moving, unit)
                    # Unit should start moving to target position.
                    self.combat.add_unit(unit)
                else:
                    self.roles.set_task(UnitTask.Attacking, unit)
                    already_attacking.append(unit)
                    # Unit should start moving to target position.
                    self.combat.add_unit(unit)

        # Execute
        self.combat.execute(target, self.move_type)


        retreat = self._should_retreat(front_runner.position, already_attacking)

        if retreat != AttackStatus.NotActive:
            self._start_retreat(retreat)

    def _should_attack(self, power: ExtendedPower, fight_center) -> bool:
        #wait_time = random.triangular(5, 45, 30)
        #if (self.last_time + wait_time > self.ai.time):
        #    return True
        #self.last_time = self.ai.time 
        local_enemy_power = self.get_enemy_local_power(fight_center)

        #result = self.knowledge.tf_manager.random_should_attack(self, power, local_enemy_power)
   
        result =  self.knowledge.tf_manager.tf_should_attack(self, power, local_enemy_power)
    
        if (result == 0):
            return False
        if (result == 2):
            self.print("Predict SearchAndDestroy")
            self.move_type = MoveType.SearchAndDestroy
        else:
            self.move_type = MoveType.Assault
            self.print("Predict Assault")
        return True


    def _start_attack(self, power: ExtendedPower, attackers: Units):
        self.roles.set_tasks(UnitTask.Attacking, attackers)
        self.status = AttackStatus.Attacking
        self.print(f"Attack started at {power.power:.2f} power.")

    def _should_retreat(self, fight_center: Point2, already_attacking: Units) -> AttackStatus:
        own_power = self.unit_values.calc_total_power(already_attacking)
        local_enemy_power = self.get_enemy_local_power(fight_center)
        #wait_time = random.triangular(5, 45, 30)
        #if (self.last_time + wait_time > self.ai.time):
        #    return AttackStatus.NotActive
        
        #result = self.knowledge.tf_manager.random_should_attack(self, own_power, local_enemy_power)
        result =  self.knowledge.tf_manager.tf_should_attack(self, own_power, local_enemy_power)
        self.last_time = self.ai.time
        if (result == 0):
            self.knowledge.print("Predict Retreat")
            return AttackStatus.Retreat
        return AttackStatus.NotActive
    
    def get_enemy_local_power(self,point):
        enemy_local_units: Units = self.ai.all_enemy_units.closer_than(PlanRandomAttack.DISTANCE_TO_INCLUDE, point)

        if self.unit_values.enemy_worker_type is not None:
            enemy_local_units = enemy_local_units.exclude_type(self.unit_values.enemy_worker_type)
        enemy_local_power = self.unit_values.calc_total_power(enemy_local_units)
        return enemy_local_power
    

        enemy_local_units: Units = self.ai.all_enemy_units.closer_than(PlanRandomAttack.DISTANCE_TO_INCLUDE, fight_center)

        if self.unit_values.enemy_worker_type is not None:
            enemy_local_units = enemy_local_units.exclude_type(self.unit_values.enemy_worker_type)

        own_local_power = self.unit_values.calc_total_power(already_attacking)
        enemy_local_power = self.unit_values.calc_total_power(enemy_local_units)

        if self.attack_on_advantage and enemy_local_power.power < 2:
            if (
                self.game_analyzer.our_army_predict in at_least_clear_advantage
                and self.game_analyzer.our_income_advantage in at_least_small_disadvantage
            ) or (
                self.game_analyzer.our_army_predict in at_least_small_advantage
                and self.game_analyzer.our_income_advantage in at_least_clear_disadvantage
            ):
                # Our army is bigger but economy is weaker, attack!
                return AttackStatus.NotActive

            # if ((self.game_analyzer.our_army_predict in at_least_small_disadvantage
            #      and self.game_analyzer.our_income_advantage in at_least_clear_advantage)
            #         or (self.game_analyzer.our_army_predict in at_least_clear_disadvantage
            #             and self.game_analyzer.our_income_advantage in at_least_small_advantage)):
            #     # Our army is smaller but economy is better, focus on defence!
            #     self.print(f'Retreat started because of army {self.game_analyzer.our_army_predict.name}.'
            #                f' {own_local_power.power:.2f} own local power '
            #                f'against {enemy_local_power.power:.2f} enemy local power.')
            #     return AttackStatus.Withdraw

        if enemy_local_power.is_enough_for(own_local_power, self.retreat_multiplier):
            # Start retreat next turn
            self.print(
                f"Retreat started at {own_local_power.power:.2f} own local power "
                f"against {enemy_local_power.power:.2f} enemy local power."
            )
            return AttackStatus.Retreat

        return AttackStatus.NotActive

    def _start_retreat(self, status: AttackStatus):
        self.status = status
        self.attack_retreat_started = self.ai.time

    def _stop_retreat(self):
        self.status = AttackStatus.NotActive
        self.attack_retreat_started = None
        self.roles.attack_ended()
        self.print("Retreat stopped.")

    def _get_target(self) -> Optional[Point2]:
        our_main = self.zone_manager.expansion_zones[0].center_location
        proxy_buildings = self.ai.enemy_structures.closer_than(70, our_main)

        if proxy_buildings.exists:
            return proxy_buildings.closest_to(our_main).position

        # Select expansion to attack.
        # Enemy main zone should the last element in expansion_zones.
        enemy_zones = list(filter(lambda z: z.is_enemys, self.zone_manager.expansion_zones))

        best_zone = None
        best_score = 100000
        start_position = self.gather_point_solver.gather_point
        if self.roles.attacking_units:
            start_position = self.roles.attacking_units.center

        for zone in enemy_zones:  # type: Zone
            not_like_points = zone.center_location.distance_to(start_position)
            not_like_points += zone.enemy_static_power.power * 5
            if not_like_points < best_score:
                best_zone = zone
                best_score = not_like_points

        if best_zone is not None:
            return best_zone.center_location

        if self.ai.enemy_structures.exists:
            return self.ai.enemy_structures.closest_to(our_main).position

        return None
