"""
Label printing plugin for InvenTree.

Supports direct printing of labels on label printers
"""
# System stuff
import socket

# Django stuff
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.validators import MaxValueValidator
from django.core.files.base import ContentFile
from django_q.models import Task
from rest_framework import serializers

# InvenTree plugin libs
from plugin import InvenTreePlugin
from plugin.mixins import LabelPrintingMixin, SettingsMixin, ScheduleMixin
from report.models import LabelTemplate
# Zebra printer support
import zpl

from .version import ZEBRA_PLUGIN_VERSION
from .request_wrappers import Wrappers


class ZebraLabelPlugin(LabelPrintingMixin, SettingsMixin, InvenTreePlugin, ScheduleMixin):

    AUTHOR = "Michael Buchmann"
    DESCRIPTION = "Label printing plugin for Zebra printers"
    VERSION = ZEBRA_PLUGIN_VERSION
    NAME = "Zebra labels"
    SLUG = "zebra"
    PUBLISH_DATE = "2024-12-20"
    TITLE = "Zebra Label Printer"
    preview_result = ''

#    BLOCKING_PRINT = True
    SETTINGS = {
        'CONNECTION': {
            'name': _('Printer Interface'),
            'description': _('Select local or network printer'),
            'choices': [('local', 'Local printer e.g. USB'),
                        ('network', 'Network printer with IP address'),
                        ('preview', 'ZPL preview using labelary.com API')],
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
            'choices': [('8', '8 dots per mm'), ('12', '12 dots per mm'), ('24', '24 dots per mm')],
            'default': '8',
        },
        'PRINTER_INIT': {
            'name': _('Printer Init'),
            'description': _('Additional ZPL commands sent to the printer. Use carefully!'),
            'default': '~TA000~JSN^LT0^MNW^MTT^PMN^PON^PR2,2^LRN',
        },
        'ENABLE_PRINTER_INFO': {
            'name': 'Get Printer Info',
            'description': 'Collect status info from all IP printers regularly',
            'default': True,
            'validator': bool,
        },
    }

    SCHEDULED_TASKS = {
        'member': {
            'func': 'ping_printer',
            'schedule': 'I',
            'minutes': 1,
        }
    }

    def get_settings_content(self, request):

        table_rows = ''
        try:
            t = Task.objects.filter(group='plugin.zebra.member')[0]
            for printer in t.result:
                table_rows = table_rows + f"""<tr><td>{printer.get('interface')}</td>
                                                <td>{printer.get('printer_model')}</td>
                                                <td>{printer.get('printer_name')}</td>
                                                <td>{printer.get('sw_version')}</td>
                                                <td>{printer.get('dpi')}</td>
                                                <td>{printer.get('paper_out')}</td>
                                                <td>{printer.get('head_up')}</td>
                                                <td>{printer.get('total_print_length')}</td>
                                                <td>{printer.get('memory')}</td>
                                            </tr>"""
        except Exception:
            pass
        return f"""
        <h4>Printer Status:</h4>
        <table class='table table-condensed'>
            <tr>
                <th> Interface </th>
                <th> Printer Model </th>
                <th> Printer Name </th>
                <th> SW Version </th>
                <th> dpi </th>
                <th> Paper out </th>
                <th> Head Up </th>
                <th> Print Length </th>
                <th> Memory </th></tr>
            <tr>
            {table_rows}
        </table>
        """

    class PrintingOptionsSerializer(serializers.Serializer):
        number_of_labels = serializers.IntegerField(max_value=99, min_value=1, default=1)

    def print_label(self, **kwargs):

        # Read settings
        connection = self.get_setting('CONNECTION')
        interface = self.get_setting('LOCAL_IF')
        port = int(self.get_setting('PORT'))
        threshold = self.get_setting('THRESHOLD')
        printer_init = self.get_setting('PRINTER_INIT')

        # Extract width (x) and height (y) information.
        width = kwargs['width']
        height = kwargs['height']
        number_of_labels = kwargs['printing_options']['number_of_labels']

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
            dpmm = int(label.metadata['dpmm'])
        except Exception:
            dpmm = int(self.get_setting('DPMM'))
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
            li.zpl_raw('^PQ' + str(number_of_labels))
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
            li.zpl_raw('^PQ' + str(number_of_labels))
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
                self.preview_result = None
            except Exception as error:
                raise ConnectionError('Error connecting to local printer: ' + str(error))
        elif (connection == 'network'):
            try:
                mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                mysocket.settimeout(10.0)
                mysocket.connect((ip_address, port))
                data = li.dumpZPL()
                mysocket.sendall(data.encode())
                mysocket.close()
                self.preview_result = None
            except Exception as error:
                raise ConnectionError('Error connecting to network printer: ' + str(error))
        elif (connection == 'preview'):
            width_inch = round(width / 25.4, 2)
            height_inch = round(height / 25.4, 2)
            url = f'https://api.labelary.com/v1/printers/{dpmm}dpmm/labels/{width_inch}x{height_inch}/0'
            header = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'application/pdf'}
            response = Wrappers.post_request(self, li.dumpZPL(), url, header)
            try:
                status_code = response.status_code
            except Exception:
                status_code = 0
            if status_code == 200:
                self.preview_result = ContentFile(response.content, 'label.pdf')
            elif status_code == 0:
                self.preview_result = ContentFile(f'Request error: {response}', 'label.html')
            else:
                self.preview_result = ContentFile(f'Labalary API Error: {response.content}', 'label.html')
        else:
            print('Unknown Interface')

    def get_generated_file(self, **kwargs):
        return self.preview_result

