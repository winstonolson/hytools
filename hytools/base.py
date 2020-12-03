# -*- coding: utf-8 -*-
"""
Base
"""
from collections import Counter
import os
import numpy as np
import h5py
from .io.envi import parse_envi_header,dtype_dict, envi_read_band
from .io.envi import envi_read_line,envi_read_column,envi_read_chunk


class HyTools:
    """HyTools  class object"""

    def __init__(self):
        """Constructor method
        """
        self.file_type = None
        self.interleave = None
        self.file_name = None
        self.shape = None
        self.lines = None
        self.columns = None
        self.bands = None
        self.wavelengths = None
        self.fwhm = []
        self.bad_bands = []
        self.no_data = None
        self.map_info = None
        self.crs = None
        self.ulx = None
        self.uly = None
        self.dtype = None
        self.data = None
        self.header_dict = None
        self.solar_zn =None
        self.solar_az = None
        self.sensor_zn = None
        self.sensor_az = None
        self.slope = None
        self.aspect = None
        self.transform = None
        self.path_length = None
        self.projection = None
        self.byte_order = None
        self.wavelength_units = None
        self.hdf_obj  = None

    def create_band_bands(self,bad_regions):
        """Create bad bands mask, Good: True, bad : False.

        Args:
            bad_regions (list of lists): start and end values of wavelength
            regions considered bad. Wavelengths should be in the same units as
            data units. ex: [[350,400].....[2450,2500]].

        Returns:
            None.

        """

        bad_bands = []

        for wavelength in self.wavelengths:
            for start,end in bad_regions:
                good = (wavelength >= start) & (wavelength <=end)
            bad_bands.append(good)
        self.bad_bands = np.array(bad_bands)


    def load_data(self, mode = 'r', offset = 0):
        """Load data object to memory.

        Args:
            mode (str, optional): File read mode. Defaults to 'r'.
            offset (int, optional): Offset in bytes. Defaults to 0.

        Returns:
            None.

        """

        if self.file_type  == "envi":
            self.data = np.memmap(self.file_name,dtype = self.dtype, mode=mode, shape = self.shape,offset=offset)
        elif self.file_type  == "neon":
            self.hdf_obj = h5py.File(self.file_name,'r')
            base_key = list(self.hdf_obj.keys())[0]
            self.data = self.hdf_obj[base_key]["Reflectance"]["Reflectance_Data"]

    def close_data(self):
        """Close data object.

        """
        if self.file_type  == "envi":
            del self.data
        elif self.file_type  == "neon":
            self.hdf_obj.close()

    def iterate(self,by,chunk_size= (100,100)):
        """Create data Iterator.

        Args:
            by (str): Dimension along which to iterate: "line","column","band","chunk".
            chunk_size (tuple, optional): Two dimensional chunk size (Y,X).
                                          Applies only when "chunk" selected.
                                          Defaults to (100,100).

        Returns:
            Iterator class object: Data Iterator.

        """

        return Iterator(self,by,chunk_size)

    def wave_to_band(self,wave):
        """Return band index corresponding to input wavelength. Return closest band if
           not an exact match.

        Args:
            wave (float): Wavelength of band to be retrieved in image wavelength units.

        Returns:
            band_num (int): Band index.

        """

        if (wave  > self.wavelengths.max()) | (wave  < self.wavelengths.min()):
            print("Input wavelength outside image range!")
            band_num = None
        else:
            band_num = np.argmin(np.abs(self.wavelengths - wave))
        return band_num

    def get_band(self,index):
        """
        Args:
            index (inr): Zero-indexed band index.

        Returns:
            band (numpy.ndarray): A 2D (lines x columns) array.

        """

        if self.file_type == "neon":
            band =  self.data[:,:,index]
        elif self.file_type == "envi":
            band = envi_read_band(self.data,index,self.interleave)
        return band

    def get_wave(self,wave):
        """Return the band image corresponding to the input wavelength.
        If not an exact match the closest wavelength will be returned.

        Args:
            wave (float): DESCRIPTION.

        Returns:
            band (numpy.ndarray): Band image array (line,columns).

        """

        if (wave  > self.wavelengths.max()) | (wave  < self.wavelengths.min()):
            print("Input wavelength outside wavelength range!")
            band = None
        else:
            band_num = np.argmin(np.abs(self.wavelengths - wave))
            band = self.get_band(band_num)
        return band

    def get_line(self,index):
        """
        Args:
            index (int): Zero-indexed line index.

        Returns:
            line (numpy.ndarray): Line array (columns, bands).

        """

        if self.file_type == "neon":
            line = self.data[index,:,:]
        elif self.file_type == "envi":
            line = envi_read_line(self.data,index,self.interleave)
        return line

    def get_column(self,index):
        """
        Args:
            index (int): Zero-indexed column index.

        Returns:
            column (numpy.ndarray): Column array (lines, bands).

        """

        if self.file_type == "neon":
            column = self.data[:,index,:]
        elif self.file_type == "envi":
            column = envi_read_column(self.data,index,self.interleave)
        return column

    def get_chunk(self,col_start,col_end,line_start,line_end):
        """
        Args:
            col_start (int): Chunk starting column.
            col_end (int): Noninclusive chunk ending column index.
            line_start (int): Chunk starting line.
            line_end (int): Noninclusive chunk ending line index.

        Returns:
            chunk (numpy.ndarray): Chunk array (line_end-line_start,col_end-col_start,bands).

        """

        if self.file_type == "neon":
            chunk = self.data[line_start:line_end,col_start:col_end,:]
        elif self.file_type == "envi":
            chunk =   envi_read_chunk(self.data,col_start,col_end,line_start,line_end,self.interleave)
        return chunk


    def load_obs(self,observables):
        """Map observables to memory.
        """
        if self.file_type == "envi":
            observables = open_envi(observables)
            observables.load_data()
            self.sensor_az = np.radians(observables.get_band(1))
            self.sensor_zn = np.radians(observables.get_band(2))
            self.solar_az = np.radians(observables.get_band(3))
            self.solar_zn = np.radians(observables.get_band(4))
            self.slope = np.radians(observables.get_band(6))
            self.aspect = np.radians(observables.get_band(7))
            observables.close_data()

