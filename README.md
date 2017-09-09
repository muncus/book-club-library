# Library experiments

This repo contains some of my experiments with Book libraries.

I like to loan out my books, so they can be read by more people! I am building
tools to make loaning out books easier.

I'm also in a book swap club, and we trade a lot of books around.

This app is intended for use from mobile phones, as it uses the links with the
[zxing](github.com/zxing/zxing) protocol to scan barcodes. These links will not
work as intended on a non-mobile computer.

note: zxing can be used to scan barcode, and include it in a web request:
https://github.com/zxing/zxing/wiki/Scanning-From-Web-Pages

  http://zxing.appspot.com/scan? 
    ret=http%3A%2F%2Ffoo.com%2Fproducts%2F%7BCODE%7D%2Fdescription
    &SCAN_FORMATS=UPC_A,EAN_13

### Development

* Make a new virtualenv: `virtualenv env`
* link virtualenv's lib dir to lib: `ln -s env/lib/python2.7/site-packages/ lib` (helps prevent library skew between the virtualenv and the lib directory used by App Engine.
* activate the virtualenv: `source env/bin/activate`
* Install requirements: `pip install -r requirements.txt`
* Deploy it somewhere (assumes gcloud is setup): `gcloud app deploy app.yaml`

## Further Ideas

### OPDS server

  lots of these have been written already. what's one more?!
  opds loans can be done using indirectAquisition links:
    https://github.com/Feedbooks/opds-test-catalog/blob/gh-pages/catalog/acquisition/sample_borrow.xml

