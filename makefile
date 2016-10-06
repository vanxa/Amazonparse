all: clean init azparser walmartparser move-dist 

azparser:
	pyinstaller -F -n azparser_win32 src\parsers\azparser.py
	echo "Done"

walmartparser:
	pyinstaller -F -n walmartparser_win32 src\parsers\walmartparser.py
	echo "Done"

move-dist:
	mv dist\azparser_win32.exe azparser\azparser_win32.exe
	mv dist\walmartparser_win32.exe walmartparser\walmartparser_win32.exe



clean-dist:
	rm -rvf dist build 

clean:
	rm -rvf dist build azparser walmartparser

init:
	mkdir azparser
	cp LICENSE template.html azparser
	touch azparser\UPC.txt
	touch azparser\asin.txt
	mkdir walmartparser
	cp LICENSE template.html walmartparser 
	touch walmartparser\UPC_walmart.txt
	touch walmartparser\walmart.txt


