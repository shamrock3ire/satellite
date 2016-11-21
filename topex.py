# -*- coding: utf8 -*-
## calculate TOPEX (Topographic Exposure) ##
## import module ##
import grass.script as grass
import grass.script.setup as gsetup
import math
import os

def topex(gisdb,location,mapset,dem,res,interval,range_max,output):

    # set up grass path #
    gisbase = os.environ['GISBASE']
    # set GRASS gisdatabase, location, mapset #
    gsetup.init(gisbase, gisdb, location, mapset)
    # set region as same as input DEM (extent and resolution)
    grass.run_command("g.region", rast=dem)
    # calculate pixel based interval
    interval_p = int(round(interval / res))
    # calculate pixel based maximum range
    range_max_p = int(round(range_max / res))
    
    ## set formula for calculation ##
    # set initial formula
    formula_t1 = output + " = "
    
    for azi in (0,45,90,135,180,225,270,315):
        # initial cell number
        num = 0
        formula = "max("
        while num < range_max_p:
            num = num + interval_p
            x = int(round(math.sin(math.radians(azi))*num))
            y = int(round(math.cos(math.radians(azi))*num))
            formula = formula + "atan((" + dem + "[" + str(y) + "," + str(x) + "] - " + dem + ") / (" + str(res) + " * " + str(num) + ")),"
        # build formula for calculating max elevation angle at single direction    
        formula_t = formula[0:-1] + ")"
        # build formula for summing up value at all direction 
        formula_t1 = formula_t1 + formula_t + " + "
    # build formula for r.mapcalc
    formula_f = formula_t1[0:-3]    
    print formula_f    
    ## run r.mapcalc command ##
    grass.run_command("r.mapcalc_wrapper",expression = formula_f)
    
    print "finish"
    
if __name__ == '__main__':
    print "this is code block"
