#/////////////////////////////////--- IOT CASE STUDY ---//////////////////////////////////////////
#// Deze code is geschereven door SEBASTIAAN GANBAATAR, student Thomas More ITF 1_08 10/5/2021  //
#// Dit project is voor de evaluatie voor IoT Essentials - Case study                           //
#// CONTACT --> sebas.ganba@telenet.be ThomasMore R-0855556                                     //
#/////////////////////////////////////////////////////////////////////////////////////////////////

#programma naam:    x_Radio_IO.py
#functionaliteit:   de code bestuurt een internet radio... met 
#///////////////////////////////////////!!! DE LIBRARIES !!!//////////////////////////////////////
import spidev # spi librarie voor nokia en mcp30058
import sys # om subprocess te gebruiken (via python code console commands uitvoeren)
import json # is nodig voor adafruit en voor Ubeac data sturen via http
import requests # voor mqtt
import subprocess # via python code console commands uitvoeren
import busio # spi library
import digitalio # input en output intializeren
import board # GPIO pinnen importeren
import adafruit_pcd8544 # scherm LCD library
import paho.mqtt.client as mqtt #  mqtt om data te krijgen
import paho.mqtt.publish as publish # mqtt om data te zenden
import RPi.GPIO as GPIO # Voor in en outputs aan te sturen
from time import sleep # Voor scherm te printen Nokia 5110
from PIL import Image #     ^
from PIL import ImageDraw # ^
from PIL import ImageFont # ^
from time import sleep # sleep functie (code pauzeren)
from adafruit_bus_device.spi_device import SPIDevice # adafruit om nokia 5110 te laten werken

#//////////////////////////////////////!!! DE VARIABELEN !!!//////////////////////////////////////

#******!!! DE PIN CONFIGURATIE !!!**************************************************************//
ledPin1 = 2 # gpio nummer voor de groene led
ledPin2 = 3 # gpio nummer voor de gele led
ledPin3 = 15 # gpio nummer voor de rode led 
in1 = 17 # gpio nummer voor 'in 1' op de stappenmotor driver module
in2 = 18 # gpio nummer voor 'in 2' op de stappenmotor driver module
in3 = 27 # gpio nummer voor 'in 3' op de stappenmotor driver module 
in4 = 22 # gpio nummer voor 'in 4' op de stappenmotor driver module
cali = 21 # gpio nummer voor de optische calibratie module om het rad te bespturen
#*******!!! VARIABELEN VOOR MQTT !!!***********************************************************//
global vvll # globale variabele om mqtt volume te besturen (slider web interface)
global nnxx # globale variable om mqtt volgende channel te gaan (knop NEXT CHANNEL web interface)
global pprr # globale variable om mqtt vorige channel te gaan (knop PREV CHANNEL web interface)
global mmdd # globale variabele om de mode te bepalen '1' voor WEB '2' voor PI  (web interface)
vvll = "" # de globale variabele anouncen
nnxx = 0 # idem ^^
pprr = 0 # idem ^^
mmdd = 0 # idem ^^
MQTT_TOPIC = [("radioIOT/volume",1),("radioIOT/nextChannel",1),("radioIOT/prevChannel",1),("radioIOT/volumeMode",1)] # alle topics in een list zetten (topic, qoclevel1)
#*******!!! VARIABELEN VOOR MPD !!!************************************************************//
commandVolume = "mpc volume " # de command om de volume aan te passen in mpd mpc (voor sub.process)
volumeInvertHulp = 100 # hulp variabele om de pot meter te inverteren
volume = 0 # de volume regeling voor de MPC
volumeHulp = 0 # helpt bij enkel 'on change' bij volume
nextChannelHulp = 0 # hulp variabele om next channel voor pot meter
prevChannelHulp = 0 # hulp variabele om vorig channel voor pot meter
currentchannel = 8 # variabele om te weten welke channel aan het spelen is
#*******!!! VARIABELEN OM TXT BESTAND IN TE LEZEN !!!******************************************//
hulpListLinks = [] # een hulp variable om alle links te extracten uit 'instellingen.txt'
hulpListNames = [] # een hulp variable om alle stations namen te extracten uit 'instellingen.txt'

