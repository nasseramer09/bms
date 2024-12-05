import time
from threading import Thread
from typing import final

from flask_socketio import SocketIO

import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
socketio = SocketIO(app)
url = "http://127.0.0.1:5000/"
optimized_kwh = 0
optimized_percent = 0
last_capacity_kwh = 0

def fetchData(endpoint):
    try:
        response = requests.get(f"{url}/{endpoint}")
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error fetching {endpoint}, status code: {response.status_code}")
    except Exception as e:
        print(f"error: {e}")
        return{}

def connection_handler():
    ev_batt_max_capacity = 46.3
    while True:
        time.sleep(1)
        try:
            data = fetchData("info")
            if not data:
                continue

                #beräkningen sker har för att den ska inkluderas i socket därmed uppdatera sida och begränsas till 80%
            ev_batt_capacity_percent = min(round(data['battery_capacity_kWh'] / ev_batt_max_capacity * 100, 2), 80)

            socketio.emit('update_time',
                          {'sim_time_hour':data['sim_time_hour'],
                                'sim_time_min':data['sim_time_min'],
                                'base_current_load':data['base_current_load'],
                                'battery_capacity_kWh':data['battery_capacity_kWh'],
                                'ev_batt_capacity_percent':ev_batt_capacity_percent,
                                'charging':data['ev_battery_charge_start_stopp'],
                                'optimized_kwh':optimized_kwh,
                                'optimized_percent':optimized_percent
                                      })
        except Exception as e:
            print(f"error in connection handler: {e}")


def charging_optimizer():
    global last_capacity_kwh
    ev_batt_max_capacity = 46.3

    while True:
        try:
            info = fetchData("info")
            baseload=fetchData("baseload")
            priceData=fetchData("priceperhour")

            if not info or not baseload or not priceData:
                print("data for optimizing the charge is missing, trying agin in 5 seconds ")
                time.sleep(5)
                continue

            current_hour = info['sim_time_hour']
            current_baseLoad= baseload[current_hour]
            battery_capacity_percent = round(info.get('ev_batt_capacity_percent', 0) / ev_batt_max_capacity * 100, 2)
            chargingStatus=info['ev_battery_charge_start_stopp']

#kontrollera om batteriet är över 80%
            if battery_capacity_percent >= 80:
                if chargingStatus:
                    print(f"[{current_hour}:00] Batteriet är {battery_capacity_percent}%, stoppar laddningen")
                    requests.post(f"{url}/charge", json={"charging": "off"})
                    continue


            #hitta lägst förbrukning (när basload är som lägst)
            lowest_consumption_hour=baseload.index(min(baseload))
            isLowestConsumption=current_hour == lowest_consumption_hour
            isLowestPrice = priceData[current_hour] == min(priceData)


            #kollar om vi kan ladda baserat på förbrukning eller låg pris
            canCharge= (current_baseLoad + 7.4 <= 11) and (battery_capacity_percent < 80)

#startar laddningen om kriterierna uppfylls och logga status
            if not chargingStatus and canCharge:
                if isLowestConsumption and not isLowestPrice:
                    print(f"[{current_hour}:00] Batteriets laddning triggas av lägst förbrukning")
                elif isLowestPrice and not isLowestConsumption:
                    print(f"[{current_hour}:00] Batteriets laddning triggas av lägst pris")
                elif isLowestConsumption and isLowestPrice:
                    print(f"[{current_hour}:00] Batteriets laddning triggas av lägst förbrukning och lägst pris")
                requests.post(f"{url}/charge", json={"charging": "on"})
            elif chargingStatus and not (isLowestConsumption and isLowestPrice):
                print(f"[{current_hour}:00]  laddning stoppas, ingen av kriterierna är uppfyllda")
                requests.post(f"{url}/charge", json={"charging": "off"})



        except Exception as e:
            print(f"error while optimizing: {e}")
        finally:
            time.sleep(5)


@app.route('/')
def home_page():

    responses = requests.get(url)
    if responses.status_code == 200:
        data = responses.json()
        return render_template("home.html", data=data)

@app.route('/info')
def info():

        data = fetchData("info")
        baseload=fetchData("baseload")
        total_energy_consumption=sum(baseload)

        #omvandlar laddningen till procent och skickar den till data som sedan skickas till jinja 2
        ev_batt_max_capacity = 46.3
        ev_batt_capacity_percent = min(round(data['battery_capacity_kWh'] / ev_batt_max_capacity * 100, 2), 80)
        data['ev_battery_capacity_percent'] = ev_batt_capacity_percent
        return render_template("info.html",
                               data=data ,
                               total_energy_consumption=total_energy_consumption)

@app.route('/priceperhour')
def priceperhour():
        data = fetchData("priceperhour")
        return render_template("priceperhour.html", data=data)

@app.route('/baseload')
def baseload():
        data = fetchData("baseload")
        return render_template("baseload.html", data=data)

@app.route('/charge', methods=['GET'])
def charge():
        data = fetchData("charge")
        return render_template("evBatteryStatus.html", data=data)

@app.route('/discharge', methods=['POST'])
def discharge():
    try:

        response = requests.post(f"{url}/discharge", json={"discharging": "on"})
        if response.status_code == 200:
            data = fetchData("info") # is going to get current status after discharging (nollställer allt
            return render_template("evBatteryStatus.html", data=data)
        else:
            return {"error": "error while discharging"}, response.status_code
    except Exception as e:
        return {"error while discharging:": {e}},

@app.route('/charging_handle', methods=['POST'])
def charging_handle():
    isCharging = request.json.get('charging')
    info = fetchData("info")
    ev_batt_max_capacity = 46.3
    battery_percent = round(info['battery_capacity_kWh'] / ev_batt_max_capacity * 100, 2)

    # checks battery percent if the battery is full sends this message
    if battery_percent >= 80:
        return {"Battery is sufficiently charged"}, 400


    response = requests.post(f"{url}/charge", json={"charging": isCharging})
    if response.status_code == 200:

        socketio.emit('update_time', {'charging': isCharging})
        return jsonify({"success": True, "charging": isCharging}), 200
    return jsonify({"error: charging failed"}), 500



    responses = requests.post(f"{url}/charge", json={"charging": isCharging})
    if responses.status_code == 200:
        socketio.emit('update_time',{
            'charging': isCharging,
        })
        return responses.json(), 200
    return 'fail to toggle charging', 500


if __name__ == '__main__':
    thread = Thread(target=connection_handler)
    charging_optimizer: thread = Thread(target=charging_optimizer)
    thread.daemon = True
    thread.start()
    charging_optimizer.start()

    socketio.run(app, host='0.0.0.0', port=8080, debug=True)
