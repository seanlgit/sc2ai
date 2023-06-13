
import random
import numpy as np

import tensorflow as tf
from typing import Callable, Optional, Coroutine
from sc2.units import Units
from sc2.data import Race
from sharpy.managers.core.manager_base import ManagerBase
from sharpy.general.extended_power import siege


class TFManager(ManagerBase):

    interpreter = None
    input_details = None
    output_details = None
    decisions = []

    def __init__(self) -> None:
        print("init tfmagagers")
        super().__init__()
        self.setup_tflite_model()
        #self.predic_model = Model()
        #self.predic_model.load_weights('trained_model_weights')
        #self._update_func = update_func
        #self._post_update_func = post_update_func

    async def start(self, knowledge: "Knowledge"):
        await super().start(knowledge)

    async def update(self):
        #await self._update_func()
        pass

    async def post_update(self):
        #if self._post_update_func is not None:
        #    self._post_update_func()
        pass

    def setup_tflite_model(self): 
        self.interpreter = tf.lite.Interpreter(model_path='trained_tf_model.tflite')
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def endgame(self, result):
        def save_data(decisions):
            with open('training_data.txt', 'a') as file:
                line = ' '.join([str(decision) for decision in decisions]) + '\n'
                file.write(line)

        def thin_out_2d_array(arr, max_limit):
            if max_limit >= len(arr):
                return arr
            thin_out_ratio = int(len(arr) // (max_limit/2))
            thinned_array = []
            for i in range(0, len(arr), thin_out_ratio):
                thinned_array.append(arr[i])
            return thinned_array

        trimmed_decisions =  thin_out_2d_array(self.decisions, 100)
        #unsure what the correct action would be, but we don't want to overfit with winning games only
        if result == 0:
            return
            for decision in trimmed_decisions: 
                decisions = [0,1,2,0,1,2]
                decisions.remove(decision[-1])
                decision[-1] = random.choice(decisions)
             
        for decision in trimmed_decisions:
            save_data(decision)

    def get_input_data(self, bot, extended_power, enemy_local_power):
        def shorten(decimal):
            return round(decimal*100)


        time = shorten(bot.ai.time)

        race_map =  {Race.Protoss:1, Race.Terran:2, Race.Zerg:3, Race.Random: 4}
        race = race_map[self.ai.enemy_race]
        income = bot.game_analyzer.our_income_advantage.value
        eep = bot.enemy_units_manager.enemy_total_power
        elp = enemy_local_power
        
        o_detectors = extended_power.detectors
        o_air =  shorten(extended_power.air_power)
        o_ground = shorten(extended_power.ground_power)
        o_power = shorten(extended_power.power)

        e_air =  shorten(eep.air_power)
        e_ground = shorten(eep.ground_power)
        e_melee = shorten(eep.melee_power)
        e_stealth = shorten(eep.stealth_power)
        e_surround = shorten(eep.surround_power)
        e_siege = shorten(eep.siege_power)
        e_power = shorten(eep.power)

        el_air =  shorten(elp.air_power)
        el_ground = shorten(elp.ground_power)
        el_melee = shorten(elp.melee_power)
        el_stealth = shorten(elp.stealth_power)
        el_surround = shorten(elp.surround_power)
        el_siege = shorten(elp.siege_power)
        el_power = shorten(elp.power)

        can_survive = 1 if bot.game_analyzer.army_can_survive else 0
        army_adv = bot.game_analyzer.our_army_advantage.value

        attackers = Units([], self.ai)
        for unit in bot.roles.free_units:
            if self.unit_values.should_attack(unit):
                attackers.append(unit)
        print(len(attackers))        
        our_power = shorten(bot.unit_values.calc_total_power(attackers).power)

        inputs = [race, time, income,
                 o_detectors, o_air, o_ground,
                 e_air, e_ground, e_melee, e_stealth, e_surround, e_siege, 
                 el_air, el_ground, el_melee, el_stealth, el_surround, el_siege, el_power,
                 e_power, o_power, our_power, can_survive, army_adv]
        
        return inputs

    def random_should_attack(self, bot, extended_power, enemy_local_power) -> bool:
        inputs = self.get_input_data(self, bot, extended_power, enemy_local_power)
        prediciton = random.choice([0,1,2])
        
        # Save inputs and resuls
        decision = inputs + [prediciton]
        self.decisions.append(decision)
        #model.save_data(inputs, prediciton)
        return prediciton
    
    def tf_should_attack(self, bot, extended_power, enemy_local_power):
        inputs = self.get_input_data(bot, extended_power, enemy_local_power)
        np_inputs = np.array([inputs], dtype=np.int32)
        self.interpreter.set_tensor(self.input_details[0]['index'], np_inputs)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        prediction = np.argmax(np.array(output_data))

        decision = inputs + [prediction]
        self.decisions.append(decision)

        return decision
    '''
            prediction = self.predic_model.predict([inputs])
        predicted_val = np.argmax(prediction)
        print(f"{predicted_val} with {prediction[0][predicted_val]} confidence")

        decision = inputs + [predicted_val]
        self.decisions.append(decision)
        return predicted_val

    '''

    
 


  
        



        


   