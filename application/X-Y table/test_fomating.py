import datetime
current_time = datetime.datetime.now()
current_time = datetime.datetime(2022,11,12,2,14,11,160000)
capturenamex=10
capturenamey=2
current_time=datetime.datetime(current_time.year-2000,current_time.month,current_time.day,current_time.hour,current_time.minute,current_time.second,current_time.microsecond)
print(current_time.microsecond)
namefile=str('{:02d}'.format(current_time.year))+"_"+\
    str('{:02d}'.format(current_time.month))+"_"+\
    str('{:02d}'.format(current_time.day))+" "+\
    str('{:02d}'.format(current_time.hour))+"_"+\
    str('{:02d}'.format(current_time.minute))+"_"+\
    str('{:02d}'.format(current_time.second))+"."+\
    str('{:02d}'.format(int(current_time.microsecond/10000)))+"_"+\
    "{:02d}".format(capturenamex)+"_"+\
    "{:02d}".format(capturenamey)+".jpg" 
print(namefile)
    # str('{:02.2f}'.format(current_time.second+(current_time.microsecond/1000000)))+"_"+\

