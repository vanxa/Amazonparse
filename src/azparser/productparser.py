import urllib3
from urllib.request import urlretrieve
import time
import re
from multiprocessing import Pool
import os
import sys


DO_CACHE = True
#class AZParser(object):
#    
#    def __init__(self, asin):
#        self.url = "https://www.amazon.com/gp/product/" + asin
#        self.asin = asin
##        self.html = []
 #       user_agent = {'user-agent' : 'Mozilla/5.0 (Windows NT 6.3; rv:36) ..'}
 #       self.http = urllib3.PoolManager(3, user_agent)
    
def open_url(asin):
    url = "https://www.amazon.com/gp/product/" + asin
    if DO_CACHE:
        if os.path.isfile("CACHE/"+asin+".html"):
            print("Caching is on and found local copy of " + url)
            return open("CACHE/"+asin+".html","r").read().replace("\n","")
    kwargs = {'retries' : 1}
    print("Opening URL " + url)
    user_agent = {'user-agent' : 'Mozilla/5.0 (Windows NT 6.3; rv:36) ..'}
    conn = urllib3.connection_from_url(url, timeout=10.0, maxsize=10, block=True, headers=user_agent)
    html = conn.urlopen("GET",url)
    if html.status == 200:
        print("OK")
        data = html.data.decode("UTF-8")
        if DO_CACHE:
            print("Saving local copy of " + url)
            with open("CACHE/"+asin+".html", "w") as f:
                f.write(data)
        return data.replace("\n","")
    else:
        print("Could not find URL")
        return None
    #return conn.urlopen("GET",url).data.decode("UTF-8")
    
def process_url(asin):
    data = open_url(asin)
    if data != None:
        print("Got url for ASIN " + asin)
        print("Finding images")
        images = parse_url(data)
        print("Creating storage directory for product " + asin)
        if not os.path.isdir(asin):
            os.mkdir(asin)
        else:
            print("Directory already exists in " + os.getcwd())
        print("Saving hiRes images")
        a = 0
        print("Got " + str(images.keys()) + " keys")
        if "hiRes" in images.keys():
            for item in images["hiRes"]:
                urlretrieve(item, asin+"/"+str(a)+".jpg")
                a += 1
        sys.stdout.flush()
        return True
    
            

        
def test_threading():
    #asin_list = ["B01H2E0J5M", "B01EZC9WC0", "B01F9N5QXI", "B019O8YWR0", "B01GINVN1W", "B018IZ0SWI"]
    asin_list = ["B01H2E0J5M"]
    a = []
    with Pool(processes = len(asin_list)) as pool:
        a = pool.map(process_url,asin_list)
    return a




def parse_url(data):
    #data = None
    #with open("test1.txt","r", encoding="UTF-8") as f:
    #    data = f.read().replace("\n","")
    print("Searching for Javascript segment that has image urls")  
    obj = re.search(r"P.when\(\'A\'\).register\(\"ImageBlockATF.*colorImages.*initial[\'\"]*.*(\[\{.*\]\}).*colorToAsin",data)
    print(obj.groups())
    if obj == None:
        print("Something went wrong. No such segment exists")
        return 
    print("Found segment")
    i = re.sub(r"[\[\]\{\}]", "", obj.group(1))
    print("Splitting")
    lst  = [re.sub(r"[\'\"]","", item) for item in i.split("\",\"")]
    #if len(lst) == 0:
    #    print("something went wrong")
    images = {}
    print("Gathering images by type")
    for item in lst:
        item = item.replace("\"","").replace("'","")
        print(item)
        obj = re.search(r"(.*)\:(http.*)", item)
        if obj != None:
            print("For type " + obj.group(1) + " URL is " + obj.group(2))
            try:
                images[obj.group(1)] += [obj.group(2)]
            except KeyError:
                images[obj.group(1)] = [obj.group(2)]
    print("Done")
    return images
    
        
if __name__ == "main":
    test_threading()

        