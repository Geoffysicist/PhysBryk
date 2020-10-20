"""PhysBryk module.
Services & Characteristics
MotionService       100
    acceleration    101
    gyro            102
MagnetService 200
    magnet        201
EMRService          300
    intensity       301
    spectrum        302
    proximity       303
DummyService        1000
    value           1001
    

Base uuid for PhysBryk is a0d1nnnn-0eaa-5b52-bc84-818888dc7dc5
Generated by 
physbryk_uuid.baseUUID('https://github.com/Geoffysicist/PhysBrykPy')

  Typical usage example:

  foo = SampleClass()
  
  bar = foo.public_method(required_variable, optional_variable=42)
"""

import random as rn
import struct
import math

from micropython import const

from adafruit_ble.advertising import Advertisement, LazyObjectField
from adafruit_ble.advertising.standard import ManufacturerData, ManufacturerDataField
from adafruit_ble.characteristics import Characteristic, StructCharacteristic
from adafruit_ble.characteristics.int import Uint8Characteristic, Int32Characteristic, Int16Characteristic, Uint32Characteristic, Uint16Characteristic
from adafruit_ble.characteristics.float import FloatCharacteristic
from adafruit_ble.characteristics.string import StringCharacteristic, FixedStringCharacteristic
from adafruit_ble.uuid import VendorUUID
from adafruit_ble.services import Service
from adafruit_ble.attributes import Attribute
from adafruit_ble import BLERadio # , BLEConnection

from adafruit_ble_adafruit.adafruit_service import AdafruitService

# _MANUFACTURING_DATA_ADT = const(0xFF)
# _ADAFRUIT_COMPANY_ID = const(0x0822)
# _PID_DATA_ID = const(0x0001)  # This is the same as the Radio data id, unfortunately.
PHYSBRYK_UUID = 'a0d10000-0eaa-5b52-bc84-818888dc7dc5'

MEASUREMENT_PERIOD = 1000

class PhysBryk(object):
    
    def __init__(self, device=None):
        '''device is a PhysBryk BLE device'''
        self._device = device
        self._connection = None
        self._connected = False
    
    def setDevice(self, ble_device):
        self._device = ble_device
        
    def getAddress(self):
        return self._device.address

    def getName(self):
        return self._device.name

    def connected():
        if self._connection:
            self._connected = self._connection.connected
        else:
            self._connected = False
        return self._connected

class PhysBrykClient(object):
    def __init__(self):
        self._connection = None # a BLEConnection TODO change to a PhysBryk
        self._connected = False
        self._name = None
        self._measurement_period = 1000
        self._services = []
        self._core_service = None
        self._electrical_service = None

        self._log = []

    def connect(self):
        print("Scanning for a PhysBryk Server advertisement...")
        ble = BLERadio()  # pylint: disable=no-member
        for adv in ble.start_scan(PhysBrykServerAdvertisement, timeout=10):
            if adv.complete_name and ("PhysBryk" in adv.complete_name):
                print(f'Found {adv.complete_name}, connecting...')
                self._connection = ble.connect(adv)
                print(adv)
                self._name = adv.complete_name
                if self.connected():
                    self._core_service = self._connection[CoreService]
                    self._services.append(self._core_service)
                    try: #TODO maybe move this checking to the server side
                        self._electrical_service = self._connection[ElectricalService]
                        self._services.append(self._electrical_service)
                    except NameError:
                        self._electrical_service = None
                    print(f"{self.getName()} connected")
                                
                else:
                    print(f'unable to connect to {self.getName()}')

                break  # Stop scanning whether or not we are connected.
        ble.stop_scan()

    def connected(self):
        '''Boolean described connection status.
        '''
        self._connected = self._connection.connected
        return self._connected

    def getName(self):
        return self._name

    def setMeasurementPeriod(self, period):
        self._measurement_period = period
        for s in self._services:
            s.measurement_period = self._measurement_period

    def getMeasurementPeriod(self):
        return self._measurement_period

    def get_voltage(self):
        """Calculates the voltage from the reading of the on board battery sensor."""
        return (self._core_service.battery * 3.3) / 65536 * 2
    
    def getAcceleration(self):
        return self._core_service.acceleration

    def getNetAcceleration(self):
        acc_xzy = self._core_service.acceleration
        acc_net = 0
        for a in acc_xzy:
            acc_net += a**2
        return math.sqrt(acc_net)

    def getMagnetic(self):
        return self._core_service.magnetic

    def record(self, data):
        self._log.clear()

class PhysBrykServerAdvertisement(Advertisement):
    """Advertise theBryk.
    """

    def __init__(self):
        super().__init__()
        self.connectable = True
        self.flags.general_discovery = True
        self.flags.le_only = True

