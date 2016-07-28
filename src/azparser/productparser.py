import urllib3
from urllib import request, parse
import re
import os
import sys
from bs4 import BeautifulSoup as bs
import optparse
from PIL import Image
import itertools
import traceback

USE_CACHE = False
AUTO_OPEN_EDITOR = False

def open_url(asin, use_cache=None):
    url = "https://www.amazon.com/gp/product/" + asin
    
    print("Creating storage directory for product " + asin)
    if not os.path.isdir(asin):
        os.mkdir(asin)
    else:
        print("Directory already exists in " + os.getcwd())    
    if USE_CACHE or use_cache != None:
        if os.path.isfile(asin + "/" + asin + ".html"):
            print("Caching is on and found local copy of " + url)
            return bs(open(asin + "/" + asin+".html","r",encoding="UTF-8").read(), "html.parser")
    kwargs = {'retries' : 1}
    print("Opening URL " + url)
    user_agent = {'user-agent' : 'Mozilla/5.0 (Windows NT 6.3; rv:36) ..'}
    conn = urllib3.connection_from_url(url, timeout=10.0, maxsize=10, block=True, headers=user_agent)
    html = conn.urlopen("GET",url)
    if html.status == 200:
        print("OK")
        data = html.data.decode("UTF-8")
        if USE_CACHE:
            print("Saving local copy of " + url)
            with open(asin + "/" + asin+".html", "w", encoding="UTF-8") as f:
                f.write(data)
        return bs(data, "html.parser")
    else:
        print("Could not find URL")
        return None
    #return conn.urlopen("GET",url).data.decode("UTF-8")
    
def process_asin(asin):
    print("Processing " + asin)
    try:
        html = open_url(asin)
        if html != None:
            print("Getting product information")
            done = False
            if os.path.isfile(asin+"/info.txt"):
                while True:
                    q = input("Info file already exists in %s. Re-process the information (y/N/q)? ").lower()
                    if q == "y":
                        done = parse_url_for_info(html, asin)
                        break
                    elif q == "" or q == None or q == "n":
                        done = True
                        break
                    elif q == "q":
                        print("Quitting")
                        return False
            
            else:
                done = parse_url_for_info(html,asin)
            if not done:
                print("There was an exception raised. Exiting")
                return False
            
            if AUTO_OPEN_EDITOR:
                flag = open_editor(os.path.join(os.getcwd(),asin,"info.txt"))
                #if flag != 0:
                #    print("There was an error while editing the file.")
                #    return False
                # This is just a temporary step, in order to test the above functionality
                #input("Done. Press any key to continue")
            else:
                input("The info file has been created in %s . Press any key to continue with image download, once you're done editing the data" % asin+"/info.txt")
            
            print("Parsing keyword data from file")
            keywords = parse_keywords(asin+"/info.txt")
            print("Getting images")
            images = parse_url_for_images(html)
            if images == None:
                print("Something went wrong for asin " + asin)
                return False

           
            a = 0
            print("Got " + str(images.keys()) + " keys")
            keys = images.keys()
            size = None
            if "hiRes" in keys:
                size = "hiRes"
            elif "large" in keys:
                size = "large"
            elif "medium" in keys:
                size = "medium"
            elif "thumb" in keys:
                size = "thumb"
            print("Getting %s size images" % size)
            for item in images[size]:
                print("Saving %s to temporary location %s" % ( item, asin+"/"+str(a)+".jpg") )
                request.urlretrieve(item, asin+"/"+str(a)+".jpg")
                a += 1
            print("Done. Resizing and renaming images.")
            img_count = a
            a = 0
            longtailkword = keywords["LongTailKeyword"]
            while a < img_count:
                name = longtailkword
                if a > len(keywords["SuggestedKeyword"]):
                    print("There are more images saved than keywords! Will set the name to %s%d" %(name, a))
                    name += str(a)
                else:
                    kword = keywords["SuggestedKeyword"][a]
                    if isinstance(kword, str):
                        name += " " + kword
                    elif isinstance(kword, tuple):
                        name += " " + kword[0] + " "+ kword[1]
                    else:
                        print("Was expecting either string or tuple, got %s " % str(type(kword)))    
                im = Image.open(asin+"/"+str(a)+".jpg")
                size = min(im.size)
                if size < 500:
                    print("Resizing image to 500x500")
                    im = im.resize((500,500))
                elif size > 900 and size < 1500:
                    print("Resizing image to 1500x1500")
                    im = im.resize((1500,1500))
                print("Saving image to %s.jpg" % (name))
                try:
                    im.save(asin+"/"+name+".jpg")
                    os.remove(asin+"/"+str(a)+".jpg")
                except Exception as e:
                    print("Exception - {0}".format(e)) 
                a += 1
            return True
        else:
            print("Skipping processing")
            return True
    except Exception as e:
        (trace_type, trace_val, stacktrace) = sys.exc_info()
        print("Caught exception for asin "+ asin)
        print("-"*50)
        traceback.print_exception(trace_type,trace_val, stacktrace,limit=2, file=sys.stdout)
        print("-"*50)
        return False

