import os
import time
from waveshare_OLED import OLED_1in51
from PIL import Image,ImageDraw,ImageFont
import sys

picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)



def display(mx,my):
    disp = OLED_1in51.OLED_1in51()
    disp.Init()
    disp.clear()
    image1 = Image.new('1', (disp.width, disp.height), "WHITE")
    font1 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
    draw = ImageDraw.Draw(image1)
    if (mx <= 150):
        draw.line([(127,0),(127,63)], fill = 0)
        print("left")
        
    else:
        draw.line([(0,0),(0,63)], fill = 0)
        print("right")

    image1 = image1.rotate(180) 
    disp.ShowImage(disp.getbuffer(image1))
    time.sleep(2)
    disp.clear()