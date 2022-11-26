import datetime
current_time = datetime.datetime.now()
capturenamex=10
capturenamey=2
current_time=datetime.datetime(current_time.year-2000,current_time.month,current_time.day,current_time.hour,current_time.minute,current_time.second,current_time.microsecond)
print(current_time.microsecond)
namefile=str(current_time.year)+"_"+\
    str(current_time.month)+"_"+\
    str(current_time.day)+" "+\
    str(current_time.hour)+"_"+\
    str(current_time.minute)+"_"+\
    str('{:.2f}'.format(current_time.second+(current_time.microsecond/1000000)))+"_"+\
    "{:02d}".format(capturenamex)+"_"+\
    "{:02d}".format(capturenamey)+".jpg" 
print(namefile)