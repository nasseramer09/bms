#Written by Rikard Ed 2024-01-30

#charging_simulation.py
#Använd simuleringen av en laddstation för en EV som är kopplat till ett hushåll. Den simulerade laddstationen finns som ett skript i Python och startar en webserver som svarar på anrop via JSON-protokollet. Skriv en applikation (i valfritt programmeringsspråk) som hämtar och sänder följande data.
#1.	Hämta information om vilken effekt laddstationen klarar av
#2.	Hämta information om hushållets förbrukning
#3.	Skicka kommando för att starta och stoppa laddningen av EVs batteri. Laddningen skall starta när elpriset är som lägst och hushållets förbrukning inte överstiger 11 kW (trefas-16A) 3.6 kW (enfas 16A) 7.3 kW (enfas 32A) 6.9 kW (trefas 10 A)
#4.	Avläs batteriets kapacitet och ladda batteriet från 20% till 80%
#5. Skapa ett GUI eller använd ett terminalfönster(kommandoprompt) för att kommunicera med den simulerade 

#1 Charging profile without energy price
#2 charging profile with energy price
import json,time
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

#Energy_price in Öre per kWh incl VAT
energy_price=[85.28,70.86,68.01,67.95,68.01,85.04,87.86,100.26,118.45,116.61,105.93,91.95,90.51,90.34,90.80,88.85,90.39,99.03,87.11,82.9,80.45,76.48,32.00,34.29]

#Residential building
max_power_residential_building=11  # (11 kW = 16A 3 phase)
base_load_residential_percent=[0.08,0.07,0.20,0.18,0.25,0.35,0.41,0.34,0.35,0.40,0.43,0.56,0.42,0.34,0.32,0.33,0.53,1.00,0.81,0.55,0.39,0.24,0.17,0.09]
base_load_residential_kwh=[value * max_power_residential_building for value in base_load_residential_percent]
base_load_residential_kwh = [round(x, 2) for x in base_load_residential_kwh]
#base_load_residential_kWh=[1.6,1.494,1.332,1.275,1.372,1.408,1.588,2.18,2.142,2.73,1.439,1.416,1.14,1.18,1.651,1.968,2.08,1.87,2.77,3.157,2.365,2.854,2.911,1.942]
base_current_load=base_load_residential_kwh[0]

#Battery (Citroen e_Berlingo M)
ev_batt_nominal_capacity=50 # kWh
ev_batt_max_capacity=46.3   # kWh
ev_batt_capacity_percent=20 #
ev_batt_capacity_kWh=ev_batt_capacity_percent/100*ev_batt_max_capacity
ev_batt_energy_consumption=226 #kWh per km = 2260 per swedish mil
#ev_battery_charge_start_stopp=False
ev_battery_charge_start_stopp=False

#Charging station
charging_station_info= {"Power":"7.4"} #EV version 2 charger
charging_power=7.4 # kW pchmax from car manufacturer

#time
sim_hour=0
sim_min=0
seconds_per_hour=4

# define a lock to synchronize access to the global variable
global_lock = threading.Lock()

app = Flask(__name__)
CORS(app)

def main_prg():
    global sim_hour
    global sim_min
    global ev_battery_charge_start_stopp
    global ev_batt_capacity_percent
    global ev_batt_capacity_kWh
    global ev_batt_max_capacity
    global base_current_load
    global seconds_per_hour
    while True:
        base_current_load=base_load_residential_kwh[sim_hour]
        for i in range(0,seconds_per_hour):
            if ev_battery_charge_start_stopp:
                if ev_batt_capacity_percent <110.0:
                    ev_batt_capacity_kWh=ev_batt_capacity_kWh+charging_power/seconds_per_hour
                    ev_batt_capacity_kWh=round(ev_batt_capacity_kWh,2)
                    base_current_load=round(base_current_load+charging_power/seconds_per_hour,2)
                    ev_batt_capacity_percent=round(ev_batt_capacity_kWh/ev_batt_max_capacity*100,2)
            sim_min=int(round((60/seconds_per_hour*i)%60,0))
            time.sleep(1)
        sim_hour=(sim_hour+1)%24
        sim_min=0

