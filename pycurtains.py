#!/usr/bin/env python3
"""
Module Docstring
"""

__author__ = "Richard Miller-Smith"
__version__ = "0.1.0"
__license__ = "MIT"

import argparse
import configparser
import numbers
import os
import sys
import time
from logzero import logger
from astral import Astral
import pytz
from datetime import datetime, timedelta

class PyCurtainConfig:
  def __init__(self, config_path : str):
    self.city = 'London'
    self.dawn_delay = 30 * 60
    self.dusk_delay = -15 * 60
    self.open_cmd = "echo Open"
    self.close_cmd = "echo Close"

    self._parse_config(config_path)

  def _parse_config(self, config_path : str):
    if not os.path.exists(config_path):
      logger.error("Config file '%s' not found"%config_path)
      sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    if 'pycurtains' in config:
      pyc = config['pycurtains']

      for name in self.__dict__:
        if name in pyc:
          if isinstance(self.__dict__[name], numbers.Number):
            self.__dict__[name] = float(pyc[name])
          else:
            self.__dict__[name] = pyc[name]


class PyCurtain:
  def __init__(self, config_path : str):
    self.config = PyCurtainConfig(config_path)

    self.astral = Astral()
    self.city = self.astral[self.config.city]
    logger.info('Information for %s/%s' % (self.city.name, self.city.region))
    logger.info('Latitude: %.02f; Longitude: %.02f' % (self.city.latitude, self.city.longitude))

    self.state = "INIT"
    self.sun = None

    self.last_date = None

    self.dawn = None
    self.dusk = None


  def run(self):
    while True:
      self._poll()
      time.sleep(12)


  def _poll(self):
    dt = self.get_now()

    if self.is_new_day(dt):
      self.sun = None
      self.dawn = None
      self.dusk = None

    if self.sun is None:
      dt = datetime.today()
      dt = pytz.timezone(self.city.timezone).localize(dt)
      self.sun = self.city.sun(date=dt, local=True)
      logger.info(self.sun)

      self.dawn_count = 3
      self.dusk_count = 3

    if self.dawn is None:
      self.dawn = self.sun['dawn'] + timedelta(seconds=self.config.dawn_delay)
      logger.info("Dawn is at %s"%self.dawn)

    if self.dusk is None:
      self.dusk = self.sun['dusk'] + timedelta(seconds=self.config.dusk_delay)
      logger.info("Dusk is at %s"%self.dusk)

    if dt < self.dawn:
      # Pre-dawn
      pass
    elif dt < self.dusk:
      # Post-dawn, Pre-dusk
      if self.dawn_count > 0:
        self._actuate('open')
        self.dawn_count -= 1
    else:
      # Post-dawn, Post-dusk
      if self.dusk_count > 0:
        self._actuate('close')
        self.dusk_count -= 1

  def is_new_day(self, dt):
    date = dt.date()
    new_day = (self.last_date is None) or (self.last_date != date)
    self.last_date = date
    return new_day

  def get_now(self):
    dt = datetime.today()
    dt = pytz.timezone(self.city.timezone).localize(dt)
    return dt

  def _actuate(self, dir):
    cmd = self.config.close_cmd
    if dir == 'open':
      cmd = self.config.open_cmd

    logger.info("Calling %s command [%s]"%(dir, cmd))
    retval = os.system(cmd)
    if retval:
      logger.error("Call to %s failed"%cmd)


def main(args):
    """ Main entry point of the app """
    logger.info("pyCurtains")
    logger.info(args)

    pc = PyCurtain(args.config_path)
    pc.run()

if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()

    # Optional argument which requires a parameter (eg. -d test)
    parser.add_argument("-c", "--config", action="store",
                        dest="config_path", default="/etc/pycurtains.conf")

    # Optional verbosity counter (eg. -v, -vv, -vvv, etc.)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity (-v, -vv, etc)")

    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__))

    args = parser.parse_args()
    main(args)
