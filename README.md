# Library experiments

This repo contains some of my experiments with libraries (as in books).

I like to loan out my books, so they can be read by more people! I am building
tools to make loaning out books easier.


note: zxing can be used to scan barcode, and include it in a web request:
https://github.com/zxing/zxing/wiki/Scanning-From-Web-Pages

  http://zxing.appspot.com/scan? 
    ret=http%3A%2F%2Ffoo.com%2Fproducts%2F%7BCODE%7D%2Fdescription
    &SCAN_FORMATS=UPC_A,EAN_13

## Ideas

### OPDS server

  lots of these have been written already. what's one more?!
  opds loans can be done using indirectAquisition links:
    https://github.com/Feedbooks/opds-test-catalog/blob/gh-pages/catalog/acquisition/sample_borrow.xml

### Loan service.

  This aspect of the service is for loaning out books to others. Either by
having others browse the OPDS catalog, or by directly "checking out" a book to
someone.

## Implementation

## Data models:
  * Book (isbn, title, desc, author, etc)
  * Person (name, oauth token)
  * Loan (Person, book, date, type)
    * type: Loan, Interest/Hold.