class Iterator:
    """Iterator class
    """

    def __init__(self,hy_obj,by,chunk_size = None):
        """
        Args:
            hy_obj (Hytools object): Populated Hytools file object.
            by (str): Iterator slice dimension: "line", "column", "band"",chunk".
            chunk_size (tuple, optional): Chunk size. Defaults to None.

        Returns:
            None.

        """

        self.chunk_size= chunk_size
        self.by = by
        self.current_column = -1
        self.current_line = -1
        self.current_band = -1
        self.complete = False
        self.hy_obj = hy_obj

    def read_next(self):
        """ Return next line/column/band/chunk.
        """
        if self.by == "line":
            self.current_line +=1
            if self.current_line == self.hy_obj.lines-1:
                self.complete = True
                subset = None
            if self.hy_obj.file_type == "neon":
                subset =  self.hy_obj.data[self.current_band,:,:]
            else:
                subset =  envi_read_line(self.hy_obj.data,self.current_line,
                                         self.hy_obj.interleave)

        elif self.by == "column":
            self.current_column +=1
            if self.current_column == self.hy_obj.columns-1:
                self.complete = True
            if self.hy_obj.file_type == "neon":
                subset =  self.hy_obj.data[:,self.current_band,:]
            else:
                subset =  envi_read_column(self.hy_obj.data,self.current_column,
                                           self.hy_obj.interleave)

        elif self.by == "band":
            self.current_band +=1
            if self.current_band == self.hy_obj.bands-1:
                self.complete = True
            if self.hy_obj.file_type == "neon":
                subset =  self.hy_obj.data[:,:,self.current_band]
            else:
                subset =  envi_read_band(self.hy_obj.data,self.current_band,
                                         self.hy_obj.interleave)

        elif self.by == "chunk":
            if self.current_column == -1:
                self.current_column +=1
                self.current_line +=1
            else:
                self.current_column += self.chunk_size[1]
            if self.current_column >= self.hy_obj.columns:
                self.current_column = 0
                self.current_line += self.chunk_size[0]

            # Set array indices for current chunk and update current line and column.
            y_start = self.current_line
            y_end = self.current_line + self.chunk_size[0]
            if y_end >= self.hy_obj.lines:
                y_end = self.hy_obj.lines
            x_start = self.current_column
            x_end = self.current_column + self.chunk_size[1]
            if x_end >= self.hy_obj.columns:
                x_end = self.hy_obj.columns

            if self.hy_obj.file_type == "neon":
                subset = self.hy_obj.data[y_start:y_end,x_start:x_end,:]
            else:
                subset =  envi_read_chunk(self.hy_obj.data,x_start,x_end,
                                          y_start,y_end,self.hy_obj.interleave)
            if (y_end == self.hy_obj.lines) and (x_end == self.hy_obj.columns):
                self.complete = True
        return subset

    def reset(self):
        """Reset counters.
        """
        self.current_column = -1
        self.current_line = -1
        self.current_band = -1
        self.complete = False