class PhysBrykService(Service):
    """Common superclass for all PhysBryk board services."""

    @staticmethod
    def physbryk_service_uuid(n):
        """Generate a VendorUUID which fills in a 16-bit value in the standard
        PhysBryk Service UUID: a0d1839c-0eaa-5b52-nnnn-818888dc7dc5.
        """
        # return VendorUUID("ADAF{:04x}-C332-42A8-93BD-25E905756CB8".format(n))
        return VendorUUID('a0d1{:04x}-0eaa-5b52-bc84-818888dc7dc5'.format(n))

    @classmethod
    def name_charac(cls, name='PhysBryk Service'):
        """Create a measurement_period Characteristic for use by a subclass."""
        return StringCharacteristic(
            uuid=cls.physbryk_service_uuid(0x0001),
            write_perm=Attribute.NO_ACCESS,
            initial_value=name,
        )

    @classmethod
    def measurement_period_charac(cls, msecs=MEASUREMENT_PERIOD):
        """Create a measurement_period Characteristic for use by a subclass."""
        return Int32Characteristic(
            uuid=cls.physbryk_service_uuid(0x0002),
            properties=(Characteristic.READ | Characteristic.WRITE),
            initial_value=msecs,
        )

    @classmethod
    def service_version_charac(cls, version=1):
        """Create a service_version Characteristic for use by a subclass."""
        return Uint32Characteristic(
            uuid=cls.physbryk_service_uuid(0x0003),
            properties=Characteristic.READ,
            write_perm=Attribute.NO_ACCESS,
            initial_value=version,
        )