def parse_keywords(loc):
    try:
        keywords = {}
        with open(loc, "r", encoding="UTF-8") as f:
            for line in f.readlines():
                line = line.strip()
                obj = re.search(r"longtailkeyword\s*\=\s*(.*)", line, re.IGNORECASE)
                if obj:
                    keyword = obj.group(1)
                    print("Found it. Keyword is %s" % keyword )
                    keywords["LongTailKeyword"] = keyword
                obj = re.search(r"SuggestedKeyword(\d*)\s*\=\s*(.*)", line)
                if obj:
                    index = obj.group(1)
                    keyword = obj.group(2)
                    print("Found SuggestedKeyword%s = %s" %(index, keyword))
                    try:
                        keywords["SuggestedKeyword"] += [keyword]
                    except KeyError:
                        keywords["SuggestedKeyword"] = [keyword]
            print("Done")
            if len(keywords.keys()) == 0:
                print("No keywords were found in file. Did you forget to add keywords?")
                return None
            keywords["SuggestedKeyword"].extend(list(itertools.combinations(keywords["SuggestedKeyword"],2)))
            keywords["SuggestedKeyword"].extend(list(itertools.combinations(keywords["SuggestedKeyword"],3)))
            return keywords
                
    except Exception as e:
        print("Could not open file " + loc + " - {0}".format(e))    

def open_editor(doclocation):
    try:
        if sys.platform == 'win32':
            os.system(doclocation)
        else:
            os.system("%s %s" % (os.getenv("EDITOR"), doclocation))
    except Exception as e:
        print("Got exception {0}".format(e))
        return False
    return True

def run():
    print("Starting AZParser.")
    asin_list = parse_asin_file()
    for asin in asin_list:
        process_asin(asin)
    input("Parser has finished")
    print("Goodbye!")
        

def parse_url_for_info(html, asin = "."):
    try:
        bullets = find_bullets(html)
        descr = find_description(html)
        product = find_product_name(html)
        brand = find_brand(html)
        details = find_details(html)
        tech_details = find_tech_details(html)
        with open(asin+"/info.txt", "w", encoding="UTF-8") as f:
            f.write(product + " by " + brand + "\n")
            f.write("Bullets:\n")
            if len(bullets) == 0:
                f.write("N/A\n")
            else:
                for bullet in bullets:
                    f.write(bullet + "\n")
            f.write("Description\n")
            if descr == None:
                f.write("N/A\n")
            else:
                f.write(descr + "\n")
            f.write("Details\n")
            if details == None or len(details.keys()) == 0:
                f.write("N/A\n")
            else:
                for key in details.keys():
                    f.write(key + " : " + details[key] + "\n")
            f.write("Tech Details\n")
            if tech_details == None or len(tech_details.keys()) == 0:
                f.write("N/A\n")
            else:    
                for key in tech_details.keys():
                    f.write(key + " : " + tech_details[key] + "\n")
        return True
    except Exception as e:
        print("Got exception {0}".format(e))
        return False
        
        
