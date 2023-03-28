# Christopher Bowen
# TAP
# This script requires Python 3
# To run this tool use the following command:
# python TAP flags filepath

import os
import datetime
import argparse
import sqlite3 as sql
from datetime import datetime
import re
import json

# import module
import plotly.express as px
from geopy.geocoders import Nominatim
import geopy.distance

# setup

global curr_dir
global parser
curr_dir: str
parser: argparse

global in_arg
global out_arg

global start_date
global end_date

#curr_dir = os.path.dirname(os.path.abspath(__file__))
#parser = argparse.ArgumentParser()

# memory dump list
global memPoints
global corruptedPoints
memPoints = []
corruptedPoints = []

# sql data points
global sqlPoints
sqlPoints = []

# file list
global sqlFiles
global memFiles
sqlFiles = []
memFiles = []

# potentially spoofed locations points
global spoofPoints
spoofPoints = []

### These objects are not used. They are just for representation of what the dictionaries will look like ###
##### LocationData for Memory Dumps and signature to look for in memory #####
MEMORY_SIGNATURE = 'tile_uuid'


geolocator = Nominatim(user_agent="geoapiExercises")


class MemLocationData:
    def __init__(self, tile_uuid, location_timestamp, raw_precision, latitude, longitude, precision):
        self.tile_uuid = tile_uuid
        self.location_timestamp = location_timestamp
        self.raw_precision = raw_precision
        self.latitude = latitude
        self.longitude = longitude
        self.percision = precision


#################################################

##### LocationData for Memory Dumps #####
class SQLLocationData:
    def __init__(self, tile_uuid, location_timestamp, raw_precision, latitude, longitude, precision):
        self.tile_uuid = tile_uuid
        self.location_timestamp = location_timestamp
        self.raw_precision = raw_precision
        self.latitude = latitude
        self.longitude = longitude
        self.raw_percision = precision
#################################################


## Error Messages
#################################################
class NotMEMFileError(Exception):
    ''' Raised when a trying to find a kmem or mem file'''

    def __init__(self, in_f):
        self.value = "Could not find memory file"

    def __str__(self):
        return repr(self.value)


class NoDataBaseFileError(Exception):
    def __init__(self):
        self.value = 'Could not find Database file'

    def __str__(self):
        return repr(self.value)


class CorruptEntryError(Exception):
    def __init__(self, value="This entry is corrupted"):
        self.value = value

    def __str__(self):
        return repr(self.value)


#################################################


# Helper Methods
#################################################

def convert_SQLtime(item):
    unix = datetime(1970, 1, 1)     # UTC
    cocoa = datetime(2001, 1, 1)    # UTC
    delta = cocoa - unix            # timedelta instance
    timestamp = datetime.fromtimestamp(int(item.get('ZTIMESTAMP'))) + delta

    return timestamp

#################################################

def setup():
    # set the current directory
    global curr_dir
    curr_dir = os.path.dirname(os.path.abspath(__file__))

    # create the parser
    global parser
    parser = argparse.ArgumentParser()


def setupParser():
    parser.add_argument('input', help='path to input data file or data dir')
    parser.add_argument('-o', '--output',
                        help='path to output CSV File or directory. If none is specified the output will be saved in the current directory as output.txt.')
    parser.add_argument('-s', '--startdate', help='Set a date range in the format d/m/y ')
    parser.add_argument('-e', '--enddate', help='Set a date range in the format d/m/y ')
    parser.add_argument('-f', '--falsified', help='This flag enables spoofing detection. ')

