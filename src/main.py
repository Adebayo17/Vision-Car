#!/usr/bin/env python3

import base64
import time
import threading
import os
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import config
import variables
import ultrasonSensor
from ledControl import Led
from PIL import Image
import subprocess
from ultralytics import YOLO
import cv2
import numpy as np

# GPIO Setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
led_front = Led(config.LED_FRONT_PIN)
led_back = Led(config.LED_BACK_PIN)
led_left = Led(config.LED_LEFT_PIN)
led_right = Led(config.LED_RIGHT_PIN)

# Ultrason Instance
ultrasonFront = ultrasonSensor.UltrasonSensor(config.TRIG_FRONT_PIN, config.ECHO_FRONT_PIN)
ultrasonBack = ultrasonSensor.UltrasonSensor(config.TRIG_BACK_PIN, config.ECHO_BACK_PIN)

# MQTT Config
# Fonction pour la publication MQTT
def publish_mqtt(topic, message):
    mqtt_client.publish(topic, message)

# Fonction pour la lecture des messages MQTT
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    variables.messagesReceived[topic] = payload
    print("Message reçu - Topic : {}, Payload : {}".format(topic, payload))
    message_Control()

def message_Control():
    print(variables.messagesReceived)
    if variables.messagesReceived[variables.topicsSubscribed[0]] == variables.modes[0]:  # mode manuel
        direction = variables.messagesReceived[variables.topicsSubscribed[1]]

        if direction == "front":
            led_front.on()
            led_back.off()
            led_left.off()
            led_right.off()
        elif direction == "back":
            led_front.off()
            led_back.on()
            led_left.off()
            led_right.off()
        elif direction == "left":
            led_front.off()
            led_back.off()
            led_left.on()
            led_right.off()
        elif direction == "right":
            led_front.off()
            led_back.off()
            led_left.off()
            led_right.on()
        else:
            led_front.off()
            led_back.off()
            led_left.off()
            led_right.off()

    elif variables.messagesReceived[variables.topicsSubscribed[1]] == variables.modes[1]:  # mode automatique
        distance_avant = ultrasonFront.measure_distance()
        publish_mqtt(variables.topicsPublished[5], "front")

        if distance_avant > 20:
            publish_mqtt(variables.topicsPublished[5], "front")
            led_front.on()
            led_back.off()
            led_left.off()
            led_right.off()
        else:
            publish_mqtt(variables.topicsPublished[5], "stop")
            led_front.off()
            led_back.off()
            led_left.off()
            led_right.off()



# Initialisation du client MQTT
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

# Connexion au broker MQTT
mqtt_client.connect(variables.HOST, variables.PORT)
mqtt_client.loop_start()

# Souscription aux topics MQTT
for topic in variables.topicsSubscribed:
    mqtt_client.subscribe(topic)

# Fonction pour la récupération des mesures des capteurs
def get_sensor_measurements():
    while True:
        mqtt_client.loop_start()
        distance_avant = ultrasonFront.measure_distance()
        distance_arrière = ultrasonBack.measure_distance()
        vitesse_avant = ultrasonFront.measure_speed()
        vitesse_arrière = ultrasonBack.measure_speed()

        publish_mqtt(variables.topicsPublished[0], str("{:.2f}".format(distance_avant)))
        publish_mqtt(variables.topicsPublished[1], str("{:.2f}".format(vitesse_avant)))
        publish_mqtt(variables.topicsPublished[2], str("{:.2f}".format(distance_arrière)))
        publish_mqtt(variables.topicsPublished[3], str("{:.2f}".format(vitesse_arrière)))
        print("Mesurements taken")
        time.sleep(0.5)


# Fonction pour la capture d'image et la détection d'objets et envoi via MQTT
def capture_and_predict():
    dossier = "images"
    # Vérifier si le dossier existe
    if not os.path.exists(dossier):
        # Créer le dossier
        os.system("mkdir {}".format(dossier))
        print("Dossier créé :", dossier)
    else:
        print("Le dossier", dossier, "existe déjà.")
    while True:
        mqtt_client.loop_start()
        os.system("libcamera-jpeg -o images/img_camera.jpg -t 1 --width 640 --height 480")
        model = YOLO("yolov8n.pt")
        os.system("rm -rf images/img_result")
        results = model.predict(source="images/img_camera.jpg", save=True, project="images/", name="img_result")
        img = Image.open("images/img_result/img_camera.jpg")
        img_array = np.array(img)
        img_data = cv2.imencode(".jpg", img_array)[1]
        image_base64 = base64.b64encode(img_data).decode('utf-8')
        publish_mqtt(variables.topicsPublished[4], image_base64)
        print("Prédictions envoyées via MQTT.")



# Fonction pour exécuter Node-RED
def start_node_red():
    subprocess.run(["node-red"])

# Fonction pour le séquencage de clignotement des LEDs
def blink_leds_sequence():
    led_front.off()
    led_back.off()
    led_left.off()
    led_right.off()

    for _ in range(10):
        led_front.toggle()
        led_back.toggle()
        led_left.toggle()
        led_right.toggle()
        time.sleep(0.5)

    led_front.off()
    led_back.off()
    led_left.off()
    led_right.off()

# Création des threads pour l'exécution parallèle
capture_thread = threading.Thread(target=capture_and_predict)
sensor_thread = threading.Thread(target=get_sensor_measurements)
node_red_thread = threading.Thread(target=start_node_red)
blink_thread = threading.Thread(target=blink_leds_sequence)


# Démarrage des threads
capture_thread.start()
sensor_thread.start()
node_red_thread.start()
blink_thread.start()

# Attendre que le séquencage de clignotement des LEDs soit terminé avant de continuer
blink_thread.join()