def open_envi(src_file):
    """Open ENVI formated image file and populate Hytools object.


    Args:
        src_file (str): Pathname of input ENVI image file, header assumed to be located in
        same directory.

    Returns:
        hy_obj (HyTools object): Populated Hytools file object.

    """

    if not os.path.isfile(os.path.splitext(src_file)[0] + ".hdr"):
        print("ERROR: Header file not found.")
        return None

    hy_obj = HyTools()
    hy_obj.file_type = 'envi'

    header_dict = parse_envi_header(os.path.splitext(src_file)[0] + ".hdr")

    hy_obj.lines =  header_dict["lines"]
    hy_obj.columns =  header_dict["samples"]
    hy_obj.bands =   header_dict["bands"]
    hy_obj.interleave =  header_dict["interleave"]
    hy_obj.fwhm =  header_dict["fwhm"]
    hy_obj.wavelengths = header_dict["wavelength"]
    hy_obj.wavelength_units = header_dict["wavelength units"]
    hy_obj.dtype = dtype_dict[header_dict["data type"]]
    hy_obj.no_data = header_dict['data ignore value']
    hy_obj.map_info = header_dict['map info']
    hy_obj.byte_order = header_dict['byte order']
    hy_obj.header_dict =  header_dict

    hy_obj.file_name = src_file

    if isinstance(header_dict['bbl'],np.ndarray):
        hy_obj.bad_bands = np.array([x==1 for x in header_dict['bbl']])

    if header_dict["interleave"] == 'bip':
        hy_obj.shape = (hy_obj.lines, hy_obj.columns, hy_obj.bands)
    elif header_dict["interleave"] == 'bil':
        hy_obj.shape = (hy_obj.lines, hy_obj.bands, hy_obj.columns)
    elif header_dict["interleave"] == 'bsq':
        hy_obj.shape = (hy_obj.bands, hy_obj.lines, hy_obj.columns)
    else:
        print("ERROR: Unrecognized interleave type.")
        hy_obj = None

    if hy_obj.wavelength_units is None:
        print("Wavelength units not specified!")

    # If no_data value is not specified guess using image corners.
    if hy_obj.no_data is None:
        print("No data value specified, guessing.")
        hy_obj.load_data()
        up_l = hy_obj.data[0,0,0]
        up_r = hy_obj.data[0,-1,0]
        low_l = hy_obj.data[-1,0,0]
        low_r = hy_obj.data[-1,-1,0]
        counts = {v: k for k, v in Counter([up_l,up_r,low_l,low_r]).items()}
        hy_obj.no_data = counts[max(counts.keys())]
        hy_obj.close_data()

    del header_dict
    return hy_obj



def open_neon(src_file, no_data = -9999,load_obs = False):
    """Load and parse NEON formated HDF image into a HyTools file object.

    Args:
        src_file (str): pathname of input HDF file.
        no_data (float, optional): No data value. Defaults to -9999.
        load_obs (bool, optional): Map observables to memory. Defaults to False.

    Returns:
        hy_obj (TYPE): DESCRIPTION.

    """

    if not os.path.isfile(src_file):
        print("File not found.")
        return None

    hy_obj = HyTools()
    hy_obj.file_type = 'neon'
    hdf_obj = h5py.File(src_file,'r')

    base_key = list(hdf_obj.keys())[0]
    metadata = hdf_obj[base_key]["Reflectance"]["Metadata"]
    data = hdf_obj[base_key]["Reflectance"]["Reflectance_Data"]

    hy_obj.projection = metadata['Coordinate_System']['Coordinate_System_String'][()].decode("utf-8")
    hy_obj.map_info = metadata['Coordinate_System']['Map_Info'][()].decode("utf-8").split(',')
    hy_obj.transform = (float(hy_obj.map_info [3]),float(hy_obj.map_info [1]),0,float(hy_obj.map_info [4]),0,-float(hy_obj.map_info [2]))
    hy_obj.fwhm =  metadata['Spectral_Data']['FWHM'][()]
    hy_obj.wavelengths = metadata['Spectral_Data']['Wavelength'][()]
    hy_obj.wavelength_units = metadata['Spectral_Data']['Wavelength'].attrs['Units']
    hy_obj.lines = data.shape[0]
    hy_obj.columns = data.shape[1]
    hy_obj.bands = data.shape[2]
    hy_obj.no_data = no_data
    hy_obj.file_name = src_file

    if load_obs:
        hy_obj.solar_zn = np.ones((hy_obj.lines, hy_obj.columns)) * np.radians(metadata['Logs']['Solar_Zenith_Angle'][()])
        hy_obj.solar_az = np.ones((hy_obj.lines, hy_obj.columns)) * np.radians(metadata['Logs']['Solar_Azimuth_Angle'][()])
        hy_obj.sensor_zn = np.radians(metadata['to-sensor_Zenith_Angle'][()])
        hy_obj.sensor_az = np.radians(metadata['to-sensor_Azimuth_Angle'][()])
        hy_obj.slope = np.radians(metadata['Ancillary_Imagery']['Slope'][()])
        hy_obj.aspect =  np.radians(metadata['Ancillary_Imagery']['Aspect'][()])
        hy_obj.path_length = metadata['Ancillary_Imagery']['Path_Length'][()]

    hdf_obj.close()
    return hy_obj
