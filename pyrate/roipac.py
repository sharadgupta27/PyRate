'''
Library/script to convert ROIPAC headers to ESRI's BIL format.

GDAL lacks a driver to parse ROIPAC headers. This module translates ROIPAC
headers into ESRI's BIL format, which is supported by GDAL. A basic command line
interface is provided for testing purposes. 

The types of ROIPAC files/data used in PyRate are:
* Interferograms: a .unw 32 bit float data file, with a .rsc resource/header.
The binary data is assumed to contain 2 bands, amplitude and phase.

* DEM: with a .unw 16 bit signed int binary data file, and a .rsc header
There is only a single height band for the binary data.

* TODO: describe incidence files, and any others.   


There may be differences with the .rsc file content, with short and long forms.
The short form has 7 fields, covering raster size, location and wavelength. The
longer form can have up to 40 fields (see the test data for examples). PyRate
attempts to handle both forms of header. 

Created on 12/09/2012
@author: Ben Davies, NCI
         ben.davies@anu.edu.au
'''

import os, re, datetime


# ROIPAC RSC header file constants
WIDTH = "WIDTH"
FILE_LENGTH = "FILE_LENGTH"
XMIN = "XMIN"
XMAX = "XMAX"
YMIN = "YMIN"
YMAX = "YMAX"
X_FIRST = "X_FIRST"
X_STEP = "X_STEP"
X_UNIT = "X_UNIT"
Y_FIRST = "Y_FIRST"
Y_STEP = "Y_STEP"
Y_UNIT = "Y_UNIT"
TIME_SPAN_YEAR = "TIME_SPAN_YEAR"

# Old ROIPAC headers (may not be needed)
RLOOKS = "RLOOKS"
ALOOKS = "ALOOKS"
COR_THRESHOLD = "COR_THRESHOLD"
ORBIT_NUMBER = "ORBIT_NUMBER"
VELOCITY = "VELOCITY"
HEIGHT = "HEIGHT"
EARTH_RADIUS = "EARTH_RADIUS"
WAVELENGTH = "WAVELENGTH"
DATE = "DATE"
DATE12 = "DATE12"
HEADING_DEG = "HEADING_DEG"
RGE_REF1 = "RGE_REF1"
LOOK_REF1 = "LOOK_REF1"
LAT_REF1 = "LAT_REF1"
LON_REF1 = "LON_REF1"
RGE_REF2 = "RGE_REF2"
LOOK_REF2 = "LOOK_REF2"
LAT_REF2 = "LAT_REF2"
LON_REF2 = "LON_REF2"
RGE_REF3 = "RGE_REF3"
LOOK_REF3 = "LOOK_REF3"
LAT_REF3 = "LAT_REF3"
LON_REF3 = "LON_REF3"
RGE_REF4 = "RGE_REF4"
LOOK_REF4 = "LOOK_REF4"
LAT_REF4 = "LAT_REF4"
LON_REF4 = "LON_REF4"

# DEM specific
Z_OFFSET = "Z_OFFSET"
Z_SCALE = "Z_SCALE"
PROJECTION = "PROJECTION"
DATUM = "DATUM"

# custom header aliases
MASTER = "MASTER"
SLAVE = "SLAVE"
X_LAST = "X_LAST"
Y_LAST = "Y_LAST"


# store type for each of the header items
INT_HEADERS = [WIDTH, FILE_LENGTH, XMIN, XMAX, YMIN, YMAX, RLOOKS, ALOOKS,
							Z_OFFSET, Z_SCALE ]
STR_HEADERS = [X_UNIT, Y_UNIT, ORBIT_NUMBER, DATUM, PROJECTION ]
FLOAT_HEADERS = [X_FIRST, X_STEP, Y_FIRST, Y_STEP, TIME_SPAN_YEAR, COR_THRESHOLD,
								VELOCITY, HEIGHT, EARTH_RADIUS, WAVELENGTH, HEADING_DEG,
								RGE_REF1, RGE_REF2, RGE_REF3, RGE_REF4,
								LOOK_REF1, LOOK_REF2, LOOK_REF3, LOOK_REF4,
								LAT_REF1, LAT_REF2, LAT_REF3, LAT_REF4,
								LON_REF1, LON_REF2, LON_REF3, LON_REF4]
