import machine
import utime
import ustruct
import sys
import binascii

# Registers

ID = 0x00

# Channel specific settings

CH1SET = 0x05
CH2SET = 0x06
CH3SET = 0x07
CH4SET = 0x08
CH5SET = 0x09
CH6SET = 0x0a
CH7SET = 0x0b
CH8SET = 0x0c

###########################################################################
# Reset and register values
#CONFIG1
CONFIG1 = 0x01
CONFIG1_reset = 0x91
#|   07   |   06   |   05   |   04   |   03   |   02   |   01   |   00   |
#    01    DAISY_IN  CLK_EN     01       00   |           DR[2:0]        |

#CONFIG2
CONFIG2 = 0x02
CONFIG2_reset = 0xE0
#|   07   |   06   |   05   |   04   |   03   |   02   |   01   |   00   |
#|   01       01       01    INT_TEST    00    TEST_AMP    TEST_FREQ[0:1]

#CONFIG3
CONFIG3 = 0x03
CONFIG3_reset = 0x40
#|   07   |   06   |   05   |   04   |   03   |   02   |   01   |   00   |
#| PDB_RBUF   01     VREF4V     00    OPAMPREF PDBOPAMP    00       00 

#FAULT
FAULT = 0x04
FAULT_reset = 0x00
FAULT_mask = 0xE0
#|   07   |   06   |   05   |   04   |   03   |   02   |   01   |   00   |
#|        COMP_TH[2:0]      |   00       00       00       00       00    

#FAULT_STATP
FAULT_STATP = 0x12
FAULT_STATP_reset = 0x00
#|   07   |   06   |   05   |   04   |   03   |   02   |   01   |   00   |
#|  IN8PF    IN7PF    IN6PF    IN5PF    IN4PF    IN3PF    IN2PF    IN1PF    F = Fault

#FAULT_STATN
FAULT_STATN = 0x13
FAULT_STATN_reset = 0x00
#|   07   |   06   |   05   |   04   |   03   |   02   |   01   |   00   |
#|  IN8NF    IN7NF    IN6NF    IN5NF    IN4NF    IN3NF    IN2NF    IN1NF    F = Fault

# GPIO settings
GPIO = 0x014
GPIO_reset = 0x0F
#|   07   |   06   |   05   |   04   |   03   |   02   |   01   |   00   |
#|          GPIo[7:4]                |            GPIO[3:0]              |

#####################################################################################
# SYSTEM COMMANDS
WAKEUP = 0x02
STANDBY = 0x04
RESET = 0x06
STARTC = 0x08
STOP = 0x0a
OFFSETCAL = 0x1A

#DATA READ COMMANDS
RDATAC = 0x10
SDATAC = 0x11
RDATA = 0x12

#REGISTER READ COMMANDS
#RREG = 0x20
#WREG = 0x40

###########################################################
# Pico Settings
# Assign chip select (CS) and START and start them high
START = machine.Pin(22, machine.Pin.OUT, value=1) # purple actual pin 34
cs = machine.Pin(17, machine.Pin.OUT, value=1) #  grey pin 12 (physical pin numbers)
DRDY = machine.Pin(21, machine.Pin.IN) # green pin 32

# Initialize SPi
sck=machine.Pin(18) # blue
mosi=machine.Pin(19) # yellow
miso=machine.Pin(16) # orange
baudr8 = 10000000

spi = machine.SPI(0,
                  baudrate=baudr8,
                  polarity=0,
                  phase=1,
                  bits=8,
                  firstbit=machine.SPI.MSB,
                  sck=sck,
                  mosi=mosi,
                  miso=miso)
# actual pin 25
# pin 24
# pin 21

############################################################
# Clock Delay to allow calculating between multibit commands

baudr8 = 1e6
CLKrate = 2.046e6
TS_decode = 4/CLKrate #1.96us
SCK_time_1bit = 8*(1/(baudr8)) # time for 8 bits
CLKDEL = TS_decode - SCK_time_1bit
if CLKDEL < 0:
    CLKDEL = 0


############################################################
#Functions for read and write

def write_(spi, cs, reg, nreg, dat):
    #"""
   # write nreg bytes to the specified register/s
   # don't write to registers  (0Dh–11h), unless overwriting the data 
    #"""
    
    # Construct message
    msg1 = bytearray()
    msg1.append(0x40 | reg) #set write bit high and declare registry to write to
    
    nreg1 = nreg - 1
    msg2 = bytearray()
    msg2.append(0x00 | nreg1) # specify number of registers to write
    
    regdat = bytearray()
    regdat.append(0x00 | dat)

    # send out spi message
    cs.value(0)
    spi.write(msg1)
    utime.sleep(CLKDEL)
    spi.write(msg2)
    
    for i in range(nreg):
        utime.sleep(CLKDEL)
        data = spi.write(regdat)
        #print('writing data to registry')
        #print(binascii.hexlify(bytearray(regdat)))
        
    cs.value(1)

def command_(spi, cs, command):
    msg = bytearray()
    cs.value(0)
    msg.append(0x00 | command)
    print('sending command')
    spi.write(msg)
    print(binascii.hexlify(bytearray(msg)))
    if command == RESET:
        utime.sleep(TS_decode*5)
    else:
        utime.sleep(TS_decode)

    cs.value(1)
    
def read_(spi, cs, reg, nreg):
    #"""
   # read nbytes bytes from nreg starting at the specified register/s
    #"""
    # Construct message
    msg1 = bytearray()
    msg1.append(0x40 | reg) #set write bit high and declare registry to read from
    
    nreg1 = nreg - 1
    msg2 = bytearray()
    msg2.append(0x00 | nreg1) # specify number of registers to read
    
    # send out spi message
    cs.value(0)
    spi.write(msg1)
    utime.sleep(CLKDEL)
    spi.write(msg2)
    
    BUFF = bytearray(nreg)
    
    utime.sleep(CLKDEL)
    spi.readinto(BUFF)

    cs.value(1)
    
    return BUFF
    
###########################################################################
# Startup sequence
# CS pin high (tie start pin low on ADS131?)
# START pinhigh
cs.value(1)
onoff = cs.value()
if onoff == 1:
    print("CS pin high")
else:
    print("CS pin low")
onoff = 0

onoff = DRDY.value()
if onoff == 1:
    print("DRDY pin high")
else:
    print("DRDY pin low")
onoff = 0

onoff = sck.value()
if onoff == 1:
    print("SCK pin high")
else:
    print("SCK pin low")
onoff = 0

onoff = START.value()
if onoff == 1:
    print("START pin high")
else:
    print("START pin low")
onoff = 0

print('reading from ID registry')
data = read_(spi, cs, ID, 1)
print(data)

command_(spi, cs, RESET)
command_(spi, cs, SDATAC) # stop data continuous command.
print('writing 0xC0 to registry config3') # use internal reference
write_(spi, cs, CONFIG3, 1, 0xC3)
print('writing 0x91 to registry config1') # use internal reference
write_(spi, cs, CONFIG1, 1, 0x91)
print('writing 0xC0 to registry config2') # use internal reference
write_(spi, cs, CONFIG3, 1, 0xE0)

print('writing 0x01 to all 8 channel settings')
write_(spi, cs, CH1SET, 8, 0x01)

print('reading from ID and config registries')
data = read_(spi, cs, CONFIG1, 4)
print(data)

print('set start to 1; if stays low, manually reset the ADS131')
START.value(1)
onoff = START.value()
if onoff == 1:
    print("START pin high")
else:
    print("START pin low")
onoff = 0



while True:
    data = read_(spi, cs, CONFIG1, 4)