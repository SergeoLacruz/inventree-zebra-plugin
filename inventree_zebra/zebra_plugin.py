"""
Label printing plugin for InvenTree.

Supports direct printing of labels on label printers
"""
# System stuff
import socket
from datetime import datetime

# Django stuff
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.validators import MaxValueValidator

# InvenTree plugin libs
from plugin import InvenTreePlugin
from plugin.mixins import LabelPrintingMixin, SettingsMixin

# Zebra printer support
import zpl

from .version import ZEBRA_PLUGIN_VERSION


class ZebraLabelPlugin(LabelPrintingMixin, SettingsMixin, InvenTreePlugin):

    AUTHOR = "Michael Buchmann"
    DESCRIPTION = "Label printing plugin for Zebra printers"
    VERSION = ZEBRA_PLUGIN_VERSION
    NAME = "Zebra"
    SLUG = "zebra"
    PUBLISH_DATE = datetime.today().strftime('%Y-%m-%d')
    TITLE = "Zebra Label Printer"

    SETTINGS = {
        'CONNECTION': {
            'name': _('Printer Interface'),
            'description': _('Select local or network printer'),
            'choices': [('local', 'Local printer e.g. USB'),
                        ('network', 'Network printer with IP address')],
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
            'validator': [int, MinValueValidator(0)],
            'default': '9100',
        },
        'LOCAL_IF': {
            'name': _('Local Device'),
            'description': _('Interface of local printer'),
            'default': '/dev/usb/lp0',
        },
        'THRESHOLD': {
            'name': _('Threshold'),
            'description': _('Threshold for converting gray scale to BW (0-255)'),
            'validator': [int, MinValueValidator(0), MaxValueValidator(255)],
            'default': 200,
        },
        'DARKNESS': {
            'name': _('Darkness'),
            'description': _('Darkness of the print out. 0-30'),
            'validator': [int, MinValueValidator(0), MaxValueValidator(30)],
            'default': 20,
        },
        'DPMM': {
            'name': _('Dots per mm'),
            'description': _('The resolution of the printer'),
            'choices': [(8, '8 dots per mm'), (12, '12 dots per mm'), (24, '24 dots per mm')],
            'default': 8,
        },
        'PRINTER_INIT': {
            'name': _('Printer Init'),
            'description': _('Additional ZPL commands sent to the printer. Use carefully!'),
            'default': '~TA000~JSN^LT0^MNW^MTT^PMN^PON^PR2,2^LRN',
        },
    }

    def print_label(self, **kwargs):

        # Read settings
        connection = self.get_setting('CONNECTION')
        interface = self.get_setting('LOCAL_IF')
        port = int(self.get_setting('PORT'))
        threshold = self.get_setting('THRESHOLD')
        dpmm = int(self.get_setting('DPMM'))
        printer_init = self.get_setting('PRINTER_INIT')

        # Extract width (x) and height (y) information.
        width = kwargs['width']
        height = kwargs['height']

        # Select the right printer.
        # This is a multi printer hack. In case the label has an IP address in the metadata
        # the address in the settings is overwritten be the metadata. By this you can
        # specify a separate printer for each label.
        label = kwargs['label_instance']
        try:
            ip_address = label.metadata['ip_address']
        except Exception:
            ip_address = self.get_setting('IP_ADDRESS')
        try:
            darkness = label.metadata['darkness']
        except Exception:
            darkness = self.get_setting('DARKNESS')
        try:
            zpl_template = label.metadata['zpl_template']
        except Exception:
            zpl_template = False

        # From here we need to distinguish between html templates and ZPL templates
        if zpl_template:
            raw_zpl = kwargs['context']['template'].render_as_string(kwargs['item_instance'], None).replace('\n', '')

            # Create the zpl data
            li = zpl.Label(height, width, dpmm)
            li.set_darkness(darkness)
            li.labelhome(0, 0)
            li.zpl_raw(printer_init)
            li.origin(0, 0)
            li.zpl_raw(raw_zpl)
            li.endorigin()
        else:
            # Set the threshold
            label_image = kwargs['png_file']
            fn = lambda x: 255 if x > threshold else 0
            label_image = label_image.convert('L').point(fn, mode='1')

            # Uncomment this if you need the intermediate png file for debugging.
            # label_image.save('/home/user/label.png')

            # Convert image to Zebra zpl
            li = zpl.Label(height, width, dpmm)
            li.set_darkness(darkness)
            li.labelhome(0, 0)
            li.zpl_raw(printer_init)
            li.origin(0, 0)
            li.write_graphic(label_image, width)
            li.endorigin()

        # Uncomment this if you need the intermediate zpl file for debugging.
        # datafile=open('/home/user/label.txt','w')
        # datafile.write(li.dumpZPL())
        # datafile.close()

        # Send the label to the printer
        if (connection == 'local'):
            try:
                printer = open(interface, 'w')
                printer.write(li.dumpZPL())
                printer.close()
            except Exception as error:
                raise ConnectionError('Error connecting to local printer: ' + str(error))
        elif (connection == 'network'):
            try:
                mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                mysocket.settimeout(5)
                mysocket.connect((ip_address, port))
                data = li.dumpZPL()
                mysocket.send(data.encode())
                mysocket.close()
            except Exception as error:
                raise ConnectionError('Error connecting to network printer: ' + str(error))
        else:
            print('Unknown Interface')