def parseArgs():
    global in_arg
    global out_arg
    global start_date
    global end_date

    args = parser.parse_args()


    in_arg = args.input
    out_arg = args.output


    ##date parsing
    #######################################################
    start_date = args.startdate
    end_date = args.enddate

    if start_date is None:
        start_date = None
    else:
        start_date = datetime.strptime(start_date, "%m/%d/%y")

    if end_date is None:
        end_date = None
    else:
        end_date = datetime.strptime(end_date, "%m/%d/%y")

    #######################################################

    in_files_list = []

    if os.path.isfile(in_arg):  # file input
        in_files_list.append(in_arg)

        if out_arg == None:  # output not specified
            spl_path = os.path.split(in_arg)
            out_arg = spl_path[len(spl_path) - 1].split('.')[0] + '-Output.txt'

        else:  # file or directory output     os.path.isfile(out_arg) or os.path.isdir(out_arg)
            out_arg = out_arg

    elif os.path.isdir(in_arg):  # directory input
        print(in_arg)
        in_files_list = [f for f in os.listdir(in_arg) if os.path.isfile(os.path.join(in_arg, f))]
        in_dir = in_arg

        if out_arg == None:  # output not specified
            out_path = curr_dir
        elif os.path.isdir(out_arg):
            out_path = out_arg
        else:
            print('Error: Output must be a valid directory or None.')
            exit()
    else:  # not a valid file or directory
        print('Error: Input must be a valid file or directory.')
        exit()
    
    
    # seperate the files into each of their appropraite list
    if len(in_files_list) > 1:
        for f in in_files_list:
            fileType = f.split('.')[-1]
            if fileType == "sqlite":
                sqlFiles.append(in_arg + "/" + f)

            elif fileType == "vmem" or fileType == "mem":
                memFiles.append(in_arg + "/" + f)
    else:
        fileType = in_files_list[0].split('.')[-1]
        if fileType == "sqlite":
            sqlFiles.append(in_files_list[0])

        elif fileType == "vmem" or fileType == "mem":
            memFiles.append(in_files_list[0])


def processMEM():
    global memPoints
    global corruptedPoints
    global start_date
    global end_date

    memPoints = []
    corruptedPoints =[]
    # check to see if there are any memfiles
    if len(memFiles) == 0:
        return
    else:
        # process the Memory File(s)
        for f in memFiles:
            final = []
            fileString = []
            with open(f, 'r', encoding="utf8", errors='ignore') as fp:
                for l_no, line in enumerate(fp):

                    # search string
                    if MEMORY_SIGNATURE in line:
                        print('string found in a file')
                        print('Line Number:', l_no)
                        fileString.append(re.sub(r'[^\x00-\x7f]', r'', line))


            for i in fileString:
                l = re.findall(r'\{\"tile_uuid.*?\},', i)
                for p in l:
                    final.append(p)

            final = list(set(final))
            tempPoints = []
            for p in final:
                current = p.replace('\"', '')
                current = current.replace('\'', '')
                current = current.replace('{', '')
                current = current.replace('}', '')

                current = re.split(r'[,:]', current)

                # verification of the data
                try:
                    if current[0] == "tile_uuid":
                        if current[2] == "location_timestamp":
                            if current[4] == "raw_precision":
                                if current[6] == "latitude":
                                    if current[8] == "longitude":
                                        if current[10] == "precision":
                                            try:
                                                temp = dict(tile_uuid=current[1], location_timestamp=int(current[3]),
                                                            raw_precision=float(current[5]), latitude=float(current[7]),
                                                            longitude=float(current[9]), precision=float(current[11]))
                                                tempPoints.append(temp)

                                            except:
                                                corruptedPoints.append(p)
                                                continue
                        else:
                            corruptedPoints.append(p)
                except:
                    None
            tempPoints.sort(key=lambda x: x['location_timestamp'])

            # filtering by time input
            if start_date != None:
                if end_date != None:
                    for i in tempPoints:
                        print(i.get('location_timestamp'))
                        if start_date < datetime.fromtimestamp(i.get('location_timestamp') / 1000) < end_date:
                            memPoints.append(i)
                else:
                    for i in tempPoints:
                        if start_date < datetime.fromtimestamp(i.get('location_timestamp') / 1000):
                            memPoints.append(i)
            else:
                for i in tempPoints:
                    memPoints.append(i)


