from machine import Pin, I2C, RTC, Timer
import machine
from array import array
import time
import ads1x15
import ssd1306 # I2C oled screen
import urtc
import sdcard
import vfs

class Li850:
    
    i2c_devices = I2C(1,sda=Pin(2), scl=Pin(3))
    adc_addr = 72 # I2C address for the ADC
    adc_gain = 0 # Gain of ADC
    i2c_clock = I2C(0,scl=Pin(5), sda=Pin(4))
    dac_max_voltage = 2.5
    dac_range_CO2 = 5000
    dac_range_H2O = 60
    
    def __init__(self, timestep=10):
        self.active_measurement = False
        self.Button_left = False
        self.Button_right = False
        self.filename = ""
        #### Values #####
        self.CO2 = 0
        self.H2O = 0
        self.CO2_values_array = array("f")
        self.H20_values_array = array("f")
        #### Buttons ####
        self.left = Pin(6,Pin.IN, Pin.PULL_UP) # Selection button 1
        self.right = Pin(7, Pin.IN, Pin.PULL_UP) # Selection button 2
        #### I2C devices ####
        self.display = ssd1306.SSD1306_I2C(128, 64, self.i2c_devices)
        self.adc = ads1x15.ADS1115(self.i2c_devices, self.adc_addr, self.adc_gain)
        self.rtc = urtc.PCF8523(self.i2c_clock)
        #### Measurement option ####
        self.timestep_meas = timestep # time between two logs in secs
        #### Screen status ####
        self.device_status = "Startup"
        #### Button interrupts ####
        self.left.irq(trigger=Pin.IRQ_RISING, handler=self._Button_left_interrupt)
        self.right.irq(trigger=Pin.IRQ_RISING, handler=self._Button_right_interrupt)
        #### Measure timer setup ####
        self.meas_timer = Timer()
        self.meas_now = False
        self.new_meas = False
    
    def make_measurement(self):
        # measure the output of the Li850 dac using an ADC
        state = machine.disable_irq() # stops interrupts to prevent any meas issues
        try:
            value_DAC_CO2 = self.adc.raw_to_v(self.adc.read(1,0)) # read output of Li-850 dac for CO2
            value_DAC_H2O = self.adc.raw_to_v(self.adc.read(1,1)) # read output of Li-850 dac for H2O
            self.CO2 = value_DAC_CO2 / self.dac_max_voltage * self.dac_range_CO2 # ppm CO2
            self.H2O = value_DAC_H2O / self.dac_max_voltage * self.dac_range_H2O # mmol H2O/mol
        except:
            self.CO2 = 9999
            self.H2O = 9999
        machine.enable_irq(state) # reenables interrupts
        #print(value_DAC_CO2, value_DAC_H2O) - enable for debug
        #return (value_CO2,value_H2O) - enable for debug
    
    def _save_data_to_file(self, var1, var2):
        state = machine.disable_irq()
        with open(self.filename,'a') as f:
            now = self.rtc.datetime()
            f.write(str(now.year)+"-"+str(now.month)+"-"+str(now.day)+"T"+str(now.hour)+":"+str(now.minute)+":"+str(now.second)+",")
            f.write("%1.2f,%1.2f \n" % (var1, var2))
        machine.enable_irq(state)
    
    def _Button_left_interrupt(self, Pin):
        self.Button_left = True
    def _Button_right_interrupt(self, Pin):
        self.Button_right = True
    def check_Button_status(self,left_option, right_option):
        if self.Button_left:
            self.Button_left = False
            self.device_status = left_option
            return None
        elif self.Button_right:
            self.Button_right = False
            self.device_status = right_option
            return None
    def meas_callback(self, timer):
        self.meas_now = True
    
    def _display_bottom_options(self,left_str, right_str):
        ### To display the selectable choices at bottom of screen ###
        self.display.text(left_str, 3, 56, 1)
        self.display.rect(0, 54, len(left_str)*8+6, 15, 1)
        self.display.text(right_str,128-(len(right_str)*8+3),56,1)
        self.display.rect(128-(len(right_str)*8+6), 54, len(right_str)*8+6, 15, 1)
    
    def _display_startup_screen(self):
        self.check_Button_status("Time", "Instant")
        #### Display #####
        self.display.fill(0)
        self.display.text("Startup of Li850", 0, 0, 1)
        # Buttons at the bottom
        self._display_bottom_options("Time","Instant")
        self.display.show()
        time.sleep(0.1)
    
    def _display_time_screen(self):
        self.check_Button_status("Time", "Startup")
        ### RTC get Time ####
        now = self.rtc.datetime()
        self.display.fill(0)
        self.display.text("Current Time", 0, 0, 1)
        # display the RTC time and date
        self.display.text("Month: "+str(now.month), 5, 8+1, 1)
        self.display.text("Day: "+str(now.day), 5, 16+2, 1)
        self.display.text("Hour: "+str(now.hour), 5, 24+3, 1)
        self.display.text("Minutes: "+str(now.minute), 5, 32+4, 1)
        self.display.text("Seconds: "+str(now.second), 5, 40+5, 1)
        # Buttons at the bottom
        self._display_bottom_options("Update","Back")
        # show
        self.display.show()
        time.sleep(0.1)
        
    def _display_Instant_screen(self):
        self.check_Button_status("Meas", "Startup")
        self.make_measurement()
        self.display.fill(0)
        self.display.text("Read. CO2 & H2O", 0, 0, 1)
        self.display.text("CO2 : %1.1f" % self.CO2,5,15,1)
        self.display.text("H20 : %1.1f" % self.H2O,5,30,1)
        # Buttons at the bottom
        self._display_bottom_options("Start","Back")
        # show
        self.display.show()
        time.sleep(0.2)

    def _display_measurement_screen(self):
        if not self.new_meas:
            dt = self.rtc.datetime()
            self.filename = "/sd/data_"+str(dt.year)+"-"+str(dt.month)+"-"+str(dt.day)+"_"+str(dt.hour)+":"+str(dt.minute)+".txt"
            self.new_meas = True
            self.meas_timer.init(period = self.timestep_meas*1000,callback = self.meas_callback)
            self.make_measurement()
        if self.meas_now:
                self.make_measurement()
                self._save_data_to_file(self.CO2, self.H2O)
                self.meas_now = False
        
        if self.device_status =="Meas":
            self.check_Button_status("Slope", "Stop")
            self.display.fill(0)
            self.display.text("Measuring...", 0, 0, 1)
            self.display.text("CO2 : %1.1f" % self.CO2,5,15,1)
            self.display.text("H2O : %1.1f" % self.H2O,5,30,1)
            self._display_bottom_options("Slope","Stop")
            self.display.show()
            time.sleep(0.1)
        elif self.device_status == "Slope":
            self.check_Button_status("Instant", "Stop")
            self.display.fill(0)
            self.display.text("Measuring...", 0, 0, 1)
            self.display.text("CO2 : %1.1f" % self.CO2,5,15,1)
            self.display.text("H2O : %1.1f" % self.H2O,5,30,1)
            self._display_bottom_options("Instant","Stop")
            self.display.show()
            time.sleep(0.1)
    
    def run(self):
        while True:
            if self.device_status == "Startup":
                self._display_startup_screen()
            elif self.device_status == "Time":
                self._display_time_screen()
            elif self.device_status == "Instant":
                self._display_Instant_screen()
            elif self.device_status == "Meas":
                self._display_measurement_screen()
            elif self.device_status == "Stop":
                self.meas_timer.deinit()
                self.new_meas = False
                self._display_Instant_screen()
            else:
                self.display.fill(0)
                self.display.text("BUG", 0, 50, 1)
                self.display.show()
                time.sleep(2)
                self.device_status = "Startup"

##### Setting up SD card ######
cs = Pin(17,Pin.OUT)
spi = machine.SPI(0, 
                  baudrate=1000000,
                  polarity=0,
                  phase=0,
                  bits=8,
                  firstbit=machine.SPI.MSB,
                  sck=Pin(18),
                  mosi=Pin(19),
                  miso=Pin(16))
sd = sdcard.SDCard(spi, cs)
filsys = vfs.VfsFat(sd)
vfs.mount(filsys, "/sd")

test = Li850(2)
test.run()



    