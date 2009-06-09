#!/usr/bin/env python

'''

TODO:
	- Use custom exception types (so they can be better handled by callers)
	- Handle cancel events from outside (signals) with some grace
	- Setup the logging object to emulate a file object (maybe)
	- Autodetect the taret type
	- Move the loggedSubprocess to a subclass of subprocess.Popen
	- change the tempfolder class to hold open the enclosing folder untill the end
	- Flat-package containers
	- .app installers
	- silent installer executables
	
	- use the information from 'hdiutil imageinfo' better
	
	- solve the issue of shadow files on already mounted DMG's
	- look into nameing the shadow files a little better
'''

from __future__ import with_statement

import os, tempfile, subprocess, stat, logging, new, shutil
import Foundation

#<!---------------- Logging ------------------>

'''
Here is the logging setup:

critical (50)
error (40)
warning (30)

section (25)
	process (20)
		info (15) - normally 20
			debug (10)
				debug2 (5)
					debug3 (1)
'''

logging.SECTION	= 25
logging.section	= lambda log_message, *args, **kwargs: logging.log(logging.SECTION, log_message, *args, **kwargs)
logging.PROCESS	= 20
logging.process = lambda log_message, *args, **kwargs: logging.log(logging.PROCESS, log_message, *args, **kwargs)
logging.INFO	= 15

logging.DEBUG2	= 5
logging.debug2	= lambda log_message, *args, **kwargs: logging.log(logging.DEBUG2, log_message, *args, **kwargs)
logging.DEBUG3	= 1
logging.debug3	= lambda log_message, *args, **kwargs: logging.log(logging.DEBUG3, log_message, *args, **kwargs)