def processSQL():
    global start_date
    global end_date
    global sqlPoints

    sqlPoints = []

    # check to see if there are any sqlFiles
    if len(sqlFiles) == 0:
        return
    else:
        for f in sqlFiles:
            conn = sql.connect(f)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

                cursor.execute("select * from ZTILENTITY_PLACEMARK;")

                desc = cursor.description
                column_names = [col[0] for col in desc]
                data = [dict(zip(column_names, row))
                        for row in cursor.fetchall()]

                data.sort(key=lambda x: x['ZTIMESTAMP'])  # sort the list by time
             
                # close the connection
                conn.close()

                # filtering by time input
                if start_date != None:
                    if end_date != None:
                        for i in data:
                            if start_date < convert_SQLtime(i) < end_date:
                                sqlPoints.append(i)
                    else:
                        for i in data:
                            if start_date < convert_SQLtime(i):
                                sqlPoints.append(i)
                else:
                    for i in data:
                        sqlPoints.append(i)

            except NoDataBaseFileError:
                continue


def drawMEM():
    global memPoints
    if len(memPoints) == 0:
        return

    fig = px.scatter_mapbox(memPoints, lat="latitude", lon="longitude", hover_name="tile_uuid",
                            hover_data=["location_timestamp", "raw_precision", "precision"],
                            color_discrete_sequence=["Red"], zoom=10, height=1000)
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    fig.add_traces(px.line_mapbox(memPoints, lat="latitude", lon="longitude").data)

    fig.write_html('memlocations.html', auto_open=True)

    fig.show()


def drawSQL():
    global sqlPoints
    global spoofPoints
    if len(sqlPoints) == 0:
        return

    fig = px.scatter_mapbox(sqlPoints, lat="ZLATITUDE", lon="ZLONGITUDE", hover_name="ZSUBLOCALITY",
                            hover_data=["ZSUBLOCALITY", "ZTIMESTAMP"],
                            color_discrete_sequence=["Red"], zoom=10, height=1000)

    

    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    fig.add_traces(px.line_mapbox(sqlPoints,lat="ZLATITUDE", lon="ZLONGITUDE", hover_data=["ZTIMESTAMP"]).data)

    fig2 = px.scatter_mapbox(spoofPoints, lat="ZLATITUDE", lon="ZLONGITUDE", hover_name=["Potentially Spoofed Location"]*len(spoofPoints),
                            hover_data=["ZSUBLOCALITY", "ZTIMESTAMP"],
                            color_discrete_sequence=["Black"], zoom=10, height=1000)
    fig.add_trace(fig2.data[0])


    fig.write_html('sqllocations.html', auto_open=True)

    fig.show()


def checkspoof():
    global memPoints
    global sqlPoints

    global spoofPoints

    if sqlPoints != None:
        lastitem = None
        lastLocation = None
        newLocation = None
        for item in sqlPoints:
            
            try:
                if lastLocation is None:
                    lastitem = item
                    lastLocation = geolocator.reverse(str(item.get('ZLATITUDE'))+", "+str(item.get('ZLONGITUDE')))
                    address = lastLocation.raw['address']
                    lastLocation = address.get('state')
                else:
                    newLocation = geolocator.reverse(str(item.get('ZLATITUDE'))+", "+str(item.get('ZLONGITUDE')))
                    
                
                    timegap = item.get('ZTIMESTAMP')-lastitem.get('ZTIMESTAMP')
                    coords_1 = (item.get('ZLATITUDE'), item.get('ZLONGITUDE'))
                    coords_2 = (lastitem.get('ZLATITUDE'), lastitem.get('ZLONGITUDE'))
                    distancegap = geopy.distance.geodesic(coords_1, coords_2).miles


                    speed = distancegap / (timegap/1000/60/60)

                    address = newLocation.raw['address']
                    newLocation = address.get('state')


                    if newLocation != lastLocation:
                        print(f"time1 {item.get('ZTIMESTAMP')}\n time2: {lastitem.get('ZTIMESTAMP')}\n, timegap:{timegap}\ncords1:{coords_1}\ncords2:{coords_2}\n,distance:{distancegap},speed:{speed}")
                        if speed > 600:
                            spoofPoints.append(item)
                            lastLocation = newLocation
                            lastLocation = newLocation
                    lastitem = item
            except:
                lastitem = item
                    
                

    if memPoints != None:
        lastitem = None
        lastLocation = None
        newLocation = None

        for item in memPoints:
            try:
                #print(item)
                if lastLocation is None:
                    lastitem = item
                    lastLocation = geolocator.reverse(str(item.get('latitude'))+", "+str(item.get('longitude')))
                    address = lastLocation.raw['address']
                    lastLocation = lastLocation.address.get('state')
                else:
                    newLocation = geolocator.reverse(str(item.get('latitude'))+", "+str(item.get('longitude')))
                    timegap = item.get('location_timestamp')-lastitem.get('location_timestamp')
                    coords_1 = (item.get('latitude'), item.get('longitude'))
                    coords_2 = (lastitem.get('latitude'), lastitem.get('longitude'))
                    distancegap = geopy.distance.geodesic(coords_1, coords_2).miles


                    speed = distancegap / (timegap/1000/60/60)
                    address = lastLocation.raw['address']
                    newLocation = newLocation.address.get('state')
                    #print(f"time1 {item.get('location_timestamp')}\n time2: {lastitem.get('location_timestamp')}\n, timegap:{timegap}\ncords1:{coords_1}\ncords2:{coords_2}\n,distance:{distancegap},speed:{speed}")
                    if newLocation != newLocation:
                        if speed > 600:
                            spoofPoints.append(item)
                            lastLocation = newLocation
                            lastLocation = newLocation
                    lastitem = item
            except:
                lastitem = item

