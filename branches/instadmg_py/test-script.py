#!/usr/bin/env python

from __future__ import with_statement

import sys, os, logging, new, time
from instadmg import dmgContainer, setupLogger, tempFolder, processObject, pkgInstaller, folderContainer, loggedSubprocess
os.chdir( os.path.dirname(sys.argv[0]) )

logging.getLogger().setLevel( logging.DEBUG3 )
setupLogger(level=logging.DEBUG3)
#setupLogger(target="/tmp/detailLog", level=logging.DEBUG3, formatter='%(message)s')


logging.section('###### Start Logging test ######')
logging.critical('critical')
logging.error('error')
logging.warning('warning')

logging.section('section')
logging.process('process')
logging.info('info')

logging.debug('debug')
logging.debug2('debug2')
logging.debug3('debug3')
logging.section('###### End Logging test ######')

print("")

logging.section('###### Start Logged Subprocess test ######')
logging.process('List output (ls testing)')
loggedSubprocess(['/bin/ls', 'testing'], timeOut=None, logLevel=logging.INFO)
logging.process('Error output (ls /doesnotexist)')
loggedSubprocess(['/bin/ls', '/doesnotexist'], timeOut=None, errorLevel=logging.INFO)
logging.process('Timeout output')
loggedSubprocess(['/bin/sleep', '5'], timeOut=1, logLevel=logging.DEBUG3, errorLevel=logging.INFO)
logging.section('###### End Logged Subprocess test ######')

print("")

logging.section('###### Start DMG test ######')

dmgContainer.checksumAtMount = False
dmgContainer.fsckAtMount = False

with tempFolder():

	logging.process('Starting %s' % 'Test A')
	with processObject(
		containerType=dmgContainer, installerType=pkgInstaller,
		name="TestA", source='testing/TestA/TestA.dmg', useShadowFile=True,
		checksum='aeca2a04481fef3e7d79120f6744bfc92d22ba84') as testItem:
				
		for thisItem in testItem.listComponents():
			logging.info('Installer item: %s' % thisItem)
	logging.process('Done with %s' % 'Test A')
	
	logging.process('Starting %s' % 'Test B')
	with processObject(
		containerType=folderContainer, installerType=pkgInstaller,
		name="TestB", source='testing/TestB/',
		checksum='17dc6616ed1ab342d502453f919eab2891c43ef1') as testItem:
				
		for thisItem in testItem.listComponents():
			logging.info('Installer item: %s' % thisItem)
	logging.process('Done with %s' % 'Test B')

logging.section('###### End DMG test ######')