def loggedSubprocess(processArray, timeOut=None, suppresTimeOutError=False, logLevel=logging.DEBUG3, errorLevel=logging.WARNING):
	import subprocess, time, threading, logging, unicodedata
	
	class printThread(threading.Thread):
		import logging, unicodedata
		inputItem	= None
		logLevel	= None
		process		= None
		
		daemon		= True # automatically make these daemon threads
		
		def __init__(self, process, inputItem, logLevel):
			threading.Thread.__init__(self)
			self.inputItem	= inputItem
			self.logLevel	= logLevel
			self.process	= process
			
			self.start()
		
		def __enter__(self):
			return self
				
		def run(self):
			while self.process.poll() == None:
				thisLine = self.inputItem.readline()
				if thisLine:
					logging.log(self.logLevel, thisLine.strip())
			for thisLine in self.inputItem:
				fixed = unicodedata.normalize('NFKD', unicode(thisLine.strip(), "utf-8")).encode('ASCII', 'replace')
				if fixed:
					logging.log(self.logLevel, fixed)
		
		def __exit__(self, exc_type, exc_value, traceback):
			pass
	
	process = subprocess.Popen(processArray, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	
	logThread = printThread(process, process.stdout, logLevel)
		
	errorThread = printThread(process, process.stderr, errorLevel)
	
	startTime = time.time()
	
	if timeOut:
		while process.poll() == None and time.time() < startTime + timeOut:
			time.sleep(1)
		if process.poll() == None and suppresTimeOutError == False:
			# timed out
			logging.log(errorLevel, 'Processes %s timed out after %s seconds' % (processArray[0], timeOut))
	else:
		while process.poll() == None:
			time.sleep(1)
	
	time.sleep(.005) # allow time for output flush
	
	return process.returncode
	

class tabbedLogger ():
	import logging

	tabbingStep		= 5
	tabbingLevels	= 5
	
	criticalPrefix	= "CRITICAL: "
	errorPrefix		= "ERROR: "
	warningPrefix	= "WARNING: "
	
	def __init__(self, target=None):
		if target:
			if type(target) == type(file):
				self.__class__.__bases__ = (logging.StreamHandler,)
				self.__class__.__bases__[0].__init__(self, target)
			
			elif type(target) == type('string'):
				self.__class__.__bases__ = (logging.FileHandler,)
				self.__class__.__bases__[0].__init__(self, target)
			
			else:
				raise Exception('Unknown target type given to tabbedLogger: %s' % type(target))
		else:
			# Base this off of the StreamHandler
			self.__class__.__bases__ = (logging.StreamHandler,)
			self.__class__.__bases__[0].__init__(self)
	
	def emit(self, record):
		tabLevel = self.tabbingLevels - (int(record.levelno) /  self.tabbingStep)
		if tabLevel < 0:
			tabLevel = 0
		
		if not "tabLevel" in record.__dict__:
			record.tabLevel = 0
			
			# tag along and apply prefixes
			if record.levelno == logging.CRITICAL:
				record.msg = self.criticalPrefix + record.msg
			if record.levelno == logging.ERROR:
				record.msg = self.errorPrefix + record.msg
			if record.levelno == logging.WARNING:
				record.msg = self.warningPrefix + record.msg
		
		if tabLevel > record.tabLevel:
			record.msg = ("\t" * (tabLevel - record.tabLevel)) + record.msg
		elif tabLevel < record.tabLevel:
			record.msg = record.msg[record.tabLevel - tabLevel:]
		
		record.tabLevel = tabLevel	
		logging.StreamHandler.emit(self, record)

def setupLogger(target=None, level=None, formatter=None):
	
	thisHandler = tabbedLogger(target)
	if formatter:
		thisHandler.setFormatter(logging.Formatter(formatter))
	if level:
		thisHandler.setLevel( level )
	logging.getLogger().addHandler(thisHandler)

#<!---------------- tempFolder ---------------->

class tempFolder ():
	import logging, stat
	
	# instance variables
	
	path					= None
	
	folderName				= None
	message					= None
	
	enclosingDirPath		= None
	enclosingDirObject		= None
	
	# class variables
	
	makeTraversableFolders	= True			# if True makse folders that are traversable by group and other
	
	_enclosingDirObjects			= {}
	_defaultEnclosingDirObject		= None
	
	def __init__(self, folderName="tempFolder", enclosingDir=None, message=None, makeTraversableFolders=None):
		
		if enclosingDir == None:
			# use the default enclosing dir
			self.enclosingDirObject = self.getDefaultEnclosingDirObject()
			self.enclosingDirPath = self.enclosingDirObject.path
		
		elif isinstance(enclosingDir, tempFolder):
			self.enclosingDirObject = enclosingDir
			self.enclosingDirPath = self.enclosingDirObject.path
		
		elif type(enclosingDir) == type(str()) and os.path.isdir(enclosingDir):
			# we need to check if this is an object we already have
			for thisEnclosingDirObject in self._enclosingDirObjects:
				if thisEnclosingDirObject.path == enclosingDir:
					self.enclosingDirObject = thisEnclosingDirObject
					self.enclosingDirPath = self.enclosingDirObject.path
			
			if self.enclosingDirObject == None:
				# this is an existing folder that we don't have to worry about
				self.enclosingDirPath = enclosingDir
		
		else:
			raise Exception('Unable to understand what do do with the value given for enclosingDir: %s' % str(enclosingDir))
		
		# some ref-counting to allowed for shared directories
		if self.enclosingDirObject:
			if self.enclosingDirPath in self.__class__._enclosingDirObjects:
				self.__class__._enclosingDirObjects[self.enclosingDirObject.path]['refcount'] += 1
			else:
				self.__class__._enclosingDirObjects[self.enclosingDirObject.path] = {'object':self.enclosingDirObject, 'refcount':1}
		
		# create the folder
		folderNameSeperator = ''
		if not folderName[-1] == '.':
			folderNameSeperator = '.'
		self.path = tempfile.mkdtemp(dir=self.enclosingDirPath, prefix=folderName + folderNameSeperator)
		self.folderName = folderName
		
		if makeTraversableFolders == False:
			pass
		elif makeTraversableFolders == True or self.makeTraversableFolders == True:
			os.chmod(self.path, stat.S_IRWXU | stat.S_IXGRP | stat.S_IXOTH)
		
		if message:
			self.message = message
			logging.debug2('Created %s:	%s %s' % (self.folderName, self.path, self.message))
		else:
			logging.debug2('Created %s:	%s' % (self.folderName, self.path))
	
	def __enter__(self):
		return self
	
	@classmethod
	def getDefaultEnclosingDirObject(cls):
		if not cls._defaultEnclosingDirObject:
			# create it
			cls._defaultEnclosingDirObject = cls(enclosingDir='/tmp', folderName='defaultEnclosingFolder')
			cls._enclosingDirObjects[cls._defaultEnclosingDirObject.path] = {'object':cls._defaultEnclosingDirObject, 'refcount':0}
				
		return cls._defaultEnclosingDirObject
	
	def __exit__(self, exc_type, exc_value, traceback):
		self.__del__()
	
	def __del__(self):
		if not os.path.isdir(self.path):
			return # nothing to do
			# TODO: log this
		
		# TODO: figure out how to log this properly
		if self.message:
			logging.debug2('Removing %s:	%s %s' % (self.folderName, self.path, self.message))
		else:
			logging.debug2('Removing %s:	%s' % (self.folderName, self.path))
		
		# make sure that there is nothing mounted at this point:
		if os.path.ismount(self.path):
			# TODO: logging
			if loggedSubprocess(['/usr/bin/hdiutil', 'unmount', self.path]) != 0:
				loggedSubprocess(['/usr/bin/hdiutil', 'unmount', '-force', self.path])
		
		# wipe out anything that is in the folder
		
		for root, dirs, files in os.walk(self.path, topdown=False):
			for name in files:
				os.remove(os.path.join(root, name))
			for name in dirs:
				if os.path.ismount(os.path.join(root, name)):
					# TODO: logging
					if loggedSubprocess(['/usr/bin/hdiutil', 'unmount', os.path.join(root, name)]) != 0:
						loggedSubprocess(['/usr/bin/hdiutil', 'unmount', '-force', os.path.join(root, name)])
				os.rmdir(os.path.join(root, name))
		
		# wipe out the folder
		os.rmdir(self.path)
		
		
		# take care of the ref-counting and removing objects as they are not needed
		if self.enclosingDirObject != None:
			self.__class__._enclosingDirObjects[self.enclosingDirObject.path]['refcount'] -= 1
			if self.__class__._enclosingDirObjects[self.enclosingDirObject.path]['refcount'] < 1:
				if self.enclosingDirObject == self.__class__._defaultEnclosingDirObject:
					self.__class__._defaultEnclosingDirObject = None
				del self.__class__._enclosingDirObjects[self.enclosingDirObject.path]
		
		self.enclosingDirPath = None
		self.enclosingDirObject = None
		
#<!============== Process Object ==============>

class processObject:
	''' This class creates a dynamic class that is a mix of a container and installer type '''
	
	dynamicClasses	= {}
	
	def __init__(self, containerType=None, installerType=None, source=None, name=None, **kwargs):
		if not containerType or type(containerType) != type(self.__class__):
			raise Exception('%s was missing the containerType or it was not a class' % self.__class__)
		if not containerType or type(installerType) != type(self.__class__):
			raise Exception('%s was missing the installerType or it was not a class' % self.__class__)
		if not source or type(source) != type(str()):
			raise Exception('%s was missing the source or it was not a string' % self.__class__)
		
		thisName = containerType.__name__ + ':' + installerType.__name__
		if not (thisName in self.dynamicClasses):
			self.dynamicClasses[thisName] = new.classobj(thisName, (containerType, installerType, processObject), {})
		self.__class__ = self.dynamicClasses[thisName]
		
		if name:
			self.name = name
		
		self.source = source
		
		self.initContainer(**kwargs)
		self.initInstaller(**kwargs)
	
	def closeContainer(self):
		pass # nothing to do for a folder
		
	def cleanupContainer(self):
		pass # nothing to do for a folder
	
	def __exit__(self, exc_type, exc_value, traceback):
		self.__del__()
	
	def __del__(self):
		self.closeContainer()
		self.cleanupContainer()

#<!============= Container Objects ============>

#<!--------------- Folder Object -------------->

class folderContainer:
	import logging, subprocess, shutil
	
	# class variables
	checksumContainer			= True					# checksum the container
	
	# instance variables
	name						= 'No name provided'	# user-visible name
	
	archiveFile					= None					# path to the local resource file/folder
	checksum					= None
	checksumType				= 'sha1'
	archiveHasBeenChecksummed	= False
	archiveValidated			= False
	
	# working instance variables
	
	_containerPath				= None					# path to local folder-like object that contains the contents, always use the getContainerPath method
		
	def initContainer(self, checksum=None, checksumType=None, **kwargs):
		''' Look for the DMG, but do not mount it yet '''
		
		if not os.path.exists(self.source):
			raise Exception('No file exists at: %s' % self.source)
		else:	
			self.archiveFile = self.source
		
		if checksum:
			self.checksum = checksum
		if checksumType:
			self.checksumType = checksumType
		
		if self.checksum and self.checksumType:
			self.checksumLocal()
		
		self.initContainerSubtype(**kwargs)
		
		self.validateTarget()
	
	def initContainerSubtype(self, **kwargs):
		if len(kwargs) > 0:
			logging.debug3('Unused arguments: %s' % " ".join(kwargs.keys()))
		
	def __enter__(self):
		return self
	
	def getContainerPath(self):
		if not self._containerPath:
			self._containerPath = self.archiveFile
		return self._containerPath
	
	def validateTarget(self):
		''' Make sure that the target looks correct '''
		
		if not os.path.isdir(self.archiveFile):
			raise Exception('Target was not a directory: %s' % self.archiveFile)
		
		self.archiveValidated = True
	
	def checksumLocal(self, targetPath=None, checksum=None, checksumType=None, forceChecksum=False):
		import hashlib
		
		if self.archiveHasBeenChecksummed == True and forceChecksum == False:
			# we can skip this
			return True
		
		if not targetPath:
			if not self.archiveFile:
				raise Exception('Checksum called, but no local file provided (%s)' % self.name)
			targetPath = self.archiveFile
		if not checksum:
			if not self.checksum:
				raise Exception('Checksum called, but no checksum provided (%s)' % self.name)
			checksum = self.checksum
		if not checksumType:
			if not self.checksumType:
				raise Exception('Checksum called, but no checksum type provided (%s)' % self.name)
			checksumType = self.checksumType
		
		if not os.path.exists(targetPath):
			raise Exception('Checksum called, but there is no item at that path: %s' % targetPath)
		
		chunksize = 1 * 1024 * 1024
		hashGenerator = hashlib.new(checksumType)
		
		def checksumFile(fileLocation, hashGenerator):
			with open(fileLocation, 'rb') as hashfile:
				def chunked(f, size):
					while True:
						block = f.read(size)
						if not block:
							break
						yield block
				for thisChunk in chunked(hashfile, chunksize):
					hashGenerator.update(thisChunk)
		
		if os.path.isfile(targetPath):
			checksumFile(targetPath, hashGenerator)
		
		elif os.path.isdir(targetPath):
			for thisFolder, subFolders, subFiles in os.walk(targetPath):
				for thisFile in subFiles:
					
					if '.svn' in thisFolder.split(os.path.sep) or '.cvs' in thisFolder.split(os.path.sep):
						continue 
					
					if thisFile.startswith('.svn') or thisFile.startswith('.cvs'):
						continue
					checksumFile( os.path.join(thisFolder, thisFile), hashGenerator )
		
		else:
			raise Exception('Checksum called on unusual object: %s' % targetPath)
		
		if hashGenerator.hexdigest() != checksum:
			raise Exception('Incorrect checksum on: %s (%s) was: %s should have been: %s' % (targetPath, self.name, hashGenerator.hexdigest(), checksum))
		
		self.archiveHasBeenChecksummed = True
		if self.name:
			logging.debug('%s (%s) passed checksum: %s' % (self.name, targetPath, checksum))
		else:
			logging.debug('%s passed checksum: %s' % (targetPath, checksum))

#<!---------------- DMG Object ---------------->

class dmgContainer (folderContainer):
	# instance variables
	mountObject				= None	# to hold the tempFolder object
		
	useShadowFile			= False	# mount image with a shadow file
	shadowFilePath			= None	# path to the shadow file
	shadowFileAutoGenerated	= False	# if the shadowfile is autogenerated we will clean it up
	
	dmgIsChecksummed		= None
	dmgIsCompressed			= None
	dmgChecksumType			= None
	dmgChecksumValue		= None
	dmgClassName			= None
	dmgFormat				= None
	dmgFormatDescription	= None
	
	# class variables
	
	mountReadOnly			= True	# mount read-only (non-applicaable with a shadow file)
	checksumAtMount			= True	# checksum the image before mouting
	fsckAtMount				= True	# fsck mounted volumes durring mount
	onwnersOn				= True	# turn owners on while mounting
	
	showInFinder			= False
	
	def initContainerSubtype(self, useShadowFile=False, **kwargs):
		if len(kwargs) > 0:
			logging.debug3('Unused arguments: %s' % " ".join(kwargs.keys()))
		self.useShadowFile = useShadowFile
		
	def validateTarget(self):
		self.getDMGInformation()
		# TODO: work on lowering parinoia levels
		if self.dmgChecksumType and self.dmgChecksumValue:
			logging.debug2('Validating internal checksum of DMG: %s' % self.archiveFile)
			if loggedSubprocess(['/usr/bin/hdiutil', 'verify', self.archiveFile], logLevel=logging.DEBUG3, errorLevel=logging.DEBUG2) != 0:
				raise Exception('DMG failed internal checksum: %s' % self.archiveFile)
		
		self.archiveValidated = True
	
	def getDMGInformation(self):
		hdiutilProcess = subprocess.Popen(['/usr/bin/hdiutil', 'imageinfo', '-plist', self.archiveFile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if hdiutilProcess.wait() != 0:
			raise Exception('hdiutil failed to give status information, gave error: %s' % hdiutilProcess.stderr.read())
		
		plistData = hdiutilProcess.stdout.read()
		plistNSData = Foundation.NSString.stringWithString_(plistData).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
				
		plist, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
		if error:
			errStr = err.encode('utf-8')
			err.release()
			raise Exception('hdiutil failed to give properties about %s, gave error: %s' % (self.archiveFile, errStr))
				
		# collect information from the image
		if 'Checksum Type' in plist and plist['Checksum Type'] != "none":
			self.dmgChecksumType = str(plist['Checksum Type'])
			logging.debug3('DMG Checksum Type: %s' % self.dmgChecksumType)
		if 'Checksum Value' in plist and plist['Checksum Value'] != "":
			self.dmgChecksumValue = str(plist['Checksum Value'])
			logging.debug3('DMG Checksum Value: %s' % self.dmgChecksumValue)
		if 'Class Name' in plist:
			self.dmgClassName = str(plist['Class Name'])
			logging.debug3('DMG Class Name: %s' % self.dmgClassName)
		if 'Format' in plist:
			self.dmgFormat = str(plist['Format'])
			logging.debug3('DMG Format: %s' % self.dmgFormat)
		if 'Format Description' in plist:
			self.dmgFormatDescription = str(plist['Format Description'])
			logging.debug3('DMG Format Description: %s' % self.dmgFormatDescription)
		
		if 'Properties' in plist and isinstance(plist['Properties'], Foundation.NSDictionary):
			if 'Checksummed' in plist['Properties'] and type(plist['Properties']['Checksummed']) == type(True):
				self.dmgIsChecksummed = plist['Properties']['Checksummed']
				logging.debug3('DMG is Checksummed: %s' % self.dmgIsChecksummed)
			if 'Compressed' in plist['Properties'] and type(plist['Properties']['Compressed']) == type(True):
				self.dmgIsCompressed = plist['Properties']['Compressed']
				logging.debug3('DMG is Compressed: %s' % self.dmgIsCompressed)
			
		
	def getContainerPath(self):
		# if we have already mounted it, return the value
		if self._containerPath:
			return self._containerPath
		
		self.mount()
		
		return self._containerPath
	
	def mount(self):
		''' Mount the DMG '''
		
		if self.name:
			logging.debug('Mounting %s (%s)' % (self.name, self.archiveFile))
		else:
			logging.debug('Mounting %s' % self.archiveFile)
		
		# check if the image is already mounted
		if self.dmgAlreadyMounted():
			if self.name:
				logging.debug('DMG %s (%s) already mounted at: %s' % (self.name, self.archiveFile, self._containerPath))
			else:
				logging.debug('DMG %s already mounted at: %s' % (self.archiveFile, self._containerPath))
			return
		
		# optionally let diskutility checksum the image
		
		# TODO: work here
		
		# create the mount point
		if self.name:
			self.mountObject = tempFolder(folderName="mountPoint", message="for: %s" % self.name)
		else:
			self.mountObject = tempFolder(folderName="mountPoint", message="for: %s" % self.archiveFile)
		
		if not self.mountObject:
			raise Exception('Unable to create mount point for: %s' % self.archiveFile)
		self._containerPath = self.mountObject.path
		
		# setup the mount options
		mountOptions = ['-private']
		
		# TODO: shadow file
		
		if self.mountReadOnly:
			mountOptions.append('-readonly')
		else:
			# TODO: figure out when this requires a shadow file
			mountOptions.append('-readwrite')
		
		# TODO: setup system with checksum|no checksum|required	
		if self.checksumAtMount:
			mountOptions.append('-verify')
		else:
			mountOptions.append('-noverify')
		
		if not self.showInFinder:
			mountOptions.append('-nobrowse')
		
		if self.fsckAtMount:
			mountOptions.append('-autofsck')
		else:
			mountOptions.append('-noautofsck')
			
		if self.useShadowFile:
			if self.shadowFilePath:
				if os.path.exists(self.shadowFilePath):
					if not os.path.isfile(self.shadowFilePath):
						raise Exception('Preselected shadow file path is not a file: %s' % self.shadowFilePath)
						
					# check to see that that file looks like a shadow file... has 'shdw' as the first four bytes
					checkFile = open(self.shadowFilePath)
					checkData = checkFile.read(4)
					checkFile.close()
					if checkData != 'shdw':
						raise Exception('Existing file does not look like a shadow file: %s' % self.shadowFilePath)
					
				else:
					pass
					# we will not controll this file, but it will be created
			else:
				# note that we are not actually creating the file here, but will let hdiutil do that
				self.shadowFilePath = tempfile.mktemp(dir=tempFolder.getDefaultEnclosingDirObject().path, suffix=".shadow")
				self.shadowFileAutoGenerated = True
		
			mountOptions.append('-shadow')
			mountOptions.append(self.shadowFilePath)
				
		
		mountCommand = ['/usr/bin/hdiutil', 'attach', self.archiveFile] + mountOptions + ['-mountpoint', self._containerPath]
		
		logging.debug3('Mount command: %s' % " ".join(mountCommand))
		
		# mount the DMG
		if loggedSubprocess(mountCommand) != 0:
			self._containerPath = None
			raise Exception('Unable to mount: %s error: %s' % (self.archiveFile, 'TODO'))
		
		logging.debug('Mounted DMG %s at: %s' % (self.name, self._containerPath))
	
	def unmount(self):
		if self.mountObject and self._containerPath:
			if self.name:
				logging.debug('Unmounting disk image:	%s (%s) from: %s' % (self.name, self.archiveFile, self._containerPath))
			else:
				logging.debug('Unmounting disk image:	%s from: %s' % (self.archiveFile, self._containerPath))
			
			if loggedSubprocess(['/usr/bin/hdiutil', 'detach', self._containerPath]) != 0:
				logging.warn('Force unmounting disk image:	%s from: %s' % (self.archiveFile, self._containerPath))
				
				loggedSubprocess(['/usr/bin/hdiutil', 'detach', '-force', self._containerPath], stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE)
			self.mountObject = None
			
			if self.name:
				logging.debug('Unmounted disk image:	%s (%s) from: %s' % (self.name, self.archiveFile, self._containerPath))
			else:
				logging.debug('Unmounted disk image:	%s from: %s' % (self.archiveFile, self._containerPath))
			
			self._containerPath = None
	
	def copyShadowFileToLocation(self, location):
		if not(self.shadowFilePath):
			if self.name:
				raise Exception('Tried to copy the shadow file from a DMG without a shadow file: %s (%s)' % (self.name, self.archiveFile))
			else:
				raise Exception('Tried to copy the shadow file from a DMG without a shadow file: %s' % self.archiveFile)
		self.unmount()
		
		targetDir = None
		targetName = None
		if os.path.isdir(location):
			targetDir = location
			targetName = os.path.basename(self.shadowFilePath)
		
		elif os.path.isdir( os.path.dirname(location) ):
			targetDir = os.path.dirname(location)
			targetName = os.path.basename(location)
		
		if targetDir == None:
			raise Exception('Tried to copy the shadow file from a DMG to a location that does not exist: %s' % location)
		
		logging.debug3('Copying shadow file from: %s to: %s' % (self.shadowFilePath, location))
		shutil.copyfile(self.shadowFilePath, os.path.join(targetDir, targetName))
		
		# we leave the image unmounted, anything that uses it should get it mounted again
			
	def dmgAlreadyMounted(self):
		hdiutilProcess = subprocess.Popen(['/usr/bin/hdiutil', 'info', '-plist'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if hdiutilProcess.wait() != 0:
			raise Exception('hdiutil failed to give status information, gave error: %s' % hdiutilProcess.stderr.read())
		
		plistData = hdiutilProcess.stdout.read()
		plistNSData = Foundation.NSString.stringWithString_(plistData).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
		
		plist, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
		if error:
			errStr = err.encode('utf-8')
			err.release()
			raise Exception('hdiutil failed to give status information, gave error: %s' % errStr)
				
		for mountedImage in plist["images"]:
			if mountedImage["image-path"] == self.archiveFile:
				for entry in mountedImage["system-entities"]:
					if "mount-point" in entry:
						# NOTE: this will not handle cases where there is more than one mounted volume from a dmg
						self._containerPath = str(entry["mount-point"])
						break
				
				if self._containerPath:
					return True
		
		return False
	
	def closeContainer(self):
		''' Unmount DMG '''
		
		# unmount the dmg
		self.unmount()
			
		# the mount point should take care of itself

	def cleanupContainer(self):
		if self.shadowFileAutoGenerated == True and os.path.exists(self.shadowFilePath):
			if self.name:
				logging.debug2('Deleting shadow file for %s (%s): %s' % (self.name, self.archiveFile, self.shadowFilePath))
			else:
				logging.debug2('Deleting shadow file for %s: %s' %  self.archiveFile, self.shadowFilePath)
			os.unlink(self.shadowFilePath)

#<!-------------- Install Steps -------------->

class installItem:
	''' Abstract base class '''
	
	# instance variables
	_installItems	= None
	
	# class variables
	useChroot		= True
	useSeatbelt		= False
	checkItems		= False
	
	def initInstaller(self, **kwargs):
		pass
	
	def listComponents(self):
		return []
	
	def checkComponent(self, path):
		if os.path.exists(path):
			return True
		else:
			return False
	
	def installItem(self, useChroot=None, useSeatbelt=None):
		''' Perform the install '''
		pass
			
	def install(self, useChroot=True, useSeatbelt=False):
		''' Perform the install '''
		for thisItem in self.listComponents():
			logging.info(thisItem)

class pkgInstaller (installItem):
	''' .pkg installer '''
	
	def listComponents(self):
		
		if self._installItems:
			return self._installItems
		
		containingPath = self.getContainerPath()
		
		if self.name:
			logging.debug2('Creating list of items in %s (%s)' % (self.name, self.archiveFile))
		else:
			logging.debug2('Creating list of items in %s' % self.archiveFile)
		
		for thisItem in os.listdir(containingPath):
			
			if thisItem[0] == '.':
				logging.debug3('Item %s ignored as invisible item' % thisItem)
				continue # ignore hidden items
			elif (os.path.splitext(thisItem)[1].lower() == '.pkg' or os.path.splitext(thisItem)[1].lower() == '.mpkg'):
				if self.checkItems == False or self.checkComponent( os.path.join(self.getContainerPath(), thisItem)):
					if self._installItems == None:
						self._installItems = []
					
					self._installItems.append(os.path.join(self.getContainerPath(), thisItem))
					logging.debug3('Added Item %s to installItems' % thisItem)
					continue
			else:
				logging.debug3('Item %s ignored as it did not end in .pkg or .mpkg' % thisItem)
		
		return self._installItems

#<!---------------- Main Stub ----------------->	

if __name__ == '__main__':
	print("This program is not yet ready. If you want to demo what is avalible use test-script.puy")