def createReport():
    global in_arg
    global out_arg

    global start_date
    global end_date

    global memFiles
    global sqlFiles

    global memPoints
    global sqlPoints

    if out_arg is None:
        out_arg = "out.txt"

    f = open(out_arg, 'w')

    f.write("Report for TAP Parser\n")
    f.write("#########################################\n")

    f.write("Input path(s)\n")
    f.write("#########################################\n")
    for item in in_arg:
        f.write(item)
    f.write("\n#########################################\n")

    f.write("Out path(s)\n")
    f.write("#########################################\n")
    for item in out_arg:
        f.write(item)
    f.write("\n#########################################\n")

    f.write("Dates Selected\n")
    f.write("#########################################\n")
    f.write("\nStart Date:")
    f.write(str(start_date))
    f.write("\nEnd Date:")
    f.write(str(end_date))
    f.write("\n#########################################\n")

    f.write("\nMemory file(s) parsed \n")
    f.write("#########################################\n")
    if memFiles != None:
        for item in memFiles:
            f.write(item)
    f.write("\n#########################################\n")

    f.write("\nMemory file(s) datapoints parsed \n")
    f.write("Amount of Points:")
    f.write(str(len(memPoints)))
    f.write("\n#########################################\n")
    for item in memPoints:
        f.write(json.dumps(item))
        f.write("\n")
    f.write("#########################################\n")

    f.write("\nMemory file(s) possible corrupted datapoints parsed \n")
    if corruptedPoints != None:
        f.write("Amount of Points:")
        f.write(str(len(corruptedPoints)))
        f.write("\n#########################################\n")
        for item in corruptedPoints:
            f.write(json.dumps(item))
            f.write("\n")
    f.write("#########################################\n")

    f.write("\nSQL file(s) parsed \n")
    f.write("#########################################\n")
    if sqlFiles != None:
        for item in sqlFiles:
            f.write(item)
    f.write("\n#########################################\n")

    f.write("\nSQL file(s) datapoints parsed \n")
    f.write("Amount of Points:")
    f.write(str(len(sqlPoints)))
    f.write("\n#########################################\n")
    for item in sqlPoints:
        f.write(json.dumps(item))
        f.write("\n")
    f.write("#########################################\n")


    f.write("\nPossible spoofed data points\n")
    f.write("Amount of Points:")
    f.write(str(len(spoofPoints)))

    f.write("\n#########################################\n")
    for item in spoofPoints:
        f.write(json.dumps(item))
        f.write("\n")
    f.write("#########################################\n")

    f.close()






def main():
    
    # setup the program
    #####################

    setup()
    setupParser()

    #####################

    # parse the user input
    #####################

    parseArgs()

    #####################

    # proccess the data
    #####################

    processMEM()
    processSQL()
    checkspoof()

    #####################

    # graph each of the list of points
    #####################

    drawMEM()
    drawSQL()

    #####################

    # create a report
    createReport()

if __name__ == "__main__":
    main()
