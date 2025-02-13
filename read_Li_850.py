from machine import Pin
import time
import ads1x15
import ssd1306 # I2C oled screen

device_status = "Startup" # this will be need to know which screen should be displayed

def make_measurement(dac_max_voltage,dac_range_CO2, dac_range_H2O,ads):
    # measure the output of the Li850 dac
    value_DAC_CO2 = ads.read(1,0) # read output of Li-850 dac for CO2
    value__DAC_H2O = ads.read(1,1) # read output of Li-850 dac for H2O
    value_CO2 = value_DAC_CO2 * dac_max_voltage/dac_range_CO2 # ppm CO2
    value_H2O = value_DAC_H2O * dac_max_voltage/dac_range_H2O # mmol H2O/mol
    
    return (value_CO2,value_H2O)


def startup_screen(display):
    device_status = "Startup"
    display.fill(0)
    display.text("Startup of Li850 device", 0, 0, 1)
    display.text("Start", 115,0,1)
    display.text("PPM",115,len("start")*8+5,1)
    display.show()

def ppm_disp_screen(display, CO2_value, H2O_value):
    device_status = "PPM"
    display.fill(0)
    display.text("Reading CO2 and H2O", 0, 0, 1)
    display.text("CO2 :",50,0,1)
    display.show()


#### Buttons ####
sel_1 = Pin(4,Pin.IN) # Selection button 1
sel_2 = Pin(5, Pin.IN) # Selection button 2
sel_2 = Pin(6, Pin.IN) # Selection button 3

#### Initializing I2C devices ####
i2c_adc = I2C(0, sda=Pin(16), scl=Pin(17)) 
i2c_screen = I2C(1,sda=Pin(2), scl=Pin(3))

try:
    display = ssd1306.SSD1306_I2C(128, 64, i2c2)
except:
    print("No screen connection")
try:
    ads = ads1x15.ADS1115(i2c_adc, addr, gain)
except:
    print("no access to device")

#### Starting up ####

