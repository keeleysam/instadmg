#!/bin/bash

# This script will create a default home for the instadmg user.
# instadmg 10.5
# Josh Wisenbaker 2/17/2008


#Make the home
/usr/bin/ditto /System/Library/User\ Template/English.lproj/ /Users/instadmg
/usr/sbin/chown -R instadmg:staff /Users/instadmg

exit 0
