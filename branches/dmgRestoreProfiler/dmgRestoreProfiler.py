#!/usr/bin/python

import subprocess, Foundation, time, math

def bytesToRedableSize(sizeInBytes):
	sizeInBytes = float(math.fabs(sizeInBytes))
	if sizeInBytes >= 1024*1024*1024*1024:
		return '%.1f TiB' % (sizeInBytes / (1024*1024*1024*1024))
	elif sizeInBytes >= 1024*1024*1024:
		return '%.1f GiB' % (sizeInBytes / (1024*1024*1024))
	elif sizeInBytes >= 1024*1024:
		return '%.1f MiB' % (sizeInBytes / (1024*1024))
	elif sizeInBytes >= 1024:
		return '%.1f KiB' % (sizeInBytes / 1024)
	else:
		return '%.1f bytes' % sizeInBytes

def secondsToReadableTime(seconds):
	seconds = int(math.fabs(seconds))
	responce = ""
	
	hours = int(math.floor(float(seconds)/(60*60)))
	if hours > 0:
		if hours > 1:
			responce += "%i hours " % hours
		else:
			responce += "%i hour " % hours
		seconds -= hours * 60*60
	
	minutes = int(math.floor(float(seconds)/60))
	if minutes > 0:
		if minutes > 1:
			responce += "%i minutes " % minutes
		else:
			responce += "%i minute " % minutes
		seconds -= minutes * 60
	
	if seconds > 0:
		if seconds > 1:
			responce += "%i seconds" % seconds
		else:
			responce += "%i second" % seconds
	
	if responce == "":
		responce = "less than one second"
	
	return responce.strip()

def mountDMG(thisSourceFile, mountPoint=None, shadowFile=None):
	
	# ToDo: handle the case when mountPoint is not given
	
	print('	Mounting: %s at %s' % (thisSourceFile, mountPoint))
	
	command = ['/usr/bin/hdiutil', 'attach', '-mountpoint', mountPoint, '-noverify', '-noautofsck', '-nobrowse', '-owners', 'on', '-readonly', '-plist', thisSourceFile]
	if shadowFile is not None:
		command += ['-shadow', shadowFile]
	process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	if process.wait() != 0:
		raise Exception('Unable to mount the image: %s\nCommand: %s\nOutput: %s\nError: %s' % (thisSourceFile, " ".join(command), process.stdout.read(), process.stderr.read()))
	
	output = process.stdout.read()
	
	# convert the plist into useable objects
	plistNSData = Foundation.NSString.stringWithString_(output).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
	plist, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
	if error is not None:
		errStr = error.encode('utf-8')
		error.release()
		raise Exception('Unable to mount image: %s\nError: %s' % (thisSourceFile, errStr))
	
	# find the path it is mounted at
	if not 'system-entities' in plist:
		raise Exception('hdiutil output did not look right on mount. Data:\n%s' % output)
	
	for systemEntry in plist['system-entities']:
		if 'mount-point' in systemEntry:
			return systemEntry['mount-point']
	
	# if we get here, then we have failed
	raise Exception('Unable to figure out the mount point for: %s\n%s' % (thisSourceFile, output))