#*******!!! VARIABELEN UBEAC DASHBOARD !!!*****************************************************//
url = "https://sebasgnb.hub.ubeac.io/rad10"
#******!!! DE VARIABLELEN VOOR MOTOR CONTROLE !!!**********************************************//
wheelPosition = 0 # om de positie van het rad te weten
number = 0 # Hoeveel nummers op het rad wil je bewegen?
step_sleep = 0.001 # de snelheid van de motor bepalen (snelste 0.001)
step_count = 512 # 5.625*(1/64) per step, 4096 steps is 360° 4096... een nummer op rad is dus 4096 / 8 =512
direction = False # true for clockwise, False for counter-clockwise
motor_pins = [in1,in2,in3,in4] # de motorpinnen onthouden in een list om te besturen
#******!!! DE MOTORSTAPPEN SEQUENTIE INITALIZEREN !!!*******************************************//
#******-->(found in documentation http://www.4tronix.co.uk/arduino/Stepper-Motors.php)**********//
# full step modus:
step_sequence = [[1,0,0,1], 
                 [1,0,0,0], 
                 [1,1,0,0], 
                 [0,1,0,0], 
                 [0,1,1,0], 
                 [0,0,1,0], 
                 [0,0,1,1], 
                 [0,0,0,1]] 
#******!!! DE PINNEN INSTELLEN ALS IN OF OUTPUT !!!*********************************************//
GPIO.setmode(GPIO.BCM)              
GPIO.setup(ledPin1,GPIO.OUT)
GPIO.setup(ledPin2,GPIO.OUT)
GPIO.setup(ledPin3,GPIO.OUT)
GPIO.setup( in1, GPIO.OUT ) 
GPIO.setup( in2, GPIO.OUT ) 
GPIO.setup( in3, GPIO.OUT ) 
GPIO.setup( in4, GPIO.OUT ) 
GPIO.setup(cali,GPIO.IN) 
#******!!! DE MOTOR PINNEN LAAGZETTEN !!!*******************************************************//
GPIO.output( in1, GPIO.LOW ) 
GPIO.output( in2, GPIO.LOW ) 
GPIO.output( in3, GPIO.LOW ) 
GPIO.output( in4, GPIO.LOW ) 
#******!!! DE SPI CONFIGURATIE !!!**************************************************************//
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO) # de spi bus initializeren
#******!!! DE MCP 3008 CONFIGURATIE !!!*********************************************************//
cs1 = digitalio.DigitalInOut(board.CE1)  # chip select voor mcp3008
adc = SPIDevice(spi, cs1, baudrate= 1000000) # mcp 3008 configureren voor spi
nextActive = 0 # hulpvariabelen om te voorkomen dat pot meter constant waarde stuurt voor next ch
prevActive = 0 # hulpvariabelen om te voorkomen dat pot meter constant waarde stuurt voor prev ch
#******!!! PYGAME INITIALIZEREN !!!*************************************************************//
##pygame.init() # voor de display te 'drawen' hebben we pygame nodig
#******!!! NOKIA 5110 DISPLAY GEBRUIKEN !!!*****************************************************//
dc = digitalio.DigitalInOut(board.D23)  # data/command op d23 zetten
cs0 = digitalio.DigitalInOut(board.CE0)  # chip select CE0 for display intitializeren
reset = digitalio.DigitalInOut(board.D24)  # reset pin op D24 pin zetten
display = adafruit_pcd8544.PCD8544(spi, dc, cs0, reset, baudrate= 1000000) # display SPI configureren
display.bias = 4 # bias voor de display instellen
display.contrast = 32 # contrast voor de print op het scherm
display.invert = True # True voor gewoon false om display te inverteren
#******!!! LETTERTYPEN LADEN VOOR OP SCHERM !!!*************************************************//
font1=ImageFont.truetype("/usr/share/fonts/truetype/NokiaKokia.ttf", 12)
font2 = ImageFont.truetype("/usr/share/fonts/truetype/arial.ttf", 9)
font3=ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", 12)
font4 = ImageFont.truetype("/usr/share/fonts/truetype/arial.ttf", 12)
font5 = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", 20)
#******!!! NOKIA 5110 DISPLAY GEBRUIKEN !!!*****************************************************//
image = Image.new('1', (display.width, display.height)) 
draw = ImageDraw.Draw(image)
#/////////////////////////////////////////////////////////////////////////////////////////////////