def find_details(html):
    print("Finding product details")
    res = {} 
    try:
        detail_html = html.find(id="prodDetails")
        if detail_html == None:
            detail_html = html.find(id="detail-bullets")
            if detail_html == None:
                print("No details found")
                return None
            for li in detail_html.ul.find_all("li"):
                res[li.b.extract().getText()] = li.getText()
        else:
            for tr in detail_html.table.find_all("tr"):
                th = tr.th.getText().strip()
                if th.replace(" ","").lower() == "customerreviews":
                    res[th] = tr.td.br.getText().strip()
                else:
                    res[th] = tr.td.getText().strip()
                
            
    except Exception as e:
        print("Got exception {0}".format(e))
    return res
        
def find_tech_details(html):
    print("Finding product technical details")
    res = {} 
    try:
        detail_html = html.find(id="technicalSpecifications_feature_div")
        if detail_html == None:
            print("No details found")
            return None
        for table in detail_html.find_all("table"):
            for row in table.find_all("tr"):
                res[row.th.getText()] = row.td.getText()
        return res            
    except Exception as e:
        print("Got exception {0}".format(e))
    return res

            
def find_product_name(html):
    print("Finding product name")
    try:
        return html.find(id="productTitle").getText().strip()
    except Exception:
        print("Exception while trying to get product name")
        return None
            
def find_brand(html):
    print("Finding brand")
    try:
        return html.find(id="brand").getText().strip()
    except Exception:
        print("Exception while trying to get product brand")
        return None
            
def find_bullets(html):
    print("Finding feature bullets")
    try:
        bullets = [bullet.getText().strip() for bullet in html.find(id="feature-bullets").find_all("li")]
        return bullets
    except Exception:
        print("Exception while trying to parse feature bullets")
        return None

def find_description(html):
    print("Checking for product description")
    prod__iframe = [framescript.getText() for framescript in html.find_all("script") if re.search(r"var iframeContent",framescript.getText())]
    product_html = None
    if len(prod__iframe) == 0:
        print("Product Description iFrame was not found!")
        return None
    else:
        obj = re.search(r"var iframeContent\s*=\s(.*?);",prod__iframe[0])
        if obj:
            try:
                product_html = bs(parse.unquote(obj.group(1)), "html.parser")
                return product_html.find(class_="productDescriptionWrapper").getText().replace("\n", "").strip()
            except Exception as e:
                print("Exception when trying to parse product description")
                return None
        else:
            return None
    
    

    

def parse_url_for_images(html):
    #data = None
    #with open("test1.txt","r", encoding="UTF-8") as f:
    #    data = f.read().replace("\n","")
    print("Searching for Javascript segment that has image urls")  
    obj = None
    for script in html.find_all("script"):
        obj = re.search(r"P.when\(\'A\'\).register\(\"ImageBlockATF.*?colorImages.*?initial[\'\"]*?.*?(\[\{.*?\]\}).*?colorToAsin",script.getText().replace("\n",""))
        if obj != None:
            break
    if obj == None:
        print("Something went wrong. No such segment exists")
        return
    data = obj.group()
    obj = re.search(r"(\[\{.*\]\})",data)
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
        #print(item)
        obj = re.search(r"(.*)\:(http.*)", item)
        if obj != None:
            #print("For type " + obj.group(1) + " URL is " + obj.group(2))
   
            try:
                images[obj.group(1)] += [obj.group(2)]
            except KeyError:
                images[obj.group(1)] = [obj.group(2)]
    print("Done")
    return images
    
    
def parse_asin_file():
    with open("asin.txt","r") as f:
        asin_list = [line for line in f.read().split("\n") if line != ""]
    return asin_list
        

def main():
    global USE_CACHE
    global AUTO_OPEN_EDITOR
    parser = optparse.OptionParser('usage%prog [--cache] [--auto-open-editor]')
    parser.add_option('--cache', dest='do_cache', type='string', help='cache html files')
    parser.add_option('--auto-open-editor', dest='auto_edit', type='string', help='automatically open editor')
    (options, args) = parser.parse_args()
    do_cache= options.do_cache
    auto_edit = options.auto_edit
    if do_cache:
        USE_CACHE = True
        print("CACHE flag is set")
    if auto_edit:
        AUTO_OPEN_EDITOR = True
        print("AUTO_OPEN flag is set")
    print("Starting with CACHE %s and AUTO_EDIT %s" % ( USE_CACHE, AUTO_OPEN_EDITOR))
    #test_threading()
    run()
    
if __name__ == '__main__':
    main()

        