class CoreService(PhysBrykService):
    """Core, 'on-board' charactistics for the physbryk."""

    #the bryk 0000
    uuid = PhysBrykService.physbryk_service_uuid(0x0000)

    # Default period set by MEASUREMENT_PERIOD.
    measurement_period = Int32Characteristic(
        uuid=PhysBrykService.physbryk_service_uuid(0x0001),
        properties=(Characteristic.READ | Characteristic.WRITE),
        initial_value=MEASUREMENT_PERIOD,
    )

    battery = Uint16Characteristic(
        uuid=PhysBrykService.physbryk_service_uuid(0x0002),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    
    # motion sensor 0100
    motion_enabled =  Uint8Characteristic(
        uuid=PhysBrykService.physbryk_service_uuid(0x0100),
        initial_value=1,
    )
    # Tuple (x, y, z) float acceleration values, in m/s/s
    acceleration = StructCharacteristic(
        "<fff",
        uuid=PhysBrykService.physbryk_service_uuid(0x101),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    
    # Tuple (x, y, z) float gyroscope values, in rad/s
    gyro = StructCharacteristic(
        "<fff",
        uuid=PhysBrykService.physbryk_service_uuid(0x102),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )

    # magnetometer 0200
    magnetic_enabled = Uint8Characteristic(
        uuid = PhysBrykService.physbryk_service_uuid(0x200),
        initial_value=1,
    )

    magnetic = StructCharacteristic(
        "<fff",
        uuid=PhysBrykService.physbryk_service_uuid(0x201),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    """Tuple (x, y, z) float magnetometer values, in micro-Teslas (uT)"""

class EMRService(PhysBrykService):  # pylint: disable=too-few-public-methods
    """Light sensor value."""

    uuid = PhysBrykService.physbryk_service_uuid(0x300)

    intensity = FloatCharacteristic(
        # "<f",
        uuid=PhysBrykService.physbryk_service_uuid(0x301),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    """Calculated valuefrom get_lux (float)"""

    spectrum = StructCharacteristic(
        "<ffff",
        uuid=PhysBrykService.physbryk_service_uuid(0x302),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    """Tuple (r, g, b, c) red/green/blue/clear color values, each in range 0-65535 (16 bits)"""

    proximity = Uint16Characteristic(
        # "<H",
        uuid=PhysBrykService.physbryk_service_uuid(0x303),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    """
    A higher number indicates a closer distance to the sensor.
    The value is unit-less.
    """

    measurement_period = PhysBrykService.measurement_period_charac()
    """Initially 1000ms."""

    @classmethod
    def get_lux(cls, color_data):
        """Calculate ambient light values"""
        #   This only uses RGB ... how can we integrate clear or calculate lux
        #   based exclusively on clear since this might be more reliable?
        r, g, b, c = color_data
        lux = (-0.32466 * r) + (1.57837 * g) + (-0.73191 * b)
        return lux

class BatteryService(PhysBrykService):  # pylint: disable=too-few-public-methods
    """Random Data values."""

    uuid = PhysBrykService.physbryk_service_uuid(0x0000)

    voltage = FloatCharacteristic(
        # "<f",
        uuid=PhysBrykService.physbryk_service_uuid(0x0001),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    """Voltage level (float)"""

    @classmethod 
    def get_voltage(cls, battery_sensor):
        """Calculates the voltage from the reading of the on board battery sensor."""
        return (battery_sensor.value * 3.3) / 65536 * 2

    measurement_period = PhysBrykService.measurement_period_charac()
    """Initially 1000ms."""

class DummyService(PhysBrykService):  # pylint: disable=too-few-public-methods
    """Random Data values."""

    uuid = PhysBrykService.physbryk_service_uuid(0x1000)

    value = Int16Characteristic(
        # "<h",
        uuid=PhysBrykService.physbryk_service_uuid(0x1001),
        properties=(Characteristic.READ | Characteristic.NOTIFY),
        write_perm=Attribute.NO_ACCESS,
    )
    """Tuple (x, y, z) random values between 1 and 100"""

    # measurement_period = PhysBrykService.measurement_period_charac()
    """Initially 1000ms."""

class DummySensor(object):
    """Creates a dummy sensor which generates a tuple of 3 random numbers.
    """

    def __init__(self, likes_spam=False):
        self.name = "Dummy_Sensor"
        self.value = ()
        self.update()

    def update(self):
        """updates all the sensor values
        """
        self.value = rn.randrange(256)


def main():
    DEBUG = True
    BOARD = True #flag indicating whether attached to a board.

    try:
        import board
    except NotImplementedError:
        # no board attached so mock sensors, services etc
        import mock as mk
        print('No valid board. Using mock sensors and services')
        BOARD = False

    # sensors
    import adafruit_lsm6ds.lsm6ds33 # motion
    import adafruit_lis3mdl # magnetometer
    import adafruit_apds9960.apds9960 # EMR

    import time
    

    dummy_sensor = DummySensor()

    if BOARD: # valid board present use real sensors
        import analogio

        battery = analogio.AnalogIn(board.VOLTAGE_MONITOR)
        motion = adafruit_lsm6ds.lsm6ds33.LSM6DS33(board.I2C())
        magnet = adafruit_lis3mdl.LIS3MDL(board.I2C())
        emr = adafruit_apds9960.apds9960.APDS9960(board.I2C())
        # emr.enable_proximity = True
        emr.enable_color = True

        
        # Create and initialize the available services.
        ble = BLERadio()
        battery_svc = BatteryService()
        motion_svc = MotionService()
        magnet_svc = MagnetService()
        emr_svc = EMRService()
        dummy_svc = DummyService()
        adv = PhysBrykServerAdvertisement()

    else: #use mock sensors and services
        
        # Accelerometer and gyro
        motion = mk.Sensor()
        magnet = mk.Sensor()
        emr = mk.Sensor()
        battery = mk.Sensor()

        ble = mk.Service()
        battery_svc = mk.Service()
        motion_svc = mk.Service()
        magnet_svc = mk.Service()
        emr_svc = mk.Service()
        dummy_svc = mk.Service()
        adv = mk.Service()

    ble.name = "PhysBryk_Alpha"
    
    last_update = 0
    
    while True:
        # Advertise when not connected.
        ble.start_advertising(adv)
        if DEBUG: print('Connecting...')
        while not ble.connected:
            pass
        ble.stop_advertising()
        if DEBUG:
                print('Connected!')
        
        while ble.connected:
            now_msecs = time.monotonic_ns() // 1000000  # pylint: disable=no-member

            if now_msecs - last_update >= MEASUREMENT_PERIOD:
                battery_svc.voltage = battery_svc.get_voltage(battery)
                motion_svc.acceleration = motion.acceleration # m/s/s
                motion_svc.gyro = motion.gyro # rad/s
                magnet_svc.magnetic = magnet.magnetic # microT

                emr_svc.intensity = emr_svc.get_lux(emr.color_data)
                emr_svc.spectrum = emr.color_data
                emr_svc.proximity = emr.proximity
                dummy_svc.value = 42
                dummy_sensor.update()
                last_update = now_msecs

                if DEBUG:
                    print(f'motion acceleration: {motion_svc.acceleration}')
                    print(f'motion gyro: {motion_svc.gyro}')
                    print(f'magnet magnet: {magnet_svc.magnetic}')
                    print(f'emr intensity: {emr_svc.intensity}')
                    print(f'emr spectrum: {emr_svc.spectrum}')
                    print(f'emr proximity: {emr_svc.proximity}')
                    print(f'battery: {battery_svc.voltage}')
                    print(f'dummy: {dummy_svc.value}')
                if not BOARD:
                    for s in mk.sensors: s.update()



if __name__ == "__main__":
    main()

