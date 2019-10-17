from distutils.core import setup

majv = 1
minv = 0

setup(
	name = 'BME680',
	version = "%d.%d" %(majv,minv),
	description = "Implementation of BME680 float algorithm per Bosch's datasheet",
	author = "Colin ML Burnett",
	author_email = "cmlburnett@gmail.com",
	url = "",
	packages = ['BME680'],
	package_data = {'BME680': ['BME680/__init__.py']},
	classifiers = [
		'Programming Language :: Python :: 3.7'
	]
)