#---------------------------------------!!! DE FUNCTIES !!!---------------------------------------
# MOTOR BESTURENINGS FUNCTIE:
# motor(number, direction, pos) - het besturen van de motor
# > number      - bepaalt hoeveel nummers op het rad om te bewegen
# > direction   - bepaalt de richting van de motor
# > pos         - print de postitie waarin het rad staat
def motor(number, direction, pos):
    #de motor stappen in een loop zetten
    i = 0 # teller voor for loop
    motor_step_counter = 0 # teller om stappen te tellen voor motor
    for i in range(step_count * number): # 1 positie verder is 512 * 1... 
        for pin in range(0, len(motor_pins)): 
            GPIO.output( motor_pins[pin], step_sequence[motor_step_counter][pin] )
        if direction==True:
            motor_step_counter = (motor_step_counter - 1) % 8
        elif direction==False:
            motor_step_counter = (motor_step_counter + 1) % 8
        else: # defensive programming
            print( "uh oh... direction should *always* be either True or False" )
            cleanup()
            exit( 1 )
        sleep( step_sleep ) # snelheid tussen stappen = snelheid motor
# MOTOR CALIBRATIE FUNCTIE
def calibration():
    motor_step_counter = 0 # de motor stappen teller
    while GPIO.input(cali) == 0:# een loop zolang de calibrator niet geactiveer is (dus stopt als gecalibreert is)
        for pin in range(0, len(motor_pins)): # de motor pinnen aansturen (list met welke gpio pinnen)
            GPIO.output( motor_pins[pin], step_sequence[motor_step_counter][pin] ) # juiste sequentie aansturen
        motor_step_counter = (motor_step_counter + 1) % 8 # de teller om juiste sequentie aan te sturen
        sleep(step_sleep) # de tijd tussen motorstappen
    
    
# RADIOSTATION AFSPELEN EN GELUID EFFECT
# play(station, sound) - kiezen welke geluiden afgespeel moet worden
# > station  - bepaalt welk station afgespeeld moet worden
# > sound    - bepaalt welk sound effect moet afgespeeld moet worden
def play(station, sound):
    if sound == 1: # als variabele sound = 1 dan het geluid next afspelen 
        subprocess.call("mpc pause", shell=True) # eerst de muziek pauzeren
        subprocess.call("omxplayer --vol -800 /home/pi/mpd/music/nextt.mp3", shell=True) # next bestand afspelen
    elif sound == 2: # als variabele sound = 2 dan het geluid previous afspelen 
        subprocess.call("mpc pause", shell=True) # eerst de muziek pauzeren
        subprocess.call("omxplayer --vol -800 /home/pi/mpd/music/prevvv.mp3", shell=True) # prev bestand afspelen
    else: # wanneer geen waarde voldoet dan dit uitvoeren
        subprocess.call("mpc pause", shell=True) # eerst de muziek pauzeren
        subprocess.call("omxplayer --vol -300 /home/pi/mpd/music/welcc.mp3", shell=True) # welcc bestand afspelen
    # if om te kiezen welke radio zender afgespeeld moet worden
    if station == 1:
        subprocess.call("mpc play 1", shell=True) # console command uitvoeren
    elif station == 2:
        subprocess.call("mpc play 2", shell=True)
    elif station == 3:
        subprocess.call("mpc play 3", shell=True)
    elif station == 4:
        subprocess.call("mpc play 4", shell=True)
    elif station == 5:
        subprocess.call("mpc play 5", shell=True)
    elif station == 6:
        subprocess.call("mpc play 6", shell=True)
    elif station == 7:
        subprocess.call("mpc play 7", shell=True)
    elif station == 8:
        subprocess.call("mpc play 8", shell=True)
