from machine import Pin, I2C, RTC
import time
import ads1x15
import ssd1306 # I2C oled screen

device_status = "Startup" # this will be need to know which screen should be displayed
addr = 72
gain = 0

#### Buttons ####
sel_1 = Pin(4,Pin.IN, Pin.PULL_UP) # Selection button 1
sel_2 = Pin(5, Pin.IN, Pin.PULL_UP) # Selection button 2

Button_1 = False # Selection button 1
Button_2 = False # Selection button 2
measurement_active = False # tells us if a measurement is currently active
filename = "" # filename for saving the data

rtc = RTC()

def Button_1_interrupt(pin):
    global Button_1
    Button_1 = True
def Button_2_interrupt(pin):
    global Button_2
    Button_2 = True

sel_1.irq(trigger=Pin.IRQ_RISING, handler=Button_1_interrupt)
sel_2.irq(trigger=Pin.IRQ_RISING, handler=Button_2_interrupt)

def make_measurement(ads,dac_max_voltage=2.5,dac_range_CO2=5000, dac_range_H2O=60):
    # measure the output of the Li850 dac
    value_DAC_CO2 = ads.raw_to_v(ads.read(1,0)) # read output of Li-850 dac for CO2
    value_DAC_H2O = ads.raw_to_v(ads.read(1,1)) # read output of Li-850 dac for H2O
    value_CO2 = value_DAC_CO2 / dac_max_voltage * dac_range_CO2 # ppm CO2
    value_H2O = value_DAC_H2O / dac_max_voltage * dac_range_H2O # mmol H2O/mol
    print(value_DAC_CO2, value_DAC_H2O)
    return (value_CO2,value_H2O)

def startup_screen(display, device_status):
    global Button_1
    global Button_2
    device_status = "Startup"
    if Button_1:
        device_status = "Time"
        Button_1 = False
        return device_status
    if Button_2:
        device_status = "PPM"
        Button_2 = False
        return device_status
    display.fill(0)
    display.text("Startup of Li850", 0, 0, 1)
    display.text("Time", 0,56,1)
    display.text("PPM",128-len("PPM")*8,56,1)
    display.show()
    time.sleep(0.5)
    return device_status

def ppm_disp_screen(display, adc, device_status):
    global Button_1
    global Button_2
    device_status = "PPM"
    if Button_1:
        device_status = "Measure"
        Button_1 = False
        return device_status
    if Button_2:
        device_status = "Startup"
        Button_2 = False
        return device_status
    values = make_measurement(ads=adc)
    display.fill(0)
    display.text("Read. CO2 & H2O", 0, 0, 1)
    display.text("CO2 : %1.1f" % values[0],5,15,1)
    display.text("H20 : %1.1f" % values[1],5,30,1)
    display.text("Start", 0,56,1)
    display.text("Back",128-len("Back")*8,56,1)
    display.show()
    time.sleep(0.5)
    return device_status
    
def measurement_screen(display, adc,device_status):
    global Button_1
    global Button_2
    global measurement_active
    global filename
    
    if Button_1:
        Button_1 = False
        return "Slope"
    if Button_2:
        Button_2 = False
        measurement_active = False
        return "PPM"
    if not measurement_active:
        filename = "newfile.txt"
        measurement_active = True
    
    values = make_measurement(ads=adc)
    
    with open(filename,'a') as f:
        f.write("%1.2f,%1.2f \n" % values)
    
    if device_status=="Slope":
        dots = ""
        for i in range(0,5):
            display.fill(0)
            display.text("Measuring"+dots, 0, 0, 1)
            display.text("CO2 slope: %1.1f" % values[0],5,15,1)
            display.text("H20 slope: %1.1f" % values[1],5,30,1)
            display.text("Back", 0,56,1)
            display.text("Stop",128-len("Stop")*8,56,1)
            display.show()
            dots = dots+"."
            time.sleep(0.2)
    else:
        dots = ""
        for i in range(0,5):
            display.fill(0)
            display.text("Measuring"+dots, 0, 0, 1)
            display.text("CO2 : %1.1f" % values[0],5,15,1)
            display.text("H20 : %1.1f" % values[1],5,30,1)
            display.text("Slope", 0,56,1)
            display.text("Stop",128-len("Stop")*8,56,1)
            display.show()
            dots = dots+"."
            time.sleep(0.2)
    return device_status

def time_display():
    now = rtc.datetime()
    global Button_1
    global Button_2
    if Button_1:
        Button_1 = False
        return "Time"
    if Button_2:
        Button_2 = False
        return "PPM"
    display.fill(0)
    display.text("Startup of Li850", 0, 0, 1)
    display.text("Month: "+str(now[1]), 5, 9+5, 1)
    display.text("Day: "+str(now[2]), 5, 18+5, 1)
    display.text("Hour: "+str(now[3]), 5, 27+5, 1)
    display.text("Minutes: "+str(now[4]), 5, 36+5, 1)
    display.text("Update", 0,56,1)
    display.text("PPM",128-len("PPM")*8,56,1)
    display.show()
    time.sleep(2)
    return "Startup"

def call_screens(disp,adc,device_status):
    if device_status == "Startup":
        status = startup_screen(disp, device_status)
    elif device_status == "PPM":
        status = ppm_disp_screen(disp, adc, device_status)
    elif device_status == "Measure" or device_status == "Slope":
        status = measurement_screen(disp, adc, device_status)
    elif device_status == "Time":
        status = time_display()
    else:
        disp.fill(0)
        disp.text("BUG", 0, 50, 1)
        disp.show()
        time.sleep(2)
        status = "Startup"
    return status


#### Initializing I2C devices ####
i2c_adc = I2C(0, sda=Pin(16), scl=Pin(17)) 
i2c_screen = I2C(1,sda=Pin(2), scl=Pin(3))


display = ssd1306.SSD1306_I2C(128, 64, i2c_screen)
ads = ads1x15.ADS1115(i2c_adc, addr, gain)
status = "Startup"
#### Starting up ####
startup_screen(display, status)

#Functionning
while True:
    status = call_screens(display, ads, status)
