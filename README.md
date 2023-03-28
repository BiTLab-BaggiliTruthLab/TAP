# TAP
Tile Artifact Parser

This tool is used to parse data from Tile Inc.'s data sources. There are two input options for the tool to parse location data: SQL and vmem files. 
The following flags are available:
  
   input:     the path to the input file 
   output:    optional ouput file for the report
   startdate: optional startdate to set the date range (d/m/y)
   enddate:   optional enddate to set the date range (d/m/y)
   falsified: optional flag to enable possible spoofing detection 
   
The tool will create an html output of a map containing the location data that has been parsed, and then it will create a log report of each of the points found in each data source.