# LED CONTROLE FUNCTIE (afhankelijk van de pot waarde)
def led(mode):
    if mode == 1: # groene led branden als volgende channel getriggerd is (pot links)
        GPIO.output(ledPin1, 0)
        GPIO.output(ledPin2, 0)
        GPIO.output(ledPin3, 1)
    elif mode == 2: # gele led branden als pot meter neutraal staat
        GPIO.output(ledPin1, 0)
        GPIO.output(ledPin2, 1)
        GPIO.output(ledPin3, 0)
    else: # rode led branden als vorige channel getriggerd is (pot rechts)
        GPIO.output(ledPin1, 1)
        GPIO.output(ledPin2, 0)
        GPIO.output(ledPin3, 0)
# INSTELLING BESTAND (met channel name en url) UIT TE LEZEN
def settings_file():
    #alles in de playlist M3U en names TXT verwijderen
    linksFile = open("/home/pi/mpd/playlists/stations.m3u","w")
    linksFile.close()
    namesFile = open("/home/pi/mpd/playlists/names.text","w")
    namesFile.close()
    # Het text bestand met de instelling openen
    f = open('/home/pi/mpd/playlists/instelling.txt', "r")
    # use readlines to read all lines in the file
    # The variable "lines" is a list containing all lines in the file
    lines = f.readlines()
    # close the file after reading the lines.
    f.close()
    # for loop om channel naam en url te onderscheiden
    for x in lines: #x is elke lijn in het instelling.txt bestand
        lengteX = len(x) # eerst de lengte van de lijn bepalen als grens voor loop
        j = 0 # een teller j om elke char door te lopen van de current lijn in txt
        for j in range(lengteX): # elke char doorlopen van de txt line
            if x[j] == "*": # als de huidige char '*' dan splitsen wij de lijn met text in twee 'naam station' gedeelte en 'url' gedeelte
                linksHelper = x[j+1:] #alles rechts van de '*' zijn de links dus opslaan
                namesHelper = x[:j] #alles links van de '*' zijn de namen dus opslaan
                hulpListLinks.append(linksHelper) # de text met url van de huidige lijn toevoegen in list met enkel links
                hulpListNames.append(namesHelper) # de text met naam van huidige lijn toevoegen in lijst met enkel namen     
    # de lijsten van namen en urls in andere text bestanden toevoegen (die eerst geleegd werden)
    linksFile = open("/home/pi/mpd/playlists/stations.m3u","w") # bestand met de links van station
    for element in hulpListLinks:
        linksFile.write(element + "")
    linksFile.close()
    namesFile = open("/home/pi/mpd/playlists/names.txt","w") # bestand met namen van station
    for element in hulpListNames:
        namesFile.write(element + "\n")
    namesFile.close()
# MCP 3008 UIT TE LEZEN
def readadc(adcnum): 
    if ((adcnum > 7) or (adcnum < 0)): 
        return -1 
    with adc:
        r = bytearray(3)
        spi.write_readinto([1,(8+adcnum)<<4,0], r)
        sleep(0.000005)
        adcout = ((r[1]&3) << 8) + r[2] 
        return adcout 
# ---------------------SCHERM FUNCTIES----------------------------------
# DEFAULT SCHERM TE PRINTEN OP NOKIA 5110
# ***note de plek die gebruikt is door dit word niet constant geupdate
def print_screen(md):
    draw.rectangle((67, 31, 84, 41), outline=255, fill=255) # clear gedeeltelijk het scherm
    display.image(image)
    display.show()
    draw.text((8,12), "VOLUME:", font=font2) #volume printen
    draw.text((1,22), "IP: 192.168.137.88", font=font2) #ip printen
    draw.ellipse((2, 41, 12, 44), outline=0, fill=0) 
    draw.ellipse((68, 41, 81, 44), outline=0, fill=0)
    draw.ellipse((11, 35, 68, 48), outline=0, fill=255)
    if md == 1:
        draw.text((70,31), "PI", font=font2) # als de pi de gebruiker is 'PI' printen
    else:
        draw.text((68,31), "WEB", font=font2) # als web interface gebruiker is dan dit printen
    draw.text((19,35), "RAD-IO", font=font3) # logo printen
    display.image(image)
    display.show()
# DE NAAM VAN CURRENT RADIO STATION WEERGEVEN
def print_station(channel):
    draw.rectangle((-10, -10, 84, 10), outline=255, fill=255)
    display.image(image)
    display.show()
    draw.text((8,0), hulpListNames[channel-1] , font=font1) #radio channel
    display.image(image)
    display.show()