DATE_HEADERS = [DATE, DATE12]



ROI_PAC_HEADER_FILE_EXT = "rsc"
ROIPAC_HEADER_LEFT_JUSTIFY = 18
PIXELTYPE_INT = 'signedint'
PIXELTYPE_FLOAT = 'float'
PIXEL_TYPE = 'pixeltype'
BYTE_ORDER = 'byteorder'
Y_CORNER = 'yllcorner'
NBANDS = 'nbands'
NODATA = 'nodata'
IS_DEM = 'is_dem'
NBITS = 'nbits'



def filename_pair(base):
	"""Returns tuple of paths: (roi_pac data, roi_pac header file)"""
	b = base.strip()
	return (b, "%s.%s" % (b, ROI_PAC_HEADER_FILE_EXT))


def parse_date(dstr):
	"""Parses ROI_PAC 'yymmdd' or 'yymmdd-yymmdd' to date or date tuple"""
	def to_date(ds):
		year, month, day = [int(ds[i:i+2]) for i in range(0,6,2)]
		year += 1900 if (year <= 99 and year >= 50) else 2000
		return datetime.date(year, month, day)

	if "-" in dstr: # ranged date
		return tuple([to_date(d) for d in dstr.split("-")])
	else:
		return to_date(dstr)


def parse_header(hdr_file):
	"""Parses ROI_PAC header file to a dict"""
	with open(hdr_file) as f:
		text = f.read()

	try:
		lines = [e.split() for e in text.split("\n") if e != ""]
		headers = dict(lines)
	except ValueError:
		msg = "Unable to parse content of %s. Is it a ROIPAC header file?"
		raise RoipacException(msg % hdr_file)

	for k in headers.keys():
		if k in INT_HEADERS:
			headers[k] = int(headers[k])
		elif k in STR_HEADERS:
			headers[k] = str(headers[k])
		elif k in FLOAT_HEADERS:
			headers[k] = float(headers[k])
		elif k in DATE_HEADERS:
			headers[k] = parse_date(headers[k])
		else:
			msg = "Unrecognised header element %s: %s "
			raise RoipacException(msg % (k, headers[k]) )

	# process dates from filename if rsc file doesn't have them (skip for DEMs)
	if not headers.has_key(DATUM):
		if headers.has_key(DATE) is False or headers.has_key(DATE12) is False:
			p = re.compile(r'\d{6}-\d{6}') # match 2 sets of 6 digits separated by '-'
			m = p.search(hdr_file)

			if m:
				s = m.group()
				min_date_len = 13 # assumes "nnnnnn-nnnnnn" format
				if len(s) == min_date_len:
					date12 = parse_date(s)
					headers[DATE] = date12[0]
					headers[DATE12] = date12
			else:
				msg = "Filename does not include master/slave dates: %s"
				raise RoipacException(msg % hdr_file)

		# add master and slave alias headers
		headers[MASTER] = headers[DATE]
		headers[SLAVE] = headers[DATE12][-1]

		# replace timespan as ROI_PAC is ~4 hours different to (slave - master)
		headers[TIME_SPAN_YEAR] = (headers[SLAVE] - headers[MASTER]).days / 365.25

	# add custom X|Y_LAST for convenience
	if not headers.has_key(X_LAST):
		headers[X_LAST] = headers[X_FIRST] + (headers[X_STEP] * (headers[WIDTH]))
	if not headers.has_key(Y_LAST):
		headers[Y_LAST] = headers[Y_FIRST] + (headers[Y_STEP] * (headers[FILE_LENGTH]))

	return headers


