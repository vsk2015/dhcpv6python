#!/usr/bin/python

from optparse import OptionParser
from optparse import Option
from datetime import datetime
import itertools
import sys
import os

parse_dict = {}

config_file = "/home/ubuntu/v6-customers.conf" # path to dhcpv6_cus config file


class extendAction(Option):

    ACTIONS = Option.ACTIONS + ("extend",)
    STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
    TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)
    ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extend",)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "extend":
            lvalue = value.split(",")
            values.ensure_value(dest, []).append(lvalue)
        else:
            Option.take_action(
                self, action, dest, opt, value, values, parser)


def getCommandLineArgs():
    usage = "usage: ./%prog [option] [argument]"
    parser = OptionParser(option_class=extendAction,usage=usage, version="%prog 1.0")
    parser.add_option("-a", "--add",action="extend",type="string",dest="add_portid",help="add a customer port-id")
    parser.add_option("-d", "--del",action="extend", type="string", dest="del_portid",help="del a customer port-id")
    parser.add_option("-c", "--cus",action="extend", type="string", dest="cus_name",help="name of customer")
    parser.add_option("-l", "--list",action="store_true",dest="lst",default=False,help="list all customer port-id")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        print ("incorrect number of  arguments")
        exit(1)
    else:
        add_portid = options.add_portid
        del_portid = options.del_portid
	cus_name = options.cus_name
	if not add_portid and cus_name:
	    print "Please provide sufficient Port-Ids. Script failed."
	    sys.exit(1)
	if cus_name and add_portid:
	    while len(cus_name) < len(add_portid):
 	        cus_name.append([])
	    for j,i in itertools.izip_longest(cus_name,add_portid):
                if j and i:
	            j[0] = '"%s"' %j[0]
	        elif j and not i:
	            print "Please provide sufficient Port-Ids. Script failed."
		    sys.exit(1)
	        elif i and not j:
	            j.append('customer-%s' %i[0])
	            print "Auto generated <customer_name> = 'customer'-'port-id' : %s" %j[0]
	if not cus_name and add_portid:
	    cus_name=[]
	    for k in add_portid:
	    	cus_name_1=[]
		cus_name_1.append('customer-%s' %k[0])
		print "Auto generated <customer_name> = 'customer'-'port-id' : \"customer-%s\"" %k[0] 
	        cus_name.append(cus_name_1)
        lst = options.lst
  	
    return (add_portid, del_portid, cus_name, lst)


def dhcpParser():
    global parse_dict
    fobj = open(config_file)
    for line in fobj:
        line.rstrip()
        line_split = line.split()
        if 'class' in line_split:
            cus_name = line_split[1]
            
        if 'match' in line_split:
            port_id = line_split[6]
            port_id_1 = port_id.strip(';')
            parse_dict[port_id_1]= [cus_name]
        if 'range6' in line_split:
            range6 = line_split[1]
            range6_1 = range6.strip(';')
        if 'allow' in line_split:
            range6_cus = line_split[3]
            range6_cus_1 = range6_cus.strip(';')
            for p, c in parse_dict.iteritems():
                if c[0] == range6_cus_1:
                    parse_dict[p].append(range6_1)
    fobj.close()        
    return parse_dict


def customerAdd(port_id_in, cust_name_in ):
    global parse_dict
    cust_name = cust_name_in
    port_id = port_id_in
    ipv6block = lookUpIpv6() 
    parse_dict[port_id]=[cust_name, ipv6block]
    print "Customer name:%s with port-id %s added" %(parse_dict[port_id][0], port_id)
    return parse_dict


def customerDel(port_id_in):
    global parse_dict
    port_id = port_id_in
    if port_id in parse_dict.keys():
        cus_name = parse_dict[port_id][0]
        del parse_dict[port_id]
        if port_id not in parse_dict.keys():
            print "Customer name:%s with port-id %s deleted" %(cus_name, port_id)
	else: 
	    print "Failed: Script needs to be debugged"
    else:
	print "PortId %s doesn't exist" %port_id
    return parse_dict


def customerList():
    global parse_dict
    for p  in sorted(parse_dict.iterkeys()):
        print p, parse_dict[p]
    if bool(parse_dict):
	pass
    else:
        print "No customer configuration in the FILE"

def lookUpIpv6(): 
    global parse_dict
    ipv6BlockList = []
    for j in range(len(parse_dict.values())):
        ipv6BlockList.append(parse_dict.values()[j][1]) 

    i = 0
    while i <= 65535:
        forty8 = "2600:8C09:0000:"
        sixty4 = ":0:1::/124"
        insert = hex(i).split('x')[1]
	if len(insert) == 1:
            insert = "000%s" %insert
        if len(insert) == 2:
            insert = "00%s" %insert
        if len(insert) == 3:
            insert = "0%s" %insert
        if len(insert) == 4:
            insert = "%s" %insert
        ipv6Block = "%s%s%s" %(forty8,insert,sixty4)
        if ipv6Block in ipv6BlockList:
            i += 1
        else:
            break
    return ipv6Block


def createFile(**parse_dict_in):
    fobj = open(config_file, "w")
    parse_dict_in = parse_dict_in
    for p in sorted(parse_dict_in.iterkeys()):
        stringClass = """
class %s {
   match if v6relay(1, option dhcp6.interface-id) = %s; 
}
""" %(parse_dict_in[p][0], p)
        fobj.write(stringClass)
    stringRange ="""shared-network production-testing {
       subnet6 2600:8C09:0000::/48 {\n"""
    fobj.write(stringRange)
    for p in sorted(parse_dict_in.iterkeys()):
	stringRange1 = """            pool6 {
                    range6 %s;
                    allow members of %s;
            }\n""" %(parse_dict_in[p][1], parse_dict_in[p][0])
        fobj.write(stringRange1)
    stringCurls ="""	}
}\n"""
    fobj.write(stringCurls)
    fobj.close()	
def main ():
    global parse_dict
    parse_dict = dhcpParser()
    (add_portid, del_portid, cus_name, lst) = getCommandLineArgs()
    cus_nameList = []
    for j in range(len(parse_dict.values())):
        cus_nameList.append(parse_dict.values()[j][0])

    if add_portid and not del_portid and not lst:
        for j,k in itertools.izip_longest(cus_name,add_portid):
	   k[0] = '"%s"' %k[0]
           j[0] = '"%s"' %j[0]
    	   if j[0] in cus_nameList:
	      print "Please provide a unique <customer name>, customer name %s exists. Customer name is case sensitive. Script Failed" %j[0]
	      exit(1)
	   if k[0] in parse_dict:
	      print "Please provide unique Port-Id. %s Port-Id exists. Script Failed" %k[0]
              exit(1)
	   else:
              d = customerAdd(k[0], j[0])
              createFile(**d)
    elif del_portid and add_portid:
        print "One operation at a time only... Script failed!!!"
        exit(1)
    elif del_portid and not lst:
        for l in del_portid:
	   l[0] = '"%s"' %l[0]
           d = customerDel(l[0])
           createFile(**d)
    elif lst and not del_portid:
        customerList()
    else:
	print "Please use help : '%s -h'" %sys.argv[0]
if __name__ == '__main__':
    main()