# VOLUME WEER TE GEVEN
def print_volume(vol):
    draw.rectangle((49, 10, 84, 22), outline=255, fill=255) # volume refresh
    display.image(image)
    display.show()
    draw.text((52,10), str(vol), font=font4)
    display.image(image)
    display.show()
# WELKOM SCHERM 
def print_welcome():
    draw.rectangle((-1, 0, display.width, display.height), outline=255, fill=255)
    display.image(image)
    display.show() 
    draw.ellipse((0, 13, 12, 18), outline=0, fill=0)
    draw.ellipse((68, 13, 80, 18), outline=0, fill=0)
    draw.ellipse((-5, 0, 89, 22), outline=0, fill=255)
    draw.text((8,1), "RAD-IO", font=font5)
    draw.text((10,28), "HELLO!", font=font1)
    display.image(image)
    display.show()
# SCHERM ALS PROGRAMMA STOPT
def print_bye():
    draw.rectangle((-1, 0, display.width, display.height), outline=255, fill=255)
    display.image(image)
    display.show() 
    draw.ellipse((0, 13, 12, 18), outline=0, fill=0)
    draw.ellipse((68, 13, 80, 18), outline=0, fill=0)
    draw.ellipse((-5, 0, 89, 22), outline=0, fill=255)
    draw.text((8,1), "RAD-IO", font=font5)
    draw.text((19,27), "BYE!", font=font1)
    display.image(image)
    display.show()
# HET SCHERM LEEGMAKEN
def screen_clear():
    draw.rectangle((-1, 0, display.width, display.height), outline=255, fill=255)
    display.image(image)
    display.show() 
#------------------------MQTT FUNCTIES------------------------------------
# MQTT STARTEN
def start_mqtt():
    global client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish 
    client.connect("broker.hivemq.com", 1883, 60) # url voor mqtt broker op poort 1883
    client.subscribe(MQTT_TOPIC) # subscriben op alle topics in list
    client.loop_start() # oneindige loop starten (nieuwe thread)
# ALS CONNECTED IETS PRINTEN
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    # subscribe, which need to put into on_connect
    # if reconnect after losing the connection with the broker, it will continue to subscribe to the raspberry/topic topic
    client.subscribe("radioIOT/volume")
# BIJ HET BINNEN KOMEN VAN DATA 
def on_message(client, userdata, msg):
    global vvll # gegevens die via mqtt binnenkomen global om te gebruiken in main code volume
    global nnxx # nextChannel button web interface mqtt
    global pprr # previous channel button web
    global mmdd # mode pi of web
    msg.payload = msg.payload.decode("utf-8") #decoderen data naar string
    if msg.topic == "radioIOT/volume": #filteren data en in juiste globasl variabele sorteren
        vvll = int(msg.payload)
    elif msg.topic == "radioIOT/nextChannel":
        nnxx = int(msg.payload)
    elif msg.topic == "radioIOT/prevChannel":
        pprr = int(msg.payload)
    elif msg.topic == "radioIOT/volumeMode":
        mmdd = int(msg.payload)
# VOOR HET VERZENDEN VAN DATA
def on_publish(client,userdata,result):
    pass  
#------------------------UBEAC DASHBOARD WEERGEVEN-------------------------- 
def dashboard_ubeac(ch, vl):
    #data klaarmaken voor verzenden naar uBeac via post
    data = {
                "id": "rad10",#rad10 is de device id in uBeac
                "sensors":[{
                  'id': 'ch',#sensor id voor channel
                  'data': ch #data
                },
                {
                  'id': 'vol',#sensor id voor volume
                  'data': vl#date
                }]
            }
    requests.post(url, verify=False, json=data) #url is voor ubeac client
#---------------------------------------------------------------------------


