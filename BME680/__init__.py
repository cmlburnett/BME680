"""
Implementation of float algorithm in calculating pressure, temperature, and humidity from BME680 readings.
Gas features not implemented.
This is not an I2C/SPI implementation to interact with the BME680 chip itself, this is the heavy float implementation to be done on a desktop.
Calculate_PHT assumes you have the raw data from the BME680 converted into int() types (step 1 & 2 below are not implemented here).

Example data calculation:

	1) Register reads in hex values:
		Pressure
			BME680[0x1F]		4F
			BME680[0x20]		28
			BME680[0x21]		A0

		Temperature
			BME680[0x22]		77
			BME680[0x23]		B6
			BME680[0x24]		D0

		Humidity
			BME680[0x25]		49
			BME680[0x26]		D9

	2) Converting to decimal (registers are little endian and lower nibble of 0x21 and 0x24 are thrown away, hence the shift):
		P		(0x4F28A0 >> 4) == 0x4F28A == 324234
		T		(0x77B6D0 >> 4) == 0x77B6D == 490349
		H		0x49D9 == 18905

	3) Raw ADC values from BME680 as determined by unpacking the registers as done above:
		P		324234
		H		18905
		T		490349

	Calibration constants on my BME680:
		G1		-19
		G2		-12505
		G3		18
		H1		668
		H2		1030
		H3		0
		H4		45
		H5		20
		H6		120
		H7		-100
		P1		37284
		P10		30
		P2		-10577
		P3		88
		P4		8054
		P5		-122
		P6		30
		P7		52
		P8		-3895
		P9		-2085
		T1		26268
		T2		26341
		T3		3
	
	4) This results in the following float values per Calculate_PHT()
		P		99245.89
		H		42.019
		T		22.0

	Thus, the pressure is 99245 pascals, 42.02% relative humidity, and 22.0 Celcius.

	5) Further, from the other helper functions below:
		Qa					0.0064102890625
		STP correction		0.90647187859289
		Psat				2634.79310887939
		Pvap				1107.11371642003
		Hvap				2259.50610448612
"""

import math

class BME680:
	@staticmethod
	def Calculate_PHT(P, H, T, T1,T2,T3, P1,P2,P3,P4,P5,P6,P7,P8,P9,P10, H1,H2,H3,H4,H5,H6,H7, G1,G2,G3):
		"""
		Implementation derived from datasheet 1.3.
		Everything is done as a native float in native Python.

		All data supplied should be in float.

		Returns a tuple of pressure, humidity, and temperature rounded to significant digits per accuracy of the datasheet.
		"""

		# Temperature calculation
		var1 = ((T / 16384.0) - (T1 / 1024.0)) * T2
		var2 = (((T / 131072.0) - (T1 / 8192.0)) * ((T / 131072.0) - (T1 / 8192.0))) * (T3 * 16.0)
		t_fine = var1 + var2
		temp_comp = t_fine / 5120.0

		# Pressure calculation
		var1 = (t_fine / 2.0) - 64000.0
		var2 = var1 * var1 * (P6 / 131072.0)
		var2 = var2 + (var1 * P5 * 2.0)
		var2 = (var2 / 4.0) + (P4 * 65536.0)
		var1 = (((P3 * var1 * var1) / 16384.0) + (P2 * var1)) / 524288.0
		var1 = (1.0 + (var1 / 32768.0)) * P1
		press_comp = 1048576.0 - P
		press_comp = ((press_comp - (var2 / 4096.0)) * 6250.0) / var1
		var1 = (P9 * press_comp * press_comp) / 2147483648.0
		var2 = press_comp * (P8 / 32768.0)
		var3 = (press_comp / 256.0) * (press_comp / 256.0) * (press_comp / 256.0) * (P10 / 131072.0)
		press_comp = press_comp + (var1 + var2 + var3 + (P7 * 128.0)) / 16.0

		# Humidity calculation
		var1 = H - ((H1 * 16.0) + ((H3 / 2.0) * temp_comp))
		var2 = var1 * ((H2 / 262144.0) * (1.0 + ((H4 / 16384.0) * temp_comp) + ((H5 / 1048576.0) * temp_comp * temp_comp)))
		var3 = H6 / 16384.0
		var4 = H7 / 2097152.0
		hum_comp = var2 + ((var3 + (var4 * temp_comp)) * var2 * var2)

		return (round(press_comp,2),round(hum_comp,3),round(temp_comp,2))

	@staticmethod
	def Calculate_Psat(Tfloat):
		"""
		Calculates the water vapor saturation in air for temperatures between 0 and 100 Celcius.
		Returns pressure in Pascals.

		See https://en.wikipedia.org/wiki/Antoine_equation for the Antoine equation and origin of constants used here.
		"""
		# Antoine equation for vapor pressure in saturated are (ie, relative humidity = 100%
		# Constant 133.322 Pa/mmHg is unit conversion constant
		return math.pow(10.0, 8.07131 - (1730.63/(233.426+Tfloat))) * 133.322

	@staticmethod
	def Calculate_Pvap(Psat, Hfloat):
		"""
		Calculates the water vapor pressure for air with a given saturation pressure (see Calculate_Psat).
		By definition, relative humidity is the ratio of Pvap to Psat and Hfloat is the relativity humidity from 0 to 100 as a float.

		Returns the water vapor pressure in same units as Psat (Pascals in this module).
		"""

		return Psat * (Hfloat/100.0)

	@staticmethod
	def Calculate_Qa(Tfloat, flow):
		"""
		Calculates the heat enthalpy of air at temperature T in Kelvin (so add 273.15 to the provided value in Celcius), 29.19 is Cpm J/mol-K, and 1344000 is a unit conversion mL-sec/mol-min
		See https://en.wikipedia.org/wiki/Enthalpy_of_vaporization for Hvap

		Tfloat in Celcius, flow in mL/min, and returned is J/s or Watts.
		"""
		return (Tfloat+273.15)*29.19*flow/1344000.0

	@staticmethod
	def Calculate_STP_correction(Pfloat, Tfloat):
		"""
		Calculates the STP correction factor for temperature and pressure given to 273.15 K (0 Celcius) and 1 atm (101325 Pa).
		"""
		# STP correction factor (multiply by flow rate at this pressure and temperature to get STP-corrected flow rate
		return (Pfloat/101325.0)*(273.15/(Tfloat+273.15))

	@staticmethod
	def Calculate_Hvap(Pfloat):
		"""
		Calculate the heat of vaporization of water at the given pressure.
		This is a linear interpolation between (91192.5 Pa, 2265.65 J/g) and (101325 Pa, 2257.92 J/g) which is approximately 2260.4 J/g at room temperatures.
		Returned is heat of vaporization in J/g.
		"""
		return 2335.22 - (0.000762892*Pfloat)
	

