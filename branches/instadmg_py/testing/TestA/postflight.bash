#!/bin/bash

# the correct way
/usr/bin/touch "$3/Applications/TestA/PostFlight1"

# the wrong way
/usr/bin/touch "/Applications/TestA/PostFlight2"
