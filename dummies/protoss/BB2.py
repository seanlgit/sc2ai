from typing import Optional, List

from sc2.data import Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sharpy.combat.group_combat_manager import GroupCombatManager
from sharpy.managers.core import *
from sharpy.managers.core import ActManager, GatherPointSolver
from sharpy.managers.core import EnemyUnitsManager

from sharpy.managers.extensions import GameAnalyzer
from sharpy.managers.extensions import MemoryManager
from sharpy.plans.acts import *
from sharpy.plans.acts.protoss import *
from sharpy.plans.require import *
from sharpy.plans.tactics import *
from sharpy.plans.tactics import *
from sharpy.plans import BuildOrder, Step, SequentialList, StepBuildGas
from sharpy.knowledges import SkeletonBot
from sc2.ids.upgrade_id import UpgradeId





class BB2(SkeletonBot):
    def __init__(self):
        super().__init__("The Sharp Four")

    async def on_start(self):
        """Allows initializing the bot when the game data is available."""
        self.knowledge.pre_start(self, self.configure_managers())
        await self.knowledge.start()
        

    async def on_end(self, game_result):
        """class Result:
        Victory = 1
        Defeat = 2
        Tie = 3
        Undecided = 4"""
        await self.knowledge.on_end(game_result)
        result = 1 if game_result.value == 1 or game_result.value == 3 else 0
        self.knowledge.tf_manager.endgame(result)
    
    def configure_managers(self) -> Optional[List[ManagerBase]]:
        return [
            MemoryManager(),
            PreviousUnitsManager(),
            LostUnitsManager(),
            EnemyUnitsManager(),
            UnitCacheManager(),
            UnitValue(),
            UnitRoleManager(),
            PathingManager(),
            ZoneManager(),
            BuildingSolver(),
            IncomeCalculator(),
            CooldownManager(),
            GroupCombatManager(),
            GatherPointSolver(),
            GameAnalyzer(),
            ActManager(self.create_plan()),
            TFManager(),
        ]

    def create_plan(self) -> BuildOrder:
        #attack = PlanZoneAttack(6)
        attack = PlanRandomAttack(6)
        attack.attack_on_advantage = False  # Disables requirement for game analyzer
        return BuildOrder(
            Step(
                None,
                ChronoUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS),
                skip=UnitExists(UnitTypeId.PROBE, 20, include_pending=True),
                skip_until=UnitExists(UnitTypeId.ASSIMILATOR, 1),
            ),
            ChronoTech(AbilityId.RESEARCH_BLINK, UnitTypeId.TWILIGHTCOUNCIL),
            ChronoUnit(UnitTypeId.IMMORTAL, UnitTypeId.ROBOTICSFACILITY),
            ChronoUnit(UnitTypeId.IMMORTAL, UnitTypeId.ROBOTICSFACILITY),
            SequentialList(
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 14),
                GridBuilding(UnitTypeId.PYLON, 1),
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 17),
                GridBuilding(UnitTypeId.GATEWAY, 1),
                Expand(2),
                BuildGas(1),
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 19),
                WorkerScout(),
                BuildOrder(                    
                    SequentialList(
                        Step(None,GridBuilding(UnitTypeId.CYBERNETICSCORE, 1), skip_until=UnitReady(UnitTypeId.GATEWAY, 1)),
                        Step(UnitExists(UnitTypeId.CYBERNETICSCORE, 1, include_pending=True), BuildGas(2)),
                        Step(UnitExists(UnitTypeId.CYBERNETICSCORE, 1, include_pending=True), ProtossUnit(UnitTypeId.ZEALOT, 1, only_once=True)),
                        Step(UnitReady(UnitTypeId.CYBERNETICSCORE, 1), GridBuilding(UnitTypeId.TWILIGHTCOUNCIL, 1)),
                        Tech(UpgradeId.WARPGATERESEARCH),
                        Step(UnitReady(UnitTypeId.TWILIGHTCOUNCIL, 1), Tech(UpgradeId.BLINKTECH)),
                        
                    ),
                    SequentialList(
                        ActUnit(UnitTypeId.IMMORTAL, UnitTypeId.ROBOTICSFACILITY, 1, priority=True),
                        ActUnit(UnitTypeId.WARPPRISM, UnitTypeId.ROBOTICSFACILITY, 1, priority=True),
                        ActUnit(UnitTypeId.IMMORTAL, UnitTypeId.ROBOTICSFACILITY, 2, priority=True),
                        ActUnit(UnitTypeId.OBSERVER, UnitTypeId.ROBOTICSFACILITY, 1, priority=True),
                        ActUnit(UnitTypeId.WARPPRISM, UnitTypeId.ROBOTICSFACILITY, 2, priority=True),
                        ActUnit(UnitTypeId.IMMORTAL, UnitTypeId.ROBOTICSFACILITY, 4, priority=True),
                        ActUnit(UnitTypeId.OBSERVER, UnitTypeId.ROBOTICSFACILITY, 2, priority=True),
                        ActUnit(UnitTypeId.IMMORTAL, UnitTypeId.ROBOTICSFACILITY, 10, priority=True),
                    ),
                    SequentialList(
                        ProtossUnit(UnitTypeId.STALKER, 100, priority=True)
                    ),
                    SequentialList(
                        Step(UnitExists(UnitTypeId.CYBERNETICSCORE, 1, include_pending=True), DefensiveCannons(0,1,1)),
                        Step(UnitExists(UnitTypeId.TWILIGHTCOUNCIL, 1, include_pending=True), GridBuilding(UnitTypeId.GATEWAY, 2)),
                        Step(UnitExists(UnitTypeId.TWILIGHTCOUNCIL, 1, include_pending=True), GridBuilding(UnitTypeId.ROBOTICSFACILITY, 1)),
                        Step(UnitExists(UnitTypeId.ROBOTICSFACILITY, 1, include_pending=True), GridBuilding(UnitTypeId.GATEWAY, 4)),
                        
                        
                        Step(UnitExists(UnitTypeId.GATEWAY, 4), BuildGas(3), skip_until=Minerals(300)),
                        Step(UnitExists(UnitTypeId.GATEWAY, 4), BuildGas(4), skip_until=Minerals(400)),
                        Step(None, GridBuilding(UnitTypeId.FORGE, 1), skip_until=Minerals(400)),
                        Step(UnitExists(UnitTypeId.GATEWAY, 4), DefensiveCannons(1,1), skip_until=Minerals(400)),
                        Step(UnitReady(UnitTypeId.FORGE, 1), Tech(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL1), skip_until=Minerals(500)),
                        Step(UnitReady(UnitTypeId.FORGE, 1), Tech(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL2), skip_until=Minerals(500)),
                        Step(UnitReady(UnitTypeId.FORGE, 1), Tech(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL3), skip_until=Minerals(500)),
                    ),               
                    AutoPylon(),
                    ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 44),
                    
                ),
            ),
            SequentialList(
                MineOpenBlockedBase(),
                RestorePower(),
                DistributeWorkers(),
                Step(None, SpeedMining(), lambda ai: ai.client.game_step > 5),      
                PlanCancelBuilding(),
            ),
            SequentialList(              
                PlanZoneDefense(),                            
                PlanZoneGather(),
                Step(None, attack),
                Step(TechReady(UpgradeId.BLINKTECH, 0.9), attack),
                PlanFinishEnemy(),
            ),
        )


class LadderBot(BB2):
    @property
    def my_race(self):
        return Race.Protoss
