# Amazonparse
Amazon product information parser by ASIN number

Amazon Product Parser V.0.1.1

INSTRUCTIONS
----------------------------------------------------------------------------------------------
1. What is inside?
	productparser.exe is a bundled python executable with all required 
	DLLs and libraries linked. Also, you'll find asin.txt file, which
	contains a list of all the ASIN numbers to process in one run.
----------------------------------------------------------------------------------------------
2. Do I need anything special to run?
	You require Python 3 in order to run
----------------------------------------------------------------------------------------------
2. How to run productparser.exe
	By simple running productparser.exe, the application will start 
   	processing the Amazon URLs, given by the list of ASIN numbers. 
	For each URL, the following instructions will occur: 
	1. The URL file will be fetched from Amazon and a folder will be created
	in which to store the files processed from the URL (the name of the file
    corresponds to the ASIN number). If you've run the application with 
    the --cache flag (more on this below), the application will download 
	and cache the URL file.
	2. The contents of the URL will be parsed to find the product information
	sections and the necessary information will be saved to file info.txt. 
	3. You will be prompted to edit the file (or it will be automatically opened if
	--auto-open-editor options is used when launching the application) and once 
	you're done editing, the application will continue. You need to add the Longtail and 
	Suggested keywords, or the next processing steps will fail. The names of the variables
	must be in the following format
	LongTailKeyword = ....
	SuggestedKeyword{1-9} = ....
	4. The product images will be downloaded and stored in the product's folder and will be 
	renamed and resized (if necessary). 
	5. The application will finish.

----------------------------------------------------------------------------------------------
3. Additional options to pass to the application
	Two options can be supplied on runtime - running productparser.exe -h in command prompt will
	show you a help menu
	productparser.exe -c, --cache - Using either one will set the CACHE flag, which will allow the 
	application to download and store the URLS for future use.
	productparser.exe -a --auto-open-editor - Using this option will allow the application to
	automatically open info.txt for edit, once the product information has been gathered. Afterwards,
	simply saving and closing the editor will allow the application to continue.
----------------------------------------------------------------------------------------------
4. Additional notes
	More later...