"""
Label printing plugin for InvenTree.
Supports direct printing of labels on label printers
"""
# translation
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.validators import MaxValueValidator

# InvenTree plugin libs
from plugin import InvenTreePlugin
from plugin.mixins import LabelPrintingMixin, SettingsMixin

# Zebra printer support
import zpl
import socket

from inventree_zebra.version import ZEBRA_PLUGIN_VERSION

class ZebraLabelPlugin(LabelPrintingMixin, SettingsMixin, InvenTreePlugin):

    AUTHOR = "Michael Buchmann"
    DESCRIPTION = "Label printing plugin for Zebra printers"
    VERSION = ZEBRA_PLUGIN_VERSION
    NAME = "Zebra"
    SLUG = "zebra"
    TITLE = "Zebra Label Printer"

    SETTINGS = {
        'CONNECTION': {
            'name': _('Printer Interface'),
            'description': _('Select local or network printer'),
            'choices': [('local','Local printer e.g. USB'),('network','Network printer with IP address')],
            'default': 'local',
        },
        'IP_ADDRESS': {
            'name': _('IP Address'),
            'description': _('IP address in case of network printer'),
            'default': '',
        },
        'PORT': {
            'name': _('Port'),
            'description': _('Network port in case of network printer'),
            'default': '9100',
        },
        'LOCAL_IF': {
            'name': _('Local Device'),
            'description': _('Interface of local printer'),
            'default': '/dev/usb/lp0',
        },
        'THRESHOLD': {
            'name': _('Threshold'),
            'description': _('Threshold for converting grayscale to BW'),
            'validator': [int,MinValueValidator(0),MaxValueValidator(255)],
            'default': 200,
        },
        'DARKNESS': {
            'name': _('Darkness'),
            'description': _('Darkness of the print out. 0-30'),
            'validator': [int,MinValueValidator(0),MaxValueValidator(30)],
            'default': 20,
        },
        'XPOS': {
            'name': _('X-Position'),
            'description': _('The X position of the label in mm in case the printer is wider than the label'),
            'validator': [int,MinValueValidator(0),MaxValueValidator(100)],
            'default': 25,
        },
        'WIDTH': {
            'name': _('Width'),
            'description': _('Width of the label in mm'),
            'validator':[int,MinValueValidator(0)],
            'default': 50,
        },
        'HEIGHT': {
            'name': _('Height'),
            'description': _('Height of the label in mm'),
            'validator':[int,MinValueValidator(0)],
            'default': 30,
        },
    }

    def print_label(self, **kwargs):

        # Extract width (x) and height (y) information
        # width = kwargs['width']
        # height = kwargs['height']

        # Read settings
        IPAddress = self.get_setting('IP_ADDRESS')
        Connection = self.get_setting('CONNECTION')
        Interface = self.get_setting('LOCAL_IF')
        Port = self.get_setting('PORT')
        Threshold = self.get_setting('THRESHOLD')
        Width = self.get_setting('WIDTH')
        Height = self.get_setting('HEIGHT')
        Darkness = self.get_setting('DARKNESS')
        xPos = self.get_setting('XPOS')
        label_image = kwargs['png_file']

        fn = lambda x : 255 if x > Threshold else 0
        label_image = label_image.convert('L').point(fn, mode='1')

        # Uncomment this if you want to have in intermetiate png file for debugging. You will find it in src/Inventree
        # label_image.save('label.png')

        # Convert image to Zebra zpl
        l = zpl.Label(Width,Height,8)
        l.set_darkness(Darkness)
        l.origin(xPos, 0)
        l.write_graphic(label_image, Width)
        l.endorigin()

        # Send the label to the printer
        if(Connection=='local'):
            try:
                printer=open(Interface,'w')
                printer.write(l.dumpZPL())
                printer.close()
            except:
                raise ConnectionError('Error connecting to local printer')
        elif(Connection=='network'):    
            try:
                mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                mysocket.connect((IPAddress, int(Port)))
                data=l.dumpZPL()
                mysocket.send(data.encode())
                mysocket.close ()
            except:
                raise ConnectionError('Error connecting to network printer')
        else:
            print('Unknown Interface')