def translate_header(hdr, dest=None):
	"""
	Converts ROI_PAC header files to equivalent ESRI BIL/GDAL EHdr format. This
	allows GDAL to recognise and read ROIPAC datasets.
	
	hdr: path to .rsc header file.
	dest: path to save new header to, if None, defaults to 'base_file_name.hdr'
	"""
	if os.path.isfile(hdr) or os.path.islink(hdr):
		H = parse_header(hdr)
		H[IS_DEM] = H.has_key(DATUM)

		if dest is None:
			# determine default destination file
			if H[IS_DEM]:
				try:
					# assumes ROIPAC uses filename.dem & filename.dem.rsc
					i = hdr.index("dem.rsc")
					dest = hdr[:i] + "hdr"
				except ValueError:
					# DEM probably not from ROIPAC
					msg = "Unrecognised file naming pattern for %s"
					raise RoipacException(msg % hdr)
			else:
				i = max(hdr.rfind("unw.rsc"), hdr.rfind("tif.rsc"))
				if i > 0:
					dest = hdr[:i] + "hdr"
				else:
					msg = "Unrecognised file naming pattern for %s"
					raise RoipacException(msg % hdr)
	else:
		raise IOError("%s not a valid header file" % hdr)

	# calc coords of lower left corner
	yllcorner = H[Y_FIRST] + (H[FILE_LENGTH] * H[Y_STEP])
	if yllcorner > 90 or yllcorner < -90:
		raise RoipacException("Invalid Y latitude for yllcorner: %s" % yllcorner)
	
	H[Y_CORNER] = yllcorner 

	H[PIXEL_TYPE] = PIXELTYPE_INT if H[IS_DEM] else PIXELTYPE_FLOAT
	H[NBITS] = 16 if H[IS_DEM] else 32
	if not H[IS_DEM]:
		H[NBANDS] = 2
		
	H[BYTE_ORDER] = 'lsb'
	H[NODATA] = 0

	return write_bil_header(dest, H)


def write_bil_header(dest, H):
	'''TODO'''

	# create ESRI BIL format header, using ROIPAC defaults
	# TODO: ROIPAC uses 0 for phase NODATA, which isn't quite correct. Use zero
	# for now to allow GDAL to recognise NODATA cells
	
	# TODO: could generalise with writing key: value, using manually ordered keys
	
	with open(dest, "w") as f:
		f.write("ncols %s\n" % H[WIDTH])
		f.write("nrows %s\n" % H[FILE_LENGTH])

		# handle cells with different dimensions (square & non-square)
		if H[X_STEP] == abs(H[Y_STEP]):
			f.write("cellsize %s\n" % H[X_STEP])
		else:
			f.write("xdim %s\n" % H[X_STEP])
			# GDAL reads zeros if ydim is negative
			f.write("ydim %s\n" % abs(H[Y_STEP]) )

		f.write("xllcorner %s\n" % H[X_FIRST])
		f.write("yllcorner %s\n" % H[Y_CORNER])
		f.write("byteorder %s\n" % H[BYTE_ORDER])

		if not H[IS_DEM]:
			f.write("nodata %s\n" % H[NODATA])
			f.write("layout bil\n") # 1 band DEM doesn't interleave data
			f.write("nbands %s\n" % H[NBANDS])  # number of bands

		# ROIPAC DEMs are 16 bit signed ints, phase layers are 32 bit floats
		f.write("nbits %s\n" % H[NBITS])
		f.write("pixeltype %s\n" % H[PIXEL_TYPE])

	return dest


def write_roipac_header(params, dest_path):
	"""Writes ROIPAC format header given a dict of parameters"""
	with open(dest_path, 'w') as dest:
		for i in params.items():
			line = i[0].ljust(ROIPAC_HEADER_LEFT_JUSTIFY) + str(i[1]) + "\n"
			dest.write(line)


class RoipacException(Exception):
	pass


if __name__ == '__main__':
	import sys
	usage = "Usage: roipac.py [ROIPAC file] [... ROIPAC file]\n" 
	if len(sys.argv) < 2:
		sys.stderr.write(usage)
		sys.exit()

	for path in sys.argv[1:]:
		try:
			translate_header(path)
		except Exception as ex:
			sys.exit(ex.message)
