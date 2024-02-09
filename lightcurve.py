import requests
import xml.etree.ElementTree as ET
from astropy.coordinates import SkyCoord
import numpy as np
import os
import tarfile
from astropy.io import fits
import matplotlib.pyplot as plt
from astroquery.mast import Catalogs

class lightcurve:
    def __init__(self, ra=None, dec=None, target_name=None, radius=None):
        self.ra = ra
        self.dec = dec
        self.target_name = target_name
        self.radius = radius
        self.detuid = None
        self.separation = None

    def get_coordinates(self):
        if self.ra and self.dec:
            return self.ra, self.dec
        elif self.target_name:
            # Query the target name to obtain RA and DEC using a service (e.g., SIMBAD)
            catalogData = Catalogs.query_object(self.target_name, catalog = "TIC")
            ra = catalogData[0]['ra']
            dec = catalogData[0]['dec']
            return ra, dec
        else:
            print("Error: No coordinates or target name provided.")
            return None, None

    def extract_tar_LC(self, tar_file, extract_dir, file_name):
        with tarfile.open(tar_file, 'r:xz') as tar:
            for member in tar.getmembers():
                if "020_LightCurve" in member.name:# and file_name[5:11] in member.name:
                    tar.extract(member, path=extract_dir)
                    return os.path.join(extract_dir, member.name)

    def cone_search(self):
        self.ra, self.dec = self.get_coordinates()
        if self.ra is not None and self.dec is not None:
            url = "https://erosita.mpe.mpg.de/dr1/erodat/catalogue/SCS?CAT={CATALOGUE}&RA={RA}&DEC={DEC}&SR={RADIUS}&VERB={VERBOSITY}"
            url = url.format(CATALOGUE='DR1_Main', RA=self.ra, DEC=self.dec, RADIUS=self.radius, VERBOSITY=1)

            response = requests.get(url)

            if response.status_code == 200:
                return response.content
            else:
                print("Error:", response.status_code, response.reason)
                return None
        else:
            return None

    def parse_xml_data(self, xml_data):
        if xml_data:
            root = ET.fromstring(xml_data)
            trs = root.findall('.//TR')

            self.detuid = []
            self.separation = []

            for tr in trs:
                td_elements = tr.findall('TD')
                self.detuid.append(td_elements[1].text)
                self.separation.append(SkyCoord(ra=float(td_elements[2].text), dec=float(td_elements[3].text), unit='deg').separation(SkyCoord(ra=self.ra, dec=self.dec, unit='deg')).deg)

            return self.detuid[np.argmin(self.separation)]
        else:
            print("Target not found in eROSITA DR1!")
            return None

    def download_file(self, url, file_name, product_dir):

        # Create the directory if it doesn't exist
        if not os.path.exists(product_dir):
            os.makedirs(product_dir)

        file_path = os.path.join(product_dir, file_name)

        if file_name not in os.listdir(product_dir):
            os.system('cd {} && curl -O -L {}'.format(product_dir, url.format(file_path)))

            # Extract LC from the downloaded tar file
            fits = self.extract_tar_LC(file_path, product_dir, file_name)
            print(fits)

        else:
            print('Files are already downloaded.')

            # Extract LC from the downloaded tar file
            fits = self.extract_tar_LC(file_path, product_dir, file_name)

        return fits

    def plotter(self, fits_path):
        with fits.open(fits_path) as hdul:
            sec2day = 1.15741e-5
            TIME=hdul[1].data.TIME*sec2day
            RATE_1=(hdul[1].data.RATE)[:,0] #0.2-0.6 KeV
            RATE_2=(hdul[1].data.RATE)[:,1] #0.6-2.3 KeV
            RATE_3=(hdul[1].data.RATE)[:,2] #2.3-5.0 KeV
            RATE_1_ERR=(hdul[1].data.RATE_ERR)[:,0] #0.2-0.6 KeV
            RATE_2_ERR=(hdul[1].data.RATE_ERR)[:,1] #0.6-2.3 KeV
            RATE_3_ERR=(hdul[1].data.RATE_ERR)[:,2] #2.3-5.0 KeV

            plt.figure(1)
            plt.errorbar(TIME, RATE_1, xerr=None, yerr=RATE_1_ERR, label="0.2-0.6 KeV", fmt='o', ls='--', capsize=5, capthick=1)
            plt.errorbar(TIME, RATE_2,  xerr=None, yerr=RATE_2_ERR, label="0.6-2.3 KeV", fmt='o', ls='--', capsize=5, capthick=1)
            plt.errorbar(TIME, RATE_3,  xerr=None, yerr=RATE_3_ERR, label="2.3-5.0 KeV", fmt='o', ls='--', capsize=5, capthick=1)
            plt.legend()
            plt.ylim(0,)
            plt.xlabel('Time (days)')
            plt.ylabel('Count rate (cts/sec)')
            plt.show()