#left as a default route    
@app.route('/')
def home():
    global ev_batt_capacity_kWh
    #time.sleep(1)  # wait for 1 second before responding
    #ev_battery_charge_per_cent=ev_battery_charge_per_cent+1
    #if request.method == 'GET':
    return (json.dumps(ev_batt_capacity_kWh))
    #else:
    #    return jsonify({'error': 'Unsupported HTTP method'})

@app.route('/info', methods=['GET'])
def station_info():
    global base_current_load
    if request.method == 'GET':
        charging_station_info={ "sim_time_hour":sim_hour,\
                                "sim_time_min":sim_min, \
                                "base_current_load":base_current_load, \
                                "battery_capacity_kWh":ev_batt_capacity_kWh, \
                                "ev_battery_charge_start_stopp":ev_battery_charge_start_stopp
                              }
        return (json.dumps(charging_station_info),{"Access-Control-Allow-orogin":"*"})
    else:
        return jsonify({'error': 'Unsupported HTTP method'})

#deliver base load, starting at 00, 01, 02 a´clock
@app.route('/baseload', methods=['GET'])
def base_load_info():
    if request.method == 'GET':
        return (json.dumps(base_load_residential_kwh))
    else:
        return jsonify({'error': 'Unsupported HTTP method'})

#deliver price per hour, starting at 00-01 a´clock, 01-02 a´clock, 02-03 ...
@app.route('/priceperhour', methods=['GET'])
def price_per_hour_info():
    if request.method == 'GET':
        return (json.dumps(energy_price))
    else:
        return jsonify({'error': 'Unsupported HTTP method'})

@app.route('/charge', methods=['POST', 'GET'])
def charge_battery():
    global ev_battery_charge_start_stopp
    if request.method == 'POST':
        try:
            json_input = request.json
            # result = simulate_charging(json_input)
            # return jsonify(result)
            try:
                start_charg = json_input.get('charging', 0)
                #start_charg = json_input["charging"]
            except json.JSONDecodeError:
                return json.dumps({'error': 'Invalid JSON input'})
            with global_lock:
                if start_charg=="on":
                    ev_battery_charge_start_stopp=True
                    output_data = {'charging': 'on'}
                    return json.dumps(output_data)
                if start_charg=="off":
                    ev_battery_charge_start_stopp=False
                    output_data = {'charging': 'off'}
                    return json.dumps(output_data)

        except Exception as e:
            return jsonify({'error': str(e)})
    elif request.method == 'GET':
        return jsonify(ev_batt_capacity_percent)
        #return jsonify({'message': 'This is a GET request. Use POST to charge the battery.'})
    else:
        return jsonify({'error': 'Unsupported HTTP method'})

@app.route('/discharge', methods=['POST', 'GET'])
def discharge_battery():
    global ev_battery_charge_start_stopp
    global base_current_load
    global base_load_residential_kwh
    global ev_batt_nominal_capacity
    global ev_batt_max_capacity
    global ev_batt_capacity_percent
    global ev_batt_capacity_kWh
    global sim_hour
    global sim_min

    if request.method == 'POST':
        try:
            json_input = request.json
            # result = simulate_charging(json_input)
            # return jsonify(result)
            try:
                discharg = json_input.get('discharging', 0)
                #start_charg = json_input["discharging"]
            except json.JSONDecodeError:
                return json.dumps({'error': 'Invalid JSON input'})
            with global_lock:
                if discharg=="on":
                    ev_battery_charge_start_stopp=False
                    base_current_load=base_load_residential_kwh[0]
                    #Battery (Citroen e_Berlingo M)
                    ev_batt_nominal_capacity=50 # kWh
                    ev_batt_max_capacity=46.3   # kWh
                    ev_batt_capacity_percent=20 #
                    ev_batt_capacity_kWh=ev_batt_capacity_percent/100*ev_batt_max_capacity
                    sim_hour=0
                    sim_min=0
                    output_data = {'discharging': 'on' }
                    return json.dumps(output_data)
                
        except Exception as e:
            return jsonify({'error': str(e)})
    elif request.method == 'GET':
        #return jsonify(ev_batt_capacity_percent)
        return jsonify({'message': 'This is a GET request. Use POST to reset the battery.'})
    else:
        return jsonify({'error': 'Unsupported HTTP method'})
    
# start the increment_sum thread
increment_sum_thread = threading.Thread(target=main_prg)
increment_sum_thread.start()


if __name__ == '__main__':
    app.run(debug=True)
