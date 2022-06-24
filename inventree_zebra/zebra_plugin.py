"""
Label printing plugin for InvenTree.
Supports direct printing of labels on label printers
"""
# translation
from django.utils.translation import ugettext_lazy as _

# InvenTree plugin libs
from plugin import IntegrationPluginBase
from plugin.mixins import LabelPrintingMixin, SettingsMixin

# Zebra printer support
import zpl
import socket

from inventree_zebra.version import ZEBRA_PLUGIN_VERSION

class ZebraLabelPlugin(LabelPrintingMixin, SettingsMixin, IntegrationPluginBase):

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
        label_image = kwargs['png_file']

        # Uncomment this if you want to have in intermetiate png file for debugging. You will find it in src/Inventree
#        label_image.save('label.png')

        # Convert image to Zebra zpl
        
        l = zpl.Label(50,30,8)
        l.origin(0, 0)
        l.write_graphic(label_image, 50)
        l.endorigin()

        # Send the label to the printer
        if(Connection=='local'):
            try:
                printer=open(Interface,'w')
                printer.write(l.dumpZPL())
                printer.close()
            except:
                print('Error: Printer not available')
                raise ConnectionError('Error connecting to local printer')
        elif(Connection=='network'):    
            try:
                mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                mysocket.connect((IPAddress, int(Port)))
                data=l.dumpZPL()
                mysocket.send(data.encode())
                mysocket.close ()
            except:
                print("Error with the connection")
                raise ConnectionError('Error connecting to network printer')
        else:
            print('Unknown Interface')