#---------------------------------------!!! DE MAIN CODE !!!---------------------------------------
try: # deze blok code wordt gecontroleerd en gerunt als er geen error is
    settings_file() # Het txt bestand met instellingen
    start_mqtt() # mqtt service starten
    print_welcome() # welkom
    subprocess.call("mpc clear", shell=True) # alle bestanden in de playlist verwijderen
    subprocess.call("mpc load stations", shell=True) # alle channels laden in de playlist soort van refresh  
    pub_name = hulpListNames[currentchannel-1] + " [" +str(currentchannel) +"/8]" # de huidige channel en het nummer ervan in string steken
    client.publish("radioIOT/channelName",str(pub_name)) # de ^^ info weergeven op dashboard mqtt
    play(currentchannel, 3) # channel 8 spelen en het welcome sound effect
    calibration() # de motor calibreren op positie 8 (altijd 8 omdat hardware matig gedaan)
    screen_clear() # het scherm clearen
    print_station(currentchannel) # huidige radio station weergeven op scherm
    print_screen(1) # kleine menu weergeven

    #****note volgende oneindige loop heeft 2 modussen "controleren via pi" en "controleren via web server"
    while True:#oneindige loop maken
        #----------- MODE RADIO CONTROLEREN VIA PI ---------------
        if mmdd == 0: # als op de web "use Raspberry pi " knop dan enkel deze proportie gebruiken via mqtt = mmdd (mode)
            client.publish("radioIOT/mode","RASPBERRY PI") # weergeven op mqtt dash welke mode gebruikt is
            #----------------inlezen van de pot meters-------------------
            adcValue1 = readadc(6) # read channel 0 
            adcValue2 = readadc(0) # read channel 1        
            #---------channel en volume controle met pot meter-----------   
            volume = volumeInvertHulp - int((adcValue2 / 1023) * 100) #variabele omvorming voor volume regeling 
            if volume != volumeHulp: #volume enkel aanpassen bij veranderen van de volume waarde
                command = commandVolume + str(volume) # een command string gereed maken voor sub process "mpc volume [vol]"
                command2 = str(command) # alles in een string zetten (dit wordt enkel aanvaard)
                subprocess.call(command2, shell=True) # shell commande voor volume toepasesen 
            print_volume(volume) # volume weergeven op scherm
            client.publish("radioIOT/volume",volume) # volume weergeven via mqtt enkel bij veranderen
            volumeHulp = volume # hulp var om verandering te detecteren (dit is vorige waarde) dit kan je vergelijken
            dashboard_ubeac(currentchannel, volume) # het dashboard aanpassen
            if ( (adcValue1 >= 0) & (adcValue1 <= 246.5) ):#prev
                led(1) # de rode led voor vorige led aansturen
                changePrev = 1 # hulp om als de meter rechts staat maar 1 keer next command sturen ipv oneindig
                if (changePrev == 1) & (prevActive != 1): # als de status niet actief was vorige loop dan doorlopen
                    prevActive = 1 # vorige actief zetten hulp variabelen
                    changePrev = 0 # vorige actief zetten hulp variabelen
                    currentchannel -= 1 # de huidige channel met 1 aftrekken bv (eers was 8... na deze bew. is het nu channel 7)
                    if currentchannel == 0: # als dit 0 heeft bereikt reset de waarde naar beginwaarde (de rad heeft een revolutie gedaan)
                        currentchannel = 8 ### beginwaarde terug zetten
                    pub_name = hulpListNames[currentchannel-1] + " [" +str(currentchannel) +"/8]" #speciale mqtt publisch om te formateren voor dashboard (current channel [ch out of 8])
                    client.publish("radioIOT/channelName",str(pub_name)) # de channel naam publischen
                    play(currentchannel, 2)  # huidge channel afspelen en 'previous' sound effect
                    print_station(currentchannel) # station weergeven op lcd
                    motor(1, True, currentchannel) # de motor een positie terug zetten op de rad
            elif ( (adcValue1 >= 276.5) & (adcValue1 <= 746.5) ): # als de pot meter neutraal staat dan...
                prevActive = 0 # vorige terug op niet actief zetten hulp variabele
                nextActive = 0 # volgende terug op niet actief zetten hulp variabelen
                led(2) # de gele led laten branden
            elif ( (adcValue1 >= 776.5) & (adcValue1 <= 1023) ):#als pot meter links staat dan...
                changeNext = 1 #next op actief zetten
                led(3)  # groene led laten branden
                if (changeNext == 1) & (nextActive != 1): # als vorige loop dit niet eens is doorlopen dan doorloopen
                    nextActive = 1 # zet actief zodat volgende keer als nog links staat niet nogeens next channel
                    changeNext = 0 # change op nul zetten zodat niet dubbel gedaan word
                    currentchannel += 1 # de huidige channel met 1 omhoog doen (next channel)
                    if currentchannel == 9: # als de limiet bereikt is dan resetten (rad heeft volledige ronde gedaan)
                        currentchannel = 1 # terug op begin waarde
                    pub_name = hulpListNames[currentchannel-1] + " [" +str(currentchannel) +"/8]" # speciale naam voor op mqtt dashboard weer te geven maken [radio name] + [out of 8]
                    client.publish("radioIOT/channelName",str(pub_name))  # de speciale naam publischen
                    play(currentchannel, 1) # current channel weegeven en 'next sound effect' afspelen
                    motor(1, False, currentchannel) # de motor met rad de volgende positie laten doen
                    print_station(currentchannel) # current radio naam op scherm weergeven
            nnxx = 0 # de web interface niks laten doen (mqtt variabelen) omdat 'pi mode is geselecteerd'
            pprr = 0 # de web .. ^^ idem
            print_screen(1) # basis scherm afprinten en ook de modus
        #---------- MODE RADIO CONTROLEREN VIA WEB ---------------
        else: # als op web interface de web mode geselecteed is dan dit doorlopen
            client.publish("radioIOT/mode","WEB INTERFACE")  # de modus weergeven in mqtt dashboard
            if nnxx == 1: # als next channel dan next channel afpselen
                nnxx = 0 # op niet actief zetten
                currentchannel += 1 # channel met 1 incrementeren
                if currentchannel == 9: # limiet instellen (rad volledig rond)
                    currentchannel = 1 # beginwaarde
                pub_name = hulpListNames[currentchannel-1] + " [" +str(currentchannel) +"/8]" #speciale naam voor op mqtt dashboard weer te geven maken [radio name] + [out of 8]
                client.publish("radioIOT/channelName",str(pub_name)) # de speciale naam publischen
                play(currentchannel, 1) # current channel weegeven en 'next sound effect' afspelen
                motor(1, False, currentchannel) # de motor met rad de volgende positie laten doen
                print_station(currentchannel) # current radio naam op scherm weergeven
            if pprr == 1: # als op web interface previous channel knop dan...
                pprr = 0 # terug op niet actief zetten
                currentchannel -= 1 # channel met 1 beneden laten gaan
                if currentchannel == 0: # limiet zetten (rad is volledig rond gegaan)
                    currentchannel = 8 # terug op beginwaarde zetten
                play(currentchannel, 2) #current channel afspelen en previous sound effect: 
                pub_name = hulpListNames[currentchannel-1] + " [" + str(currentchannel) +"/8]"#speciale naam voor op mqtt dashboard weer te geven maken [radio name] + [out of 8]
                client.publish("radioIOT/channelName",str(pub_name))  # de speciale naam publischen
                print_station(currentchannel)# current radio naam op scherm weergeven
                motor(1, True, currentchannel)# de motor met rad de volgende positie laten doen
            print_screen(2) # scherm printen met mode "web"
            dashboard_ubeac(currentchannel, vvll) #Ubeac dashboard updaten
            client.publish("radioIOT/volume",vvll) #het volume via mqtt updaten op dashboard
            subprocess.call(str("mpc volume ") + str(vvll), shell=True) # console command om volume werkelijk aan te passen
            print_station(currentchannel) # huidig kanaal aanpassen
            print_volume(vvll) # volume op lcd weergeven
    
    
except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    print_bye() # bye scherm op lcd laten zien
    screen_clear() # het scherm clearen
    subprocess.call("mpc pause", shell=True) # het pauzeren van de mpc player
    subprocess.call("mpc stop", shell=True) # het stoppen van de mpc player
    subprocess.call("omxplayer --vol -800 /home/pi/mpd/music/bye.mp3", shell=True) # byebye bestand afspelen
    sys.exit(0)
    

finally: #Deze blok wordt gerunt nadat de 'try' blok afgerond is met of zonder error
    GPIO.cleanup() # proper maken van alle GPIO 