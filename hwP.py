#------------------------------------------------------------------------------
# IMPORTS ---------------------------------------------------------------------
#------------------------------------------------------------------------------

import urllib.request          # fetching internet resources
import re                      # pattern-matching via regular expressions
import datetime                # getting current date and time
import argparse

#------------------------------------------------------------------------------
# GLOBALS ---------------------------------------------------------------------
#------------------------------------------------------------------------------

portfolio = {}

#------------------------------------------------------------------------------
# FUNCTIONS -----------------------------------------------------------------
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------

def intern_portfolio(args):

    
    y = args.portfolio
    ports = y[0].split(",")                   # makes all of the portfolios into a list

    ignore = re.compile( "(\s+$)|(\s*#)" )
    
    for i in range(len(ports)):
        f = open(ports[i], "r")                 #for loop for reading the list of portfolios
        while True:
            line = f.readline()                 
            if line == "":                      
                break                           
            m = ignore.match(line)              
            if m != None:                       
                continue                        
            
            [symbol,number,avg_cost] =line.split()
        
            number = int(number)                     
            avg_cost = float(avg_cost)
            if symbol in portfolio:             # This if statement was for checking if
                                                #the symbol was already in the dictionary. Then
                                                #it adjusted the average cost and the number
                                                #of shares.
                folder= portfolio[symbol]
                numShares= folder[0]
                avgPrice= folder[1]
                total=numShares+number
                newAvgPrice= ((numShares*avgPrice)+(number*avg_cost))/total
                portfolio[symbol]=[total,newAvgPrice]
            else:
                portfolio[symbol] =  [number, avg_cost]  # create dict entry for symbol
        f.close()

    return portfolio

# This takes the argparse team's arguments and turns them into a dictionary. The function then
# returns that dictionary.

#------------------------------------------------------------------------------

def evaluate_portfolio(x, y, z):

    tot = 0.0;  deltatot = 0.0;  adv = 0;  decl = 0
    
    symbols = list(y.keys())         # gather dict keys into a list
    symbols.sort()                           # sort the list
    req = build_quote_request(symbols)     # format keys for online look-up

    # send request for quotes to server and save handle to quotes
    conn = put_request(req)

    # date/time stamp the report
    print(datetime.datetime.now(), "\n")

    # print report column headers
    print( "{0:<8} {1:>9} {2:>6} {3:>6} {4:<9}\n".format(
            "SYMBOL", "#SHRS", "PRICE", "COST", "GAIN/LOSS") )

    # receive and process quotes from server
    quotes = get_response(conn)
    
    for q in quotes:
        numshares = y[q[0]][0]
        sharecost = y[q[0]][1]
        value = numshares * q[1]
        delta = value - (numshares * sharecost)
        if delta > 0:
            adv += 1
        elif delta < 0:
            decl += 1
        else:
            neutr += 1
        deltatot += delta
        tot += value
        print( "{0:<8} {1:>9d} {2:6.02f} {3:6.02f} {4:+9.02f}".format(
               ("*" + q[0]) if (q[1] < 0.0) else q[0],
               numshares, q[1], sharecost, delta ))
        
        if q[1] < 0.0:      #may noy not need
            z += 1

    print( "\nPortfolio Value = {0:.02f} ({1:+.02f}), advances/declines: {2}/{3}\n".
           format(tot, deltatot, adv, decl))

    # knock down connection with quote server
    conn.close()

    return z

#------------------------------------------------------------------------------
# Get response from quote server.  Filter out everything but desired data.

