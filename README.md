[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


# inventree-zebra-plugin

This is a label printing plugin for [InvenTree](https://inventree.org), which provides support for Zebra Label printers .
It was only tested with  GK420T but should work for other ZPL printers too. It uses the ZPL library to
convert the png data provided by InvenTree to Zebra's bitmap format. 

It can output the print data either to a local printer connected to the computer via USB or to a network printer
with an IP address. The output can be configured in the InvenTree plugin user interface. So the source code is 
a good example for this. 

Error handling is very basic. 

## Installation

Install this plugin using pip with the following command::

```
pip install git+https://github.com/SergeoLacruz/inventree-zebra-plugin
```
 
## Configuration Options
### Printer Interface
Here you can chose between Local printer or network printer. Default value is a local printer.

### IP address
In case you use an IP printer set the IPv4 address here.

### Port 
In case you use an IP printer set the port number here. The default port number is 9100.

### Local Device
In case of a local printer set the device here. The plugin actually puts the data directly to the
device /dev/usb/lp0. No printer spooler is involved so far. 

### Threshold 
The image from pillow comes in greyscale. The plugin converts it ti pure BW because this gives a much 
better print result. The threshold between black and white can be adjusted here.

### Darkness 
This is a value that influences the darkness of the print. Allowed values are 0 (white) to 30 (black).
It is directly converted to a SD command in ZPL. If your black areas tend to blur out reduce the 
darkness.

### X-Position 
This sets the position of the label in x-axis in mm. If your printer is 100mm wide and your label
is 50mm wide set X-Position to 25.

### Width, Height
These are values for the label width and height in mm. Please be aware that this is the size of the 
paper in the printer. The definition of the label in the css file has to fit to these values. 
There is no automatic scaling. 

## How it works
First import all the stuff you need. Here we use the translation mechanism from Django for multi language support.
The import the InvenTree libs and everything you need for plugin. Here we have ZPL for the Zebra bitmaps and socket
for the IP connection to the printer. 

The next part is this:

```python
class ZebraLabelPlugin(LabelPrintingMixin, SettingsMixin, IntegrationPluginBase):

    AUTHOR = "Michael Buchmann"
    DESCRIPTION = "Label printing plugin for Zebra printers"
    VERSION = ZEBRA_PLUGIN_VERSION
    NAME = "Zebra"
    SLUG = "zebra"
    TITLE = "Zebra Label Printer"
```

The name of the class can be freely chosen. You reference to it in the entry_points section of the setup.py file.
The parameters need to be like in the example. Then there is the description block. The keywords are fixed and 
need to be like that. The values are found in the UI as shown in the pictures below.

![Admin](https://github.com/SergeoLacruz/inventree-zebra-plugin/blob/master/pictures/plugin_admin.png)
![Config](https://github.com/SergeoLacruz/inventree-zebra-plugin/blob/master/pictures/plugin.png)


Then we add the configuration parameters.
```python
SETTINGS = {
        'CONNECTION': {
            'name': _('Printer Interface'),
            'description': _('Select local or network printer'),
            'choices': [('local','Local printer e.g. USB'),('network','Network printer with IP address')],
            'default': 'local',
        },
        'PORT': {
            'name': _('Port'),
            'description': _('Network port in case of network printer'),
            'default': '9100',
        },
    }

```

We need to define a dict with the name SETTINGS. Please be aware the keys need to be in all CAPITAL letters like CONNECTION.
Simple parameters are just text strings like the port. We can set a default. The name and description shows up in the UI. 
Instead of a simple text we can also use choices. The first string like "local" it the key you use in the code. The second
one is the description in the UI. 
After that we need to define a function:

```python
def print_label(self, **kwargs){
```

The kwargs is a dict with the following keys:

- pdf_data
- user
- filename
- label_instance
- item_instance
- width
- height
- png_file

the item_instance is the part to be printed. This allows direct access to all part data. The arguments width and height 
come from the settings of the label in the admin interface. NOT from the html template. 
For the Zebra printer we use the png_file. This is a PIL (python Pillow) object with the graphic of the label in PNG format. 
The PIL object is a greyscale image. Because the printer can just print pure BW we convert this to a BW picture. 

```python
fn = lambda x : 255 if x > Threshold else 0
label_image = label_image.convert('L').point(fn, mode='1')
```

The threshold can by modified by a plugin parameter. 200 is a good starting value.  This trick gives much better prints. 
We can put the result of this directly into the ZPL library. 

```python
l = zpl.Label(Width,Height,8)
l.origin(0, 0)
l.write_graphic(label_image, Width)
l.endorigin()
```

Width and Height define is the size of the label in millimeters as described above. The third parameter is the resolution of the printer in
dots per mm. As the Zebra printer has 200dpi we put an eight here. write_graphic converts the pillow data
to ZPL. 

The plugin was tested with a labels of various sizes as defined using css and html in InvenTree as shown below. The DPI scaling
can be chosen in the InvenTree settings. 800 is a good value because it gives good quality.

```
<style>
    @page {
        width: 50mm;
        height: 30mm;
        padding: 0mm;
        margin: 0px 0px 0px 0px;
        background-color: white;
    }
```

The rest of the code is just output to the printer on different interfaces.

## Quality matters 
The InvenTree printer system uses a graphical representation of the label. The label is described
in HTML, converted to a pixel graphic and printed. The advantage is independency  printer
models and systems. Disadvantage is larger data and quality problems with darkness and scaling.
Let's have a look at the following printout:

![QRcodes](https://github.com/SergeoLacruz/inventree-zebra-plugin/blob/master/pictures/qr.png|width=500px)

Both codes have been printed with the same printer on the same reel. The left one is 
hardly readable using my mobile. The right one reads easily even as it is smaller. 

### Secret 1, Scale
The printer resolution is 8 dots per mm resulting in a dot size of 0.125mm. The QR code pixel 
and the printer pixel size should be integrally divisible. The code in the picture has 21
pixels plus one in the frame, so 23 pixel. The frame is set in the HTML description. 

```
{% qrcode qr_data border=1 %}
```

I selected two dots per pixel. So 23 * 2 * 0.125 = 6.125mm. If the size is something different
scaling takes place and the result might be worse. If you like a larger printout select more 
dots per pixel. From a certain size upwards the value does not matter any more because the code
gets large enough to be readable in any quality. 

### Secret 2: Darkness
Zebra printers allow to set the darkness of the print in values between 0 (white) and 30 (max)
The left code was printed with a value 0r 30. The black dots tend to blur out a bit resulting
in smaller white areas. The right code was printed with a value of 25 resulting in larger white
pixels.  The darkness values are just examples. Your values will differ based on printer model,
media type and printer age. The printer head tends to wear out and the darkness value might
need an adjustment from time to time. 