# -----------------------------------------------------------------------------
    def ping_printer(self, *args, **kwargs):

        printer_data = []
        if not self.get_setting('ENABLE_PRINTER_INFO'):
            return (printer_data)
        connection = self.get_setting('CONNECTION')
        if (connection == 'network'):
            port = int(self.get_setting('PORT'))
            all_printer = self.collect_all_ipprinter()
            for printer in all_printer:
                data = self.get_all_printer_data(printer, port)
                printer_data.append(data)
            return (printer_data)
        elif (connection == 'local'):
            interface = self.get_setting('LOCAL_IF')
            printer_data.append(self.get_all_printer_data(interface))
            return (printer_data)
        else:
            printer_data.append({'interface': 'preview', 'printer_model': 'Preview printer skipped'})
            return (printer_data)

# ----------------------------------------------------------------------------
    def get_all_printer_data(self, printer, port=None):

        if port is None:
            result = self.get_printer_data(printer, '~HI')
            result_hs = self.get_printer_data(printer, '~HS')
            printer_name = self.get_printer_data(printer, '! U1 getvar "device.friendly_name"\r\n')
            head_up = self.get_printer_data(printer, '! U1 getvar "head.latch"\r\n')
            total_print_length = self.get_printer_data(printer, '! U1 getvar "odometer.total_print_length"\r\n')
        else:
            result = self.get_ipprinter_data(printer, port, '~HI')
            result_hs = self.get_ipprinter_data(printer, port, '~HS')
            printer_name = self.get_ipprinter_data(printer, port, '! U1 getvar "device.friendly_name"\r\n')
            head_up = self.get_ipprinter_data(printer, port, '! U1 getvar "head.latch"\r\n')
            total_print_length = self.get_ipprinter_data(printer, port, '! U1 getvar "odometer.total_print_length"\r\n')
        try:
            result.split(',')[1]
            result_hs.split(',')[1]
        except Exception:
            printer_data = {'interface': printer, 'printer_model': f'HI:{result}, HS:{result_hs}'}
            return (printer_data)
        try:
            total_print_length = total_print_length.replace('"', '')
            total_print_length = total_print_length.split(',')[1]
        except Exception:
            total_print_length = ''
        result_hs = result_hs.replace('\n', ',')
        printer_data = {
            'interface': printer,
            'printer_model': result.split(',')[0],
            'printer_name': printer_name,
            'sw_version': result.split(',')[1],
            'dpi': result.split(',')[2],
            'memory': result.split(',')[3],
            'paper_out': result_hs.split(',')[1],
            'head_up': head_up,
            'total_print_length': total_print_length,
        }
        return (printer_data)

# --------------------------- get_printer_data --------------------------------
    def get_ipprinter_data(self, ip_address, port, command):

        try:
            mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            mysocket.settimeout(5)
            mysocket.connect((ip_address, port))
            mysocket.send(command.encode())
            result = mysocket.recv(1000)
            mysocket.close()
        except Exception as error:
            return (f'Connection error on {ip_address}: {error}')
        result = result.decode('UTF-8')

        # remove the STX and ETX commands from printers answer
        result = result.replace('\02', '')
        result = result.replace('\03', '')
        return result

# --------------------------- get_printer_data --------------------------------
    def get_printer_data(self, device, command):

        try:
            printer = open(device, 'r+')
            printer.write(command)
            result = ''
            to = 0
            while result == '' and to < 10:
                to = to + 1
                result = printer.read()
            printer.close()
        except Exception as error:
            return (f'Connection Error on {device}: {error}')
        if to == 10:
            return (f'Bad response from {device}')

        # remove the STX and ETX commands from printers answer
        result = result.replace('\02', '')
        result = result.replace('\03', '')
        return result

# -----------------------------------------------------------------------------
    def collect_all_ipprinter(self):

        all_printer = []
        all_printer.append(self.get_setting('IP_ADDRESS'))
        all_templates = LabelTemplate.objects.all()
        for template in all_templates:
            try:
                if 'ip_address' in template.metadata:
                    if template.metadata['ip_address'] not in all_printer:
                        all_printer.append(template.metadata['ip_address'])
            except Exception:
                pass
        return all_printer