def unmountDMG(mountPoint):
	
	print('	Unmounting: %s' % mountPoint)
	
	if not os.path.ismount(mountPoint):
		raise Exception('The item "%s" was not a mount point, so it can not be unmounted' % mountPoint)
	
	command = ['/usr/bin/hdiutil', 'eject', mountPoint]
	if subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) != 0:
		print('The image did not unmount cleanly, forcing: %s' % mountPoint)
		
		command = ['/usr/bin/hdiutil', 'eject', '-force', mountPoint]
		subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def isValidDMG(pathToDGM):
	hdiutilCommand = ["/usr/bin/hdiutil", "imageinfo", pathToDGM]
	if subprocess.call(hdiutilCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0:
		return True
	else:
		return False

if __name__ == "__main__":
	import optparse, sys, os, Foundation, re, tempfile, shutil
	
	if os.geteuid() != 0:
		sys.stderr.write("Error: in order to restore volumes this command must be run with root permissions (sudo works)\n")
		sys.exit(1)
	
	optionParser = optparse.OptionParser(usage="usage: %prog --restore-volume=VOLUME [options] [test1.dmg [test2.dmg [...]]]")
	optionParser.add_option("-r", "--restore-volume", dest="restoreVolume", type="string", action="store", default=None, help="Restore over this volume. WARNING: all data on this volume will be lost!", metavar="Volume")
	(options, arguments) = optionParser.parse_args()
	
	restorePoint = None
	restorePointName = None
	restorePointSizeInBytes = None
		
	if options.restoreVolume == None:
		sys.stderr.write("Error: To test the restore speed a volume to restore is required.\n\n")
		optionParser.print_help()
		sys.exit(1)
	
	# check the volume that we are going to restore to, and make sure we have the /dev entry for it
	
	elif re.search("^/dev/disk\d+s+\d+$", options.restoreVolume) or re.search("^disk\d+s+\d+$", options.restoreVolume):
		# we have a dev entry, make sure it is valid, not the one we are standing on, and the media is writable
		# note: we will confirm that it is big enough for the images later
		
		devEntry = options.restoreVolume
		if not devEntry.startswith("/dev/"):
			devEntry = "/dev/" + options.restoreVolume
		
		diskutilCommand = ["/usr/sbin/diskutil", "info", "-plist", devEntry]
		diskutilProcess = subprocess.Popen(diskutilCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if diskutilProcess.wait() != 0:
			# there was some problem, so this is probably not a valid dev entry
			sys.stderr.write("Error: unable to verify restore volume %s. diskutil gave error code: %i and the message: '%s'\n" % (options.restoreVolume, diskutilProcess.returncode, diskutilProcess.stdout.read().strip()))
			sys.exit(1)
		
		diskutilOutput = diskutilProcess.stdout.read()
		
		# convert the info into readable data
		plistNSData = Foundation.NSString.stringWithString_(diskutilOutput).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
		plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
		if error:
			sys.stderr.write('Error: Unable to convert the diskuitl info output for %s to a plist, got error: %s\nOutput was:\n%s\n' % (error, devEntry, diskutilOutput))
			sys.exit(1)
		
		# make sure that this is not the root volume
		if "MountPoint" in plistData and plistData["MountPoint"] == "/":
			sys.stderr.write("Error: cannot use the root volume as the restore volume\n")
			sys.exit(1)
		
		if "VolumeName" in plistData:
			restorePointName = plistData["VolumeName"]
		
		restorePointSizeInBytes = plistData["TotalSize"]
		restorePoint = devEntry
	
	elif os.path.ismount(options.restoreVolume):
		# we have a mountpoint, and need to translate to a dev entry
		
		diskutilCommand = ["/usr/sbin/diskutil", "info", "-plist", options.restoreVolume]
		diskutilProcess = subprocess.Popen(diskutilCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if diskutilProcess.wait() != 0:
			# there was some problem, so this is probably not a valid dev entry
			sys.stderr.write("Error: unable to verify restore volume %s. diskutil gave error code: %i and the message: '%s'\n" % (options.restoreVolume, diskutilProcess.returncode, diskutilProcess.stdout.read().strip()))
			sys.exit(1)
		
		diskutilOutput = diskutilProcess.stdout.read()
		
		# convert the info into readable data
		plistNSData = Foundation.NSString.stringWithString_(diskutilOutput).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
		plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
		if error:
			sys.stderr.write('Error: Unable to convert the diskuitl info output for %s to a plist, got error: %s\nOutput was:\n%s\n' % (error, devEntry, diskutilOutput))
			sys.exit(1)
		
		# make sure that this is not the root volume
		if "MountPoint" in plistData and plistData["MountPoint"] == "/":
			sys.stderr.write("Error: cannot use the root volume as the restore volume\n")
			sys.exit(1)
		
		if "VolumeName" in plistData:
			restorePointName = plistData["VolumeName"]
		
		restorePointSizeInBytes = plistData["TotalSize"]
		restorePoint = "/dev/" + plistData["DeviceIdentifier"]
	
	else:
		# we have fallen through all the cases we know, and don't understand the target volume
		sys.stderr.write("Error: could not find the restore volume: %s\n" % options.restoreVolume)
		sys.exit(1)
	
	
	if len(arguments) == 0:
		arguments.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "../OutputFiles")))
	
	sourceFiles = {}
	
	# check the arguments as valid sources
	for thisArgument in arguments:
				
		if os.path.isdir(thisArgument): # see if it is a folder of dmg's
			# Possible ToDo: recurse into directories
			foundFiles = []
			for thisFile in os.listdir(thisArgument):
				if not thisFile.lower().endswith(".dmg"):
					continue
				
				resolvedPath = os.path.realpath(os.path.join(thisArgument, thisFile))
				
				if isValidDMG( resolvedPath ):
					foundFiles.append( resolvedPath )
				else:
					sys.stderr.write("Warning: file is not a valid dmg: %s\n" % resolvedPath)
			
			if len(foundFiles) > 0:
				for thisFile in foundFiles:
					sourceFiles[thisFile] = True
			else:
				sys.stderr.write("Error: folder does not contain any valid dmgs: %s\n" % thisArgument)
				sys.exit(1)
		
		elif os.path.isfile(thisArgument):
			resolvedPath = os.path.realpath(thisArgument)
			
			if isValidDMG( resolvedPath ):
				sourceFiles[resolvedPath] = True
			else:
				sys.stderr.write("Error: file is not a valid dmgs: %s\n" % thisArgument)
				sys.exit(1)
		
		else:
			sys.stderr.write("Error: argument given was neither a dmg file, nor a folder of dmgs: %s\n" % thisArgument)
			sys.exit(1)
	
	assert len(sourceFiles) > 0, "There were no valid source files, this should not be possible"	
	
	# confirm that all of the images are restoreable onto the target volume
	for thisImage in sourceFiles.keys():
		diskutilCommand = ["/usr/bin/hdiutil", "imageinfo", "-plist", thisImage]
		diskutilProcess = subprocess.Popen(diskutilCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if diskutilProcess.wait() != 0:
			# there was some problem, so this is probably not a valid dev entry
			sys.stderr.write("Error: unable to verify restore volume %s. diskutil gave error code: %i and the message: '%s'\n" % (options.restoreVolume, diskutilProcess.returncode, diskutilProcess.stdout.read().strip()))
			sys.exit(1)
		
		diskutilOutput = diskutilProcess.stdout.read()
		
		# convert the info into readable data
		plistNSData = Foundation.NSString.stringWithString_(diskutilOutput).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
		plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
		if error:
			sys.stderr.write('Error: Unable to convert the diskuitl info output for %s to a plist, got error: %s\nOutput was:\n%s\n' % (error, devEntry, diskutilOutput))
			sys.exit(1)
		
		if int(plistData["Size Information"]["Total Non-Empty Bytes"]) > restorePointSizeInBytes:
			sys.stderr.write('Error: image %s takes more space than is avalible on the target volume (%s vs. %s)\n' % (thisImage, bytesToRedableSize(plistData["Size Information"]["Total Non-Empty Bytes"]), bytesToRedableSize(restorePointSizeInBytes)))
			sys.exit(1)
	
	# tell the user what we will be processing	
	pluralEnding = ""
	if len(sourceFiles) > 1:
		pluralEnding = "s"
	targetVolumeDisplay = restorePoint
	if restorePointName != None:
		targetVolumeDisplay = "'%s' (%s)" % (restorePointName, restorePoint)
	
	print("Profiling will be done by restoring to %s using the following dmg%s:\n\t%s\n" % (targetVolumeDisplay, pluralEnding, "\n\t".join(sourceFiles.keys())))
	
	# warn the user
	choice = raw_input('WARNING: All data on the volume %s will be ERASED! Are you sure you want to continue? (Y/N):' % targetVolumeDisplay)
	if not( choice.lower() == "y" or choice.lower() == "yes" ):
		print("Canceling")
		sys.exit()
	
	print ("\nTesting will now start. This can take a very long time.\n\n==================Start testing data==================")
	
	# grab the relevent data from system_profiler
	systemProfilerCommand = ["/usr/sbin/system_profiler", "-xml", "SPHardwareDataType"]
	systemProfilerProcess = subprocess.Popen(systemProfilerCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	if systemProfilerProcess.wait() != 0:
		# there was some problem, so this is probably not a valid dev entry
		sys.stderr.write("Error: Unable to get system profiler information with command: %s\nRecieved error number: %i with message: %s\n" % (" ".join(systemProfilerCommand), systemProfilerProcess.returncode, systemProfilerProcess.stdout.read().strip()))
		sys.exit(1)
		
	systemProfilerOutput = systemProfilerProcess.stdout.read()
	
	plistNSData = Foundation.NSString.stringWithString_(systemProfilerOutput).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
	plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
	if error:
		sys.stderr.write('Error: Unable to convert the diskuitl info output for %s to a plist, got error: %s\nOutput was:\n%s\n' % (error, devEntry, systemProfilerOutput))
		sys.exit(1)
	
	print("Computer Type:\t%(machineName)s (%(machineModel)s)" % {"machineName":plistData[0]["_items"][0]["machine_name"], "machineModel":plistData[0]["_items"][0]["machine_model"]})
	print("Processor:\t%(processorSpeed)s %(processorType)s" % {"processorSpeed":plistData[0]["_items"][0]["current_processor_speed"], "processorType":plistData[0]["_items"][0]["cpu_type"]})
	print("Memory:\t\t%(memorySize)s" % {"memorySize":plistData[0]["_items"][0]["physical_memory"]})
	
	
	# ToDo: print out the information about the disk the restore volume is on
		
	# create a tempfile location for asr to write onto

	
	# create the tempMountPoint to mount the image to
	tempMountPoint = tempfile.mkdtemp(suffix="-mountPoint", prefix=os.path.basename(sys.argv[0]), dir="/tmp")
	
	# create a tempfile for hdiutil to write onto
	hdiutilOutfilePath = tempfile.mktemp(suffix=".dmg", prefix=os.path.basename(sys.argv[0]), dir="/tmp")
	
	# create a shadowfile location so we can fsck mounted images
	shadowFileLocation = tempfile.mktemp(suffix=".shadow.dmg", prefix=os.path.basename(sys.argv[0]), dir="/tmp")
	
	# process things
	for thisSourceFile in sourceFiles.keys():
		
		# the source options to use
		sourceOptions = [
			{"message":"Creating image from volume", "command":["/usr/bin/hdiutil", "create", "-nocrossdev", "-ov", "-srcfolder", tempMountPoint, hdiutilOutfilePath], "mountImage":True},
			{"message":"Converting dmg image directly", "command":["/usr/bin/hdiutil", "convert", thisSourceFile, "-o", hdiutilOutfilePath, "-ov"]}
		]
		
		# output options to use		
		outputOptions = [
			{"message":" using ADC compression ", "command":["-format", "UDCO"]}, # ADC-compressed image
			{"message":" using zlib compression level 1 (fast) ", "command":["-format", "UDZO", "-imagekey", "zlib-level=1"]}, # zlib-compressed image - fast
			{"message":" using zlib compression level 6 (default) ", "command":["-format", "UDZO", "-imagekey", "zlib-level=6"]}, # zlib-compressed image - default
			{"message":" using zlib compression level 9 (smallest) ", "command":["-format", "UDZO", "-imagekey", "zlib-level=9"]}, # zlib-compressed image - fast
			{"message":" using bzip2 compression ", "command":["-format", "UDBZ"]} # bzip2-compressed image
		]
		
		# asr scanning options
		asrImagescanOptions = [
			{"message":"without file checksums ", "command":[]},
			{"message":"with file checksums ", "command":["--filechecksum"]}
			# ToDo: play with buffers
		]
		
		# ToDo: play with buffers 
		
		for thisSourceOption in sourceOptions:
			print("\n" + thisSourceOption["message"] + "\n------------------")
			
			if "mountImage" in thisSourceOption and thisSourceOption["mountImage"] == True:
				mountDMG(thisSourceFile, mountPoint=tempMountPoint, shadowFile=shadowFileLocation)
				
				# fsck the file to rebuild the file catalog
				#command = ['/sbin/fsck_hfs', '-r', tempMountPoint]
				#print("\tfsck'ing command: " + " ".join(command))
				#process = subprocess.Popen(command)
				#if process.wait() != 0:
				#	raise Exception('Processes: %s\nReturned: %i with output:\n%s\nAnd error: %s' % (' '.join(command), process.returncode, process.stdout.read(), process.stderr.read()))	
			
			for thisOutputOption in outputOptions:
				
				# make sure that there is something at the output location
				open(hdiutilOutfilePath, "w").close()
				
				print("\t" + thisSourceOption["message"] + thisOutputOption["message"])
				command = thisSourceOption["command"] + thisOutputOption["command"]
				print("\t\tCommand: " + " ".join(command))
				
				startTime = time.time()
				process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				if process.wait() != 0:
					raise Exception('Processes: %s\nReturned: %i with output:\n%s\nAnd error: %s' % (' '.join(command), process.returncode, process.stdout.read(), process.stderr.read()))				
				
				print("\t\tConversion took: %s\n" % secondsToReadableTime(time.time() - startTime))
				
				asrTargetFile = None
				
				if thisOutputOption == outputOptions[len(outputOptions) - 1]:
					# since this is the last one we can just use the raw file
					asrTargetFile = hdiutilOutfilePath
					
				else:
					# because there are others that want to use this file, we need to make a copy
					
					tempFileObject, asrTargetFile = tempfile.mkstemp(suffix=".dmg", prefix=os.path.basename(sys.argv[0]), dir="/tmp")
					os.close(tempFileObject)
					
					print('\n\t\tCopying: %s to %s' % (hdiutilOutfilePath, asrTargetFile))
					shutil.copyfile(hdiutilOutfilePath, asrTargetFile)
				
				# asr scan the image
				for scanOption in asrImagescanOptions:
				
					# copy the image if this is not the last item
					asrInnerTargetFile = None
					if scanOption == asrImagescanOptions[len(asrImagescanOptions) - 1]:
						# if it is the last round in this one, no need to copy things
						tempFileObject, asrInnerTargetFile = tempfile.mkstemp(suffix=".dmg", prefix=os.path.basename(sys.argv[0]), dir="/tmp")
						os.close(tempFileObject)
						
						shutil.copyfile(asrTargetFile, asrInnerTargetFile)
					else:
						asrInnerTargetFile = asrTargetFile
					
					print('\t\tASR scanning image %s' % scanOption['message'])
					command = ['/usr/sbin/asr', 'imagescan'] + scanOption['command'] + ['--source', asrInnerTargetFile]
					print('\t\t\tCommand: ' + ' '.join(command))
					
					startTime = time.time()
					process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					if process.wait() != 0:
						print('\t\t\tASR scan failed, trying with the --allowfragmentedcatalog flag')
						command = ['/usr/sbin/asr', 'imagescan'] + scanOption['command'] + ['--allowfragmentedcatalog', '--source', asrInnerTargetFile]
						startTime = time.time()
						process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
						
						if process.wait() != 0:
							raise Exception('Processes: %s\nReturned: %i with output:\n%s\nAnd error: %s' % (' '.join(command), process.returncode, process.stdout.read(), process.stderr.read()))
					
					print("\t\t\tScan took: %s\n" % secondsToReadableTime(time.time() - startTime))
					
					# restore the image
					# ToDo: play with asr options more
					print('\t\t\tASR restoring image')
					command = ['/usr/sbin/asr', 'restore', '--source', asrInnerTargetFile, '--target', restorePoint]
					print('\t\t\t\tCommand: ' + ' '.join(command))
					
					startTime = time.time()
					process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					if process.wait() != 0:
						print('\t\t\t\tASR restore failed, trying with the --allowfragmentedcatalog flag')
						command = ['/usr/sbin/asr', 'restore', '--allowfragmentedcatalog', '--source', asrInnerTargetFile, '--target', restorePoint]
						startTime = time.time()
						process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
						
						if process.wait() != 0:
							raise Exception('Processes: %s\nReturned: %i with output:\n%s\nAnd error: %s' % (' '.join(command), process.returncode, process.stdout.read(), process.stderr.read()))
					print("\t\t\t\tRestore took: %s\n" % secondsToReadableTime(time.time() - startTime))
					
					# cleanup
					os.unlink(asrInnerTargetFile) # cleanup the innerTargetFile
					
				os.unlink(asrTargetFile) # cleanup the targetFile
			
			if "mountImage" in thisSourceOption and thisSourceOption["mountImage"] == True:
				unmountDMG(tempMountPoint)
				
				os.unlink(shadowFileLocation)
				
	sys.exit(0)