def get_response(conn):     #This needs to have the HTML parser

    # initialize list of quotes to return; each quote is two-element list
    # of form [<symbol>,<price>], where <price> is -1.0 if <symbol> is invalid
    quotes = []

    lines2 = conn.read()        #Reads the whole webpage

    #Start of HTML Parser
    from html.parser import HTMLParser

    class MyHTMLParser(HTMLParser):
        global state
        state = [3,3,3,3,"z"]                               #This generates an array of states that are used to append quotes[] properly
        def handle_starttag(self, tag, attrs):              #How the parser handles starttags
            newTag = tag                                    #Generic 
            newAttrs = attrs
            if newTag == "td":                              #Searches for start tag td
                a = newAttrs[0]                             #Sets 'a' to the attribute value at index 0
                if a[0] == "class":                         #Looks at the dattribute value at index 0 and checks if it is class
                    b = a[1]                                #Variable b is equal to the phrase that comes after attribute class
                    b = b.split()                           #Splits the string in a[1] to equal b
                    if b[0] == "col-symbol":                #Looks for specific starting phrase in b[0]
                        symbol = b[3][9:]
                        state[4] = symbol                   #Sets symbol to the accurate symbol for that specific stock
                        state[0] = 0                        #state is Valid
                    if a[1] == "invalid-symbol":            #Looks for invalid symbol phrase in b[0]
                        state[0] = 1                        #state is invalid
                a = newAttrs[0]                             #Sets 'a' to the attribute value at index 0
                if a[0] == "class":                         #Looks at the attribute value at index 0 and checks if it is class
                    b = a[1]                                #Variable b is equal to the phrase that comes after attribute class
                    b = b.split()                           #splits it to find the col-price
                    if b[0] == "col-price":                 #searches for col-price
                        state[3] = 1                        #sets col-price state to valid                        
                    else:                                   #if b[0] is not col-price
                        state[3] = 0                        #sets col-price state to invalid
                        
            if newTag == "span" and state[0] == 1:      #if the next tag is span and state is invalid
                a = newAttrs[0]                         #make the a the first index of attributes
                if a[1] == "no-symbol":                 #if a[1] is no-symbol, set state to no-symbol valid
                   state[1] = 1
                   
            if newTag == "strong" and state[1] == 1:    #looks for the strong tag and if the no-symbol stat is valid
                state[2] = 1                            #sets the state for basically "it's okay to get the data" to valid
                state[1] = 0                            #converts the no-symbol state back to invalid
            else:                                       #if there is a strong tag but the no-symbol is invalid
                state[2] = 0                            #sets the state for "it's okay to get the data" to invalid
 
        def handle_data(self, data):                    #how the parser handles data
            if state[2] == 1:                           #if it's okay to get the data
                symbol = data                           
                quotes.append([symbol, -1.0])           #append quotes[] with the bad symbol state
            if state[3] == 1:                           #if the state of col-price is valid
                if data != "\\n":                       #and if the data of the col-price is not "\\n" (this was due to a new-line thing, so I figured I would just get rid of it)
                    price = data
                    price = round(float(price))         #converts string to float and rounds it
                    quotes.append([state[4], price])    #appends the symbol from above in state[4] and the price of that stock
                
               
    parser = MyHTMLParser()
    parser.feed(str(lines2))
    
    return quotes

#------------------------------------------------------------------------------

def parse_command_line_arguments():
    parser = argparse.ArgumentParser(description='Evaluates portfolios and/or obtains ad hoc price quotes.'
                                         ,epilog='Description:\n'
                                     +'Portfolios are described in tabular form'
                                         +'in external text files, one per portfolio (the exact format of a portfolio'
                                         +' file is described elsewhere).  porteval.pyc parses the portfolio files specified on the'
                                        +'command line, contacts a quote service to obtain current prices for'
          +'the securities named in these portfolios, computes a combined'
          +'valuation report and writes it to standard output.  If no portfolio'
          +'file is given on the command line, but a file named "portfolio.txt"'
          +'is present in the current directory, then that file is parsed by'
          +'default.  To omit portfolio evaluation, specify the -n or --no_report'
          +'option.'

          +'Price quotes for any collection of securities may be obtained by'
          +'specifying the -s or --securities option on the command line,'
          +'providing a list of the ticker symbols corresponding to these'
          +'securities as the argument for this option.  porteval.pyc will contact'
          +'a quote service to obtain current prices for the indicated'
          +'securities and write the resulting price list to standard output.'

          +'If both portfolio evaluation and ad hoc price quotes are requested,'
          +'the portfolio valuation report will precede the ad hoc price quotes.'
          +'If only ad hoc price quotes are desired, be sure to specify the -n'
          +'or --no_report option otherwise, a default portfolio file may be'
          +'processed even if no portfolio files were explicitly given on the'
          +'command line.')
    parser.add_argument('portfolio', nargs='*', type=str,
                           help='file containing a securities portfolio')

    parser.add_argument('-n','--no_report',default=argparse.SUPPRESS ,
                           help='suppress portfolio valuation and reporting')
    parser.add_argument('-s', '--securities',metavar='SECURITIES', dest='check',action='append',
                           help='where SECURITIES is a comma-separated list of ticker'
                            +'symbols for the securities for which price quotes are'
                            +'desired')
    parser.add_argument('-v','--version',action='version', version='%(prog)s 2.0',
                           help='print version identification and exit')
    args = parser.parse_args()
    return args

#---------------------------------------------------------------------------------
#displays notes on the invalid symbols

def display_notes(invsyms):

    # display questionable symbol note
    if invsyms > 0:
        print( "* symbol may be invalid, worthless, or have no quote available\n" )

    return


#------------------------------------------------------------------------------
# Construct request for quotes from array of ticker symbols and return it.

def build_quote_request(securities):

    req = "quotes/" + ",".join(securities)

    return req


#------------------------------------------------------------------------------
# Send request to quote server.

def put_request(req):

    conn = urllib.request.urlopen("http://finance.yahoo.com/" + req)
    
    return conn

#------------------------------------------------------------------------------
# MAIN LINE -------------------------------------------------------------------
#------------------------------------------------------------------------------

invsyms = 0
args = parse_command_line_arguments()
portf = intern_portfolio(args)
invsyms = evaluate_portfolio(args, portf, invsyms)
display_notes(invsyms)